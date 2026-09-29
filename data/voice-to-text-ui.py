#!/usr/bin/env python3
"""语贴 (voice-to-text) 的 GTK4 / libadwaita 界面。

比 tkinter 版本好在：原生 Wayland、自动跟随显示器缩放（HiDPI）、跟随系统深浅色主题。

用法:
  voice-to-text-ui.py record --pid <ffmpeg_pid> --format <fmt> --source <src>
  voice-to-text-ui.py result <transcript_file>
  voice-to-text-ui.py error <message>

环境变量:
  VOICE_TO_TEXT_THEME            dark | light | auto（默认 auto，跟随系统）
  VOICE_TO_TEXT_VISUALIZER       waveform | spectrum（默认 waveform）
  VOICE_TO_TEXT_RESULT_TIMEOUT   结果窗口自动关闭秒数，0 = 不自动关闭（默认 0）
  VOICE_TO_TEXT_ERROR_TIMEOUT    错误窗口自动关闭秒数，0 = 不自动关闭（默认 0）
"""

import math
import os
import queue
import signal
import subprocess
import sys
import threading
import time

import gi

try:
    import cairo
except ImportError:  # pycairo 是 python-gobject 的常规伴随包，缺失时用数值兜底
    cairo = None

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gio, GLib, Gtk  # noqa: E402

HAS_ADW = False
try:
    gi.require_version("Adw", "1")
    from gi.repository import Adw  # noqa: E402

    HAS_ADW = True
except (ValueError, ImportError):
    Adw = None

APP_NAME = "语贴"
FRAME_MS = 33

CSS = """
.vt-timer {
  font-size: 34px;
  font-weight: 700;
  font-feature-settings: "tnum" 1;
}
.vt-dot-rec { color: @success_color; }
.vt-dot-pause { color: @warning_color; }
.vt-wave { color: @accent_color; }
.vt-card {
  background-color: @view_bg_color;
  border: 1px solid alpha(@borders, 0.9);
  border-radius: 12px;
}
.vt-hint { font-size: 11px; }
.vt-error-icon { color: @warning_color; }
"""


def clamp(value, low, high):
    return max(low, min(high, value))


def apply_theme_preference():
    """把 VOICE_TO_TEXT_THEME 翻译成 libadwaita 的配色偏好。"""
    preference = os.environ.get("VOICE_TO_TEXT_THEME", "auto").strip().lower()
    if not HAS_ADW:
        return
    style_manager = Adw.StyleManager.get_default()
    scheme = {
        "dark": Adw.ColorScheme.FORCE_DARK,
        "light": Adw.ColorScheme.FORCE_LIGHT,
    }.get(preference, Adw.ColorScheme.DEFAULT)
    style_manager.set_color_scheme(scheme)


def install_css(display):
    provider = Gtk.CssProvider()
    provider.load_from_string(CSS)
    Gtk.StyleContext.add_provider_for_display(display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


def rgba_of(widget, fallback=(1.0, 1.0, 1.0, 1.0)):
    """读取控件当前 CSS 颜色（用于 cairo 绘制），读不到就用兜底色。"""
    try:
        color = widget.get_color()
        if color is not None:
            return (color.red, color.green, color.blue, color.alpha)
    except Exception:
        pass
    return fallback


def set_source(cr, rgba, multiply_alpha=1.0):
    red, green, blue, alpha = rgba
    cr.set_source_rgba(red, green, blue, clamp(alpha * multiply_alpha, 0.0, 1.0))


class AudioMonitor(threading.Thread):
    """把录音源镜像成 16kHz 单声道 PCM，产出波形/频谱数据。"""

    def __init__(self, audio_format, audio_source, visualizer="waveform", bars=32, points=96):
        super().__init__(daemon=True)
        self.audio_format = audio_format
        self.audio_source = audio_source
        self.visualizer = visualizer if visualizer in {"waveform", "spectrum"} else "waveform"
        self.bar_count = bars
        self.waveform_count = points
        self.results = queue.Queue()
        self.stopping = False
        self.process = None

    def stop(self):
        self.stopping = True
        process = self.process
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=0.8)
            except subprocess.TimeoutExpired:
                process.kill()

    def run(self):
        while not self.stopping:
            command = [
                "ffmpeg", "-hide_banner", "-nostats", "-loglevel", "error",
                "-f", self.audio_format, "-i", self.audio_source,
                "-ac", "1", "-ar", "16000", "-f", "s16le", "-",
            ]
            try:
                self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            except Exception:
                time.sleep(0.5)
                continue
            if self.process.stdout is None:
                time.sleep(0.5)
                continue

            sample_rate = 16000
            chunk = 1024
            window = [0.5 - 0.5 * math.cos(2.0 * math.pi * n / (chunk - 1)) for n in range(chunk)]
            min_freq, max_freq = 90.0, 4200.0
            frequencies = []
            for band in range(self.bar_count):
                low = min_freq * ((max_freq / min_freq) ** (band / self.bar_count))
                high = min_freq * ((max_freq / min_freq) ** ((band + 1) / self.bar_count))
                frequencies.append(math.sqrt(low * high))
            coefficients = [2.0 * math.cos(2.0 * math.pi * freq / sample_rate) for freq in frequencies]

            while not self.stopping:
                raw = self.process.stdout.read(chunk * 2)
                if len(raw) < chunk * 2:
                    break
                samples = [
                    int.from_bytes(raw[i:i + 2], "little", signed=True) / 32768.0
                    for i in range(0, len(raw), 2)
                ]
                bucket = max(1, len(samples) // self.waveform_count)
                waveform = []
                for point in range(self.waveform_count):
                    piece = samples[point * bucket:(point + 1) * bucket]
                    waveform.append(max(piece, key=abs) if piece else 0.0)

                energies = [0.0] * self.bar_count
                if self.visualizer == "spectrum":
                    energies = []
                    for coefficient in coefficients:
                        prev = prev2 = 0.0
                        for sample, win in zip(samples, window):
                            value = sample * win + coefficient * prev - prev2
                            prev2, prev = prev, value
                        energy = math.sqrt(max(0.0, prev2 * prev2 + prev * prev - coefficient * prev * prev2))
                        level = clamp((math.log10(energy + 1e-7) + 3.8) / 2.2, 0.0, 1.0)
                        energies.append(0.0 if level < 0.035 else level)
                self.results.put((waveform, energies))

            if self.process.poll() is None:
                self.process.terminate()
            time.sleep(0.25)


def lerp_series(old, new, old_weight, new_weight):
    return [o * old_weight + n * new_weight for o, n in zip(old, new)]


class PulseDot(Gtk.DrawingArea):
    """跟随主题色呼吸的状态圆点。"""

    def __init__(self, active=True):
        super().__init__()
        self.set_content_width(12)
        self.set_content_height(12)
        self.active = active
        self.phase = 0.0
        self.add_css_class("vt-dot-rec")
        self.set_draw_func(self.draw)
        GLib.timeout_add(FRAME_MS, self.tick)

    def set_active(self, active):
        self.active = active
        self.remove_css_class("vt-dot-rec" if active else "vt-dot-pause")
        self.add_css_class("vt-dot-rec" if active else "vt-dot-pause")

    def tick(self):
        self.phase = (self.phase + 0.13) % (2.0 * math.pi)
        self.queue_draw()
        return GLib.SOURCE_CONTINUE

    def draw(self, _area, cr, width, height):
        color = rgba_of(self, (0.2, 0.8, 0.4, 1.0))
        breathe = 0.45 + 0.55 * (0.5 + 0.5 * math.sin(self.phase)) if self.active else 0.75
        cr.set_line_width(0)
        set_source(cr, color, 0.22 * breathe)
        cr.arc(width / 2, height / 2, 5.4, 0, 2 * math.pi)
        cr.fill()
        set_source(cr, color, breathe)
        cr.arc(width / 2, height / 2, 3.0, 0, 2 * math.pi)
        cr.fill()


def smooth_path(cr, points):
    """把折线变成平滑曲线（用二次贝塞尔逐点过渡）。"""
    if len(points) < 2:
        return
    cr.move_to(points[0][0], points[0][1])
    for index in range(1, len(points) - 1):
        x0, y0 = points[index]
        x1, y1 = points[index + 1]
        mid_x, mid_y = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        c1x, c1y = x0 + (mid_x - x0) * 2.0 / 3.0, y0 + (mid_y - y0) * 2.0 / 3.0
        c2x, c2y = x1 + (mid_x - x1) * 2.0 / 3.0, y1 + (mid_y - y1) * 2.0 / 3.0
        cr.curve_to(c1x, c1y, c2x, c2y, mid_x, mid_y)
    cr.line_to(points[-1][0], points[-1][1])


class Visualizer(Gtk.DrawingArea):
    def __init__(self, mode="waveform", bars=32, points=96):
        super().__init__()
        self.mode = mode if mode in {"waveform", "spectrum"} else "waveform"
        self.bar_count = bars
        self.waveform_count = points
        self.spectrum = [0.0] * bars
        self.waveform = [0.0] * points
        self.phase = 0.0
        self.paused = False
        self.add_css_class("vt-wave")
        self.set_content_height(84)
        self.set_hexpand(True)
        self.set_draw_func(self.draw)

    def feed(self, waveform, spectrum, paused):
        self.paused = paused
        if spectrum is not None:
            self.spectrum = lerp_series(self.spectrum, spectrum, 0.55, 0.45)
            self.waveform = lerp_series(self.waveform, waveform, 0.35, 0.65)
        else:
            self.spectrum = [level * 0.76 for level in self.spectrum]
            self.waveform = [point * 0.72 for point in self.waveform]
        self.queue_draw()

    def draw(self, _area, cr, width, height):
        accent = rgba_of(self, (0.35, 0.6, 1.0, 1.0))
        quiet = (accent[0], accent[1], accent[2], 1.0)
        center = height / 2.0
        self.phase += 0.02 if self.paused else 0.22

        set_source(cr, quiet, 0.18)
        cr.set_line_width(1.0)
        cr.move_to(0, center)
        cr.line_to(width, center)
        cr.stroke()

        if self.mode == "spectrum":
            gap = 4.0
            bar_width = max(4.0, (width - gap * (self.bar_count + 1)) / self.bar_count)
            for index, level in enumerate(self.spectrum):
                ratio = index / max(1, self.bar_count - 1)
                center_bias = 0.42 + 0.58 * (1.0 - abs(ratio - 0.5) * 2.0) ** 1.8
                shimmer = 0.92 + 0.08 * math.sin(self.phase + index * 0.7)
                lift = max(1.2, level * center_bias * shimmer * (height * 0.46))
                x = gap + index * (bar_width + gap)
                cr.rectangle(x, center - lift, bar_width, lift * 2.0)
            set_source(cr, accent, 0.85)
            cr.fill()
            return

        wave_peak = max((abs(point) for point in self.waveform), default=0.0)
        gain = 3.2
        points = []
        for index, sample in enumerate(self.waveform):
            ratio = index / max(1, self.waveform_count - 1)
            envelope = 0.32 + 0.68 * (math.sin(math.pi * ratio) ** 0.5)
            y = center - clamp(sample * gain, -1.0, 1.0) * envelope * (height * 0.46)
            points.append((ratio * width, y))

        active = wave_peak > 0.018 and not self.paused
        cr.set_line_width(2.4)
        cr.set_line_cap(cairo.LINE_CAP_ROUND if cairo else 1)
        cr.set_line_join(cairo.LINE_JOIN_ROUND if cairo else 1)
        if active:
            cr.new_path()
            smooth_path(cr, points)
            cr.line_to(width, center)
            cr.line_to(0, center)
            cr.close_path()
            set_source(cr, accent, 0.22)
            cr.fill()
        cr.new_path()
        smooth_path(cr, points)
        set_source(cr, accent, 0.95 if active else 0.3)
        cr.stroke()


class RecordingWindow:
    def __init__(self, application, recorder_pid, audio_format, audio_source):
        self.recorder_pid = recorder_pid
        self.paused = False
        self.pause_started = 0.0
        self.recorder_gone_at = None
        self.paused_total = 0.0
        self.started_at = time.monotonic()
        self.stopping = False
        self.monitor = AudioMonitor(
            audio_format,
            audio_source,
            os.environ.get("VOICE_TO_TEXT_VISUALIZER", "waveform"),
        )

        self.window = Adw.ApplicationWindow(application=application) if HAS_ADW else Gtk.ApplicationWindow(application=application)
        self.window.set_title("语贴 · 录音")
        self.window.set_default_size(430, 348)
        self.window.set_resizable(False)  # 固定尺寸的 HUD；niri 等合成器会据此浮动窗口
        self.window.connect("close-request", self.on_close)

        self.dot = PulseDot()
        self.status_label = Gtk.Label(label="正在录音")
        self.status_label.add_css_class("dim-label")
        status_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        status_row.set_halign(Gtk.Align.CENTER)
        status_row.append(self.dot)
        status_row.append(self.status_label)

        self.time_label = Gtk.Label(label="00:00")
        self.time_label.add_css_class("vt-timer")

        self.visualizer = Visualizer(
            os.environ.get("VOICE_TO_TEXT_VISUALIZER", "waveform"),
            self.monitor.bar_count,
            self.monitor.waveform_count,
        )

        self.pause_button = Gtk.Button(label="暂停录音")
        self.pause_button.connect("clicked", lambda _button: self.toggle_pause())
        self.stop_button = Gtk.Button(label="停止录音")
        self.stop_button.add_css_class("destructive-action")
        self.stop_button.connect("clicked", lambda _button: self.stop_recording())
        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        buttons.set_homogeneous(True)
        buttons.append(self.pause_button)
        buttons.append(self.stop_button)

        hint = Gtk.Label(label="空格 暂停 / 继续 · Enter 或 Esc 停止")
        hint.add_css_class("dim-label")
        hint.add_css_class("vt-hint")

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_margin_top(18)
        content.set_margin_bottom(18)
        content.set_margin_start(18)
        content.set_margin_end(18)
        content.append(status_row)
        content.append(self.time_label)
        content.append(self.visualizer)
        content.append(buttons)
        content.append(hint)

        if HAS_ADW:
            toolbar = Adw.ToolbarView()
            header = Adw.HeaderBar()
            header.set_title_widget(Adw.WindowTitle(title=APP_NAME, subtitle="语音输入"))
            toolbar.add_top_bar(header)
            toolbar.set_content(content)
            self.window.set_content(toolbar)
        else:
            header = Gtk.HeaderBar()
            header.set_title_widget(Gtk.Label(label=APP_NAME))
            self.window.set_titlebar(header)
            self.window.set_child(content)

        self.install_shortcuts()
        self.apply_theme()

    def install_shortcuts(self):
        controller = Gtk.ShortcutController()
        controller.set_scope(Gtk.ShortcutScope.GLOBAL)
        bindings = {
            "space": self.toggle_pause,
            "Return": self.stop_recording,
            "KP_Enter": self.stop_recording,
            "Escape": self.stop_recording,
        }
        for trigger, handler in bindings.items():
            action = Gtk.CallbackAction.new(lambda _widget, _args, cb=handler: (cb(), True)[1])
            controller.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string(trigger), action))
        self.window.add_controller(controller)

    def apply_theme(self):
        # Adw 由 apply_theme_preference() 统一管；纯 GTK 时手工设 prefer-dark。
        if HAS_ADW:
            return
        preference = os.environ.get("VOICE_TO_TEXT_THEME", "auto").strip().lower()
        settings = Gtk.Settings.get_default()
        if settings is not None and preference in {"dark", "light"}:
            settings.set_property("gtk-application-prefer-dark-theme", preference == "dark")

    def safe_signal(self, sig):
        try:
            os.kill(self.recorder_pid, sig)
        except (ProcessLookupError, PermissionError, OSError):
            pass

    def toggle_pause(self):
        if self.stopping:
            return
        if self.paused:
            self.safe_signal(signal.SIGCONT)
            self.paused_total += time.monotonic() - self.pause_started
            self.paused = False
            self.pause_button.set_label("暂停录音")
            self.status_label.set_label("正在录音")
            self.dot.set_active(True)
        else:
            self.safe_signal(signal.SIGSTOP)
            self.pause_started = time.monotonic()
            self.paused = True
            self.pause_button.set_label("继续录音")
            self.status_label.set_label("已暂停")
            self.dot.set_active(False)

    def stop_recording(self):
        if self.stopping:
            return
        self.stopping = True
        if self.paused:
            self.safe_signal(signal.SIGCONT)
            self.paused_total += time.monotonic() - self.pause_started
            self.paused = False
        self.monitor.stop()
        self.window.close()

    def on_close(self, _window):
        if self.paused:  # 被 SIGSTOP 冻住的 ffmpeg 收不到 TERM，必须先恢复
            self.safe_signal(signal.SIGCONT)
            self.paused_total += time.monotonic() - self.pause_started
            self.paused = False
        self.stopping = True
        self.monitor.stop()
        return False

    def tick(self):
        if self.stopping:
            return GLib.SOURCE_REMOVE
        # 录音进程提前退出（拔麦、崩溃）时收尾，别让计时器空转
        if self.recorder_alive():
            self.recorder_gone_at = None
        else:
            if self.recorder_gone_at is None:
                self.recorder_gone_at = time.monotonic()
            elif time.monotonic() - self.recorder_gone_at > 1.0:
                self.status_label.set_label("录音已结束")
                self.stop_recording()
                return GLib.SOURCE_REMOVE
        latest_waveform = latest_spectrum = None
        while True:
            try:
                latest_waveform, latest_spectrum = self.monitor.results.get_nowait()
            except queue.Empty:
                break
        if latest_waveform is not None and latest_spectrum is not None and not self.paused:
            self.visualizer.feed(latest_waveform, latest_spectrum, self.paused)
        elif not self.paused:
            self.visualizer.feed(None, None, self.paused)
        active_paused = time.monotonic() - self.pause_started if self.paused else 0.0
        elapsed = max(0.0, time.monotonic() - self.started_at - self.paused_total - active_paused)
        self.time_label.set_label(f"{int(elapsed) // 60:02d}:{int(elapsed) % 60:02d}")
        return GLib.SOURCE_CONTINUE

    def recorder_alive(self):
        try:
            os.kill(self.recorder_pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except OSError:
            return True
        return True

    @staticmethod
    def recorder_state(pid):
        try:
            with open(f"/proc/{pid}/stat", "r", encoding="utf-8") as handle:
                return handle.read().rsplit(") ", 1)[1].split()[0]
        except Exception:
            return "?"

    def self_test(self):
        """VOICE_TO_TEXT_UI_SELFTEST=1：脚本化走一遍暂停/继续/停止，打印真实进程状态。"""
        steps = []

        def pause():
            self.toggle_pause()
            steps.append(("暂停后", self.recorder_state(self.recorder_pid), self.status_label.get_label()))

        def resume():
            self.toggle_pause()
            steps.append(("继续后", self.recorder_state(self.recorder_pid), self.status_label.get_label()))
            steps.append(("计时", self.time_label.get_label(), "波形点已更新" if any(abs(pt) > 0.01 for pt in self.visualizer.waveform) else "波形仍为 0"))

        def finish():
            steps.append(("停止前", self.recorder_state(self.recorder_pid), self.status_label.get_label()))
            for name, state, extra in steps:
                print(f"selftest {name}: proc_state={state} {extra}", flush=True)
            self.stop_recording()

        GLib.timeout_add(1500, lambda: (pause(), False)[1])
        GLib.timeout_add(3000, lambda: (resume(), False)[1])
        GLib.timeout_add(4500, lambda: (finish(), False)[1])

    def present(self):
        self.monitor.start()
        GLib.timeout_add(FRAME_MS, self.tick)
        self.window.present()
        if os.environ.get("VOICE_TO_TEXT_UI_SELFTEST") == "1":
            self.self_test()


def copy_to_clipboard(text):
    for command in (["wl-copy", "--trim-newline"], ["xclip", "-selection", "clipboard"]):
        try:
            subprocess.run(command, input=text.encode("utf-8"), check=True, timeout=5)
            return True
        except Exception:
            continue
    return False


class ResultWindow:
    def __init__(self, application, transcript_file):
        self.transcript_file = transcript_file
        try:
            with open(transcript_file, "r", encoding="utf-8") as handle:
                text = handle.read().strip()
        except Exception:
            text = ""
        self.text = text

        self.window = Adw.ApplicationWindow(application=application) if HAS_ADW else Gtk.ApplicationWindow(application=application)
        self.window.set_title("语贴 · 识别结果")
        self.window.set_default_size(620, -1)  # 高度交给内容自适应

        text_view = Gtk.TextView()
        text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        text_view.set_monospace(False)
        text_view.set_left_margin(14)
        text_view.set_right_margin(14)
        text_view.set_top_margin(10)
        text_view.set_bottom_margin(10)
        text_view.get_buffer().set_text(text)
        text_view.add_css_class("vt-card")
        text_view.set_size_request(560, -1)  # 保证单行不至于细长，也不会太宽
        self.text_view = text_view

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_propagate_natural_height(True)  # 窗口高度随文本量变化
        scroller.set_min_content_height(48)  # 一行文本时窗口不虚胖
        scroller.set_max_content_height(420)  # 超过就内部滚动，不会撑满屏幕
        scroller.set_child(text_view)

        headline = Gtk.Label()
        headline.set_markup("<b>已复制到剪贴板</b>")
        headline.set_halign(Gtk.Align.START)
        self.count_label = Gtk.Label(label=f"{len(text)} 字")
        self.count_label.add_css_class("dim-label")
        self.count_label.set_halign(Gtk.Align.START)

        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title_box.append(headline)
        title_box.append(self.count_label)

        copy_button = Gtk.Button(label="再次复制")
        copy_button.connect("clicked", self.on_copy)
        close_button = Gtk.Button(label="关闭")
        close_button.add_css_class("suggested-action")
        close_button.connect("clicked", lambda _button: self.window.close())
        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        buttons.set_halign(Gtk.Align.END)
        buttons.append(copy_button)
        buttons.append(close_button)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_margin_top(18)
        content.set_margin_bottom(18)
        content.set_margin_start(18)
        content.set_margin_end(18)
        content.append(title_box)
        content.append(scroller)
        content.append(buttons)

        if HAS_ADW:
            toolbar = Adw.ToolbarView()
            header = Adw.HeaderBar()
            header.set_title_widget(Adw.WindowTitle(title=APP_NAME, subtitle="识别完成"))
            toolbar.add_top_bar(header)
            toolbar.set_content(content)
            self.window.set_content(toolbar)
        else:
            header = Gtk.HeaderBar()
            header.set_title_widget(Gtk.Label(label=APP_NAME))
            self.window.set_titlebar(header)
            self.window.set_child(content)

        controller = Gtk.ShortcutController()
        controller.set_scope(Gtk.ShortcutScope.GLOBAL)
        for trigger in ("Escape", "Return", "KP_Enter"):
            action = Gtk.CallbackAction.new(lambda _widget, _args: (self.window.close(), True)[1])
            controller.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string(trigger), action))
        self.window.add_controller(controller)

        timeout = os.environ.get("VOICE_TO_TEXT_RESULT_TIMEOUT", "0").strip()
        try:
            self.timeout_seconds = max(0, int(timeout))
        except ValueError:
            self.timeout_seconds = 0

    def on_copy(self, _button):
        copy_to_clipboard(self.text)

    def present(self):
        if self.timeout_seconds:
            remaining = [self.timeout_seconds]

            def countdown():
                remaining[0] -= 1
                if remaining[0] <= 0:
                    self.window.close()
                    return GLib.SOURCE_REMOVE
                self.count_label.set_label(f"{len(self.text)} 字 · {remaining[0]} 秒后自动关闭")
                return GLib.SOURCE_CONTINUE

            GLib.timeout_add_seconds(1, countdown)
        self.window.present()


class ErrorWindow:
    """错误提示窗：GTK4 卡片，替代 zenity --error，风格与结果窗一致。"""

    def __init__(self, application, message):
        self.window = Adw.ApplicationWindow(application=application) if HAS_ADW else Gtk.ApplicationWindow(application=application)
        self.window.set_title(APP_NAME)
        self.window.set_resizable(False)
        self.window.add_css_class("vt-window")

        icon = Gtk.Image.new_from_icon_name("dialog-warning-symbolic")
        icon.set_pixel_size(30)
        icon.add_css_class("vt-error-icon")
        icon.set_valign(Gtk.Align.START)

        # 标题栏已经有「语贴 / 出错了」，正文不再重复一遍应用名
        body = Gtk.Label(label=message)
        body.set_wrap(True)
        body.set_xalign(0.0)
        body.set_max_width_chars(46)
        body.set_halign(Gtk.Align.START)

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        text_box.set_hexpand(True)
        text_box.append(body)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        row.append(icon)
        row.append(text_box)

        close_button = Gtk.Button(label="关闭")
        close_button.add_css_class("suggested-action")
        close_button.connect("clicked", lambda _button: self.window.close())
        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        buttons.set_halign(Gtk.Align.END)
        buttons.append(close_button)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_top(18)
        content.set_margin_bottom(18)
        content.set_margin_start(18)
        content.set_margin_end(18)
        content.append(row)
        content.append(buttons)

        if HAS_ADW:
            toolbar = Adw.ToolbarView()
            header = Adw.HeaderBar()
            header.set_title_widget(Adw.WindowTitle(title=APP_NAME, subtitle="出错了"))
            toolbar.add_top_bar(header)
            toolbar.set_content(content)
            self.window.set_content(toolbar)
        else:
            header = Gtk.HeaderBar()
            header.set_title_widget(Gtk.Label(label=APP_NAME))
            self.window.set_titlebar(header)
            self.window.set_child(content)

        controller = Gtk.ShortcutController()
        controller.set_scope(Gtk.ShortcutScope.GLOBAL)
        for trigger in ("Escape", "Return", "KP_Enter"):
            action = Gtk.CallbackAction.new(lambda _widget, _args: (self.window.close(), True)[1])
            controller.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string(trigger), action))
        self.window.add_controller(controller)

        timeout = os.environ.get("VOICE_TO_TEXT_ERROR_TIMEOUT", "0").strip()
        try:
            self.timeout_seconds = max(0, int(timeout))
        except ValueError:
            self.timeout_seconds = 0

    def present(self):
        if self.timeout_seconds:
            GLib.timeout_add_seconds(self.timeout_seconds, lambda: (self.window.close(), GLib.SOURCE_REMOVE)[1])
        self.window.present()


def parse_options(argv):
    options = {}
    index = 0
    while index < len(argv):
        token = argv[index]
        if token.startswith("--"):
            key = token[2:]
            value = argv[index + 1] if index + 1 < len(argv) else ""
            options[key] = value
            index += 2
        else:
            index += 1
    return options


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "record"
    application = Adw.Application(application_id="dev.inkblade.VoiceToTextUI", flags=Gio.ApplicationFlags.NON_UNIQUE) if HAS_ADW else Gtk.Application(application_id="dev.inkblade.VoiceToTextUI", flags=Gio.ApplicationFlags.NON_UNIQUE)

    failed = []

    def activate(app):
        try:
            install_css(Gdk.Display.get_default())
            apply_theme_preference()
            if mode == "result":
                transcript_file = sys.argv[2] if len(sys.argv) > 2 else ""
                view = ResultWindow(app, transcript_file)
            elif mode == "error":
                view = ErrorWindow(app, sys.argv[2] if len(sys.argv) > 2 else "")
            else:
                options = parse_options(sys.argv[2:])
                view = RecordingWindow(
                    app,
                    int(options.get("pid", "0") or 0),
                    options.get("format", "pulse"),
                    options.get("source", "default"),
                )
            view.present()
        except Exception:
            import traceback

            traceback.print_exc()
            failed.append(True)
            app.quit()

    application.connect("activate", activate)
    status = application.run([])
    return 1 if failed else status


if __name__ == "__main__":
    sys.exit(main())

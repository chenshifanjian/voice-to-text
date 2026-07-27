# voice-to-text

一个 Linux 桌面语音输入小工具：从默认麦克风录音，使用本地 `faster-whisper` 转文字，把结果复制到剪贴板，并通过桌面通知提示状态。

适合快速语音输入：按快捷键，说话，停止录音，然后把识别出来的文字粘贴到聊天框、编辑器或任意输入框。

## 功能

- 使用 `faster-whisper` 本地语音识别
- 默认 CPU `int8` 模式，不依赖 CUDA
- Wayland 下使用 `wl-copy` 复制到剪贴板
- X11 下回退到 `xclip` 或 `xsel`
- 使用 `notify-send` 发送桌面通知
- 使用 `zenity` 提供“停止录音”弹窗
- 临时录音和错误日志保存在 `${XDG_RUNTIME_DIR}/voice-to-text`

## 依赖

系统依赖：

- `ffmpeg`
- `uv`
- `zenity`
- `notify-send`
- Wayland 环境需要 `wl-copy`
- X11 环境需要 `xclip` 或 `xsel`

Arch Linux 示例：

```bash
sudo pacman -S ffmpeg uv zenity libnotify wl-clipboard
```

## 安装

```bash
git clone https://github.com/chenshifanjian/voice-to-text.git
cd voice-to-text
./install.sh
voice-to-text --setup
```

`--setup` 会创建独立 Python 环境：

```text
~/.local/share/voice-to-text/venv
```

第一次转写时会下载 Whisper 模型到 Hugging Face 缓存目录，之后会复用缓存，不需要每次重新下载。

## 使用

运行：

```bash
voice-to-text
```

然后：

1. 对着麦克风说话。
2. 点击弹窗里的停止按钮。
3. 等待转文字完成。
4. 在目标输入框按 `Ctrl+V` 粘贴。

默认识别中文。可以用环境变量切换语言：

```bash
VOICE_TO_TEXT_LANGUAGE=en voice-to-text
```

默认模型是 `small`。可以切换模型：

```bash
VOICE_TO_TEXT_MODEL=base voice-to-text
```

常见模型选择：

- `tiny`：最快，准确率最低
- `base`：较快，适合普通短句
- `small`：默认选项，速度和准确率比较均衡
- `medium`：更准，但更慢

## niri 快捷键

在 niri 配置的 `binds { ... }` 块里加入：

```kdl
Mod+Alt+Space hotkey-overlay-title="语音转文字 Voice to text" { spawn "voice-to-text"; }
```

然后重新加载配置：

```bash
niri msg action load-config-file
```

之后按 `Mod+Alt+Space` 就可以启动录音转文字。

## 故障排查

如果转写失败，查看错误日志：

```text
${XDG_RUNTIME_DIR}/voice-to-text/error-*.log
```

如果录音失败，先检查 `ffmpeg` 是否能访问默认麦克风：

```bash
ffmpeg -f pulse -i default -t 3 test.wav
```

如果 Wayland 下无法复制到剪贴板，确认安装了 `wl-clipboard`，并且环境变量 `WAYLAND_DISPLAY` 存在。

如果第一次转写很慢，通常是在下载或加载 Whisper 模型。等第一次完成后，后续会快很多。

## English

A small Linux desktop voice input helper. It records from the default microphone, transcribes speech locally with `faster-whisper`, copies the result to the clipboard, and shows desktop notifications.

It is designed for quick voice prompts: press a shortcut, speak, stop recording, then paste the recognized text into any chat or editor.

## Features

- Local transcription with `faster-whisper`
- CPU `int8` mode by default, so it works without CUDA
- Wayland clipboard support via `wl-copy`
- X11 clipboard fallback via `xclip` or `xsel`
- Desktop notifications via `notify-send`
- Stop-recording dialog via `zenity`
- Temporary recordings and logs under `${XDG_RUNTIME_DIR}/voice-to-text`

## Dependencies

System packages:

- `ffmpeg`
- `uv`
- `zenity`
- `notify-send`
- `wl-copy` on Wayland, or `xclip`/`xsel` on X11

On Arch Linux, for example:

```bash
sudo pacman -S ffmpeg uv zenity libnotify wl-clipboard
```

## Install

```bash
git clone https://github.com/chenshifanjian/voice-to-text.git
cd voice-to-text
./install.sh
voice-to-text --setup
```

The setup step creates an isolated environment at:

```text
~/.local/share/voice-to-text/venv
```

The first transcription downloads the selected Whisper model into the Hugging Face cache. Later runs reuse the cached model.

## Usage

Run:

```bash
voice-to-text
```

Speak into the microphone, click the stop dialog, then paste the clipboard text with `Ctrl+V`.

Chinese is the default recognition language. Override it with:

```bash
VOICE_TO_TEXT_LANGUAGE=en voice-to-text
```

The default model is `small`. Override it with:

```bash
VOICE_TO_TEXT_MODEL=base voice-to-text
```

## niri Shortcut

Add this inside your `binds { ... }` block:

```kdl
Mod+Alt+Space hotkey-overlay-title="Voice to text" { spawn "voice-to-text"; }
```

Then reload niri config:

```bash
niri msg action load-config-file
```

## Troubleshooting

If transcription fails, check logs in:

```text
${XDG_RUNTIME_DIR}/voice-to-text/error-*.log
```

If recording fails, verify that `ffmpeg` can access your default PulseAudio/PipeWire source:

```bash
ffmpeg -f pulse -i default -t 3 test.wav
```

If clipboard copy does not work on Wayland, install `wl-clipboard` and make sure `WAYLAND_DISPLAY` is set.

## License

MIT

# 语贴 voice-to-text

一个很小的 Linux 桌面语音输入工具。

中文名叫 **语贴**：语音变成文字，然后贴到你正在使用的地方。

按下快捷键，说一句话，停止录音。它会用本地语音模型（默认 SenseVoice，可回退 Whisper）把语音转成文字，并复制到剪贴板。接下来你只需要在聊天框、编辑器或浏览器输入框里按 `Ctrl+V`。

## 项目状态（墨刃工坊内部）

- 业务域：软件工具
- 产品或系统：语贴
- 项目性质：工具开发
- 版本或阶段：护航中
- 当前状态：护航中
- 维护状态：长期运行
- 负责人：王文龙
- 参与人员：无（仅负责人王文龙）
- 最近更新时间：2026-09-29
- 最近版本：`v0.2.5`（2026-09-29）
- GitHub：`https://github.com/chenshifanjian/voice-to-text`

> 四同步位置：本地项目仓库 / GitHub 云端 / 本地安装（`~/.local/bin/voice-to-text`、`~/.local/share/voice-to-text/voice-to-text-ui.py`）/ GitHub Release。每次改动后逐个 `diff` 核对。

### 运行入口

- 命令：`~/.local/bin/voice-to-text`
- 桌面入口：`~/.local/share/applications/voice-to-text.desktop`
- 程序数据：`~/.local/share/voice-to-text`
- 详细安装和使用方式见本文下方各章节。

### 巡检方式

- 确认 `voice-to-text` 命令可执行，快捷键能正常触发录音。
- 确认录音、转写、剪贴板复制、通知四个环节都能走通。
- 确认 Whisper 模型缓存仍在，未被其他项目清理。
- 确认 `ffmpeg` 和剪贴板工具（`wl-copy` / `xclip` / `xsel`）仍可用。

### 常见故障

- 首次转写慢：需要下载模型（SenseVoice 约 900 MB，Whisper `medium` 约 1.5 GB），属正常现象，缓存后即可复用。
- 明明说了话却提示“没听到声音”：判据是「-38 dB 以上的有效语音 ≥ 0.3 秒」。说得太短、离麦太远或麦克风增益太低会被拦；错误窗里会打印有效语音秒数、峰值 dB 和平均 dB，先看数字，再判断是不是麦克风的问题。
- 悬浮窗不出现或界面报错：`VOICE_TO_TEXT_UI=none voice-to-text` 可以直接在终端里录音（按回车停止）；`voice-to-text --doctor` 会打印界面后端和依赖检查结果。
- 内存盘被写满（`/run/user/$UID` 到 100%）：只会在把 `VOICE_TO_TEXT_AUDIO_SOURCE` 指向文件或不限速的 `lavfi` 源时发生，现在由 `VOICE_TO_TEXT_MAX_SECONDS` 兜底。历史残留可手工清理 `/run/user/$UID/voice-to-text/recording-*.wav`。
- 重启后第一次很慢：先确认模型缓存目录还在（Hugging Face / ModelScope），见下方「安装后文件位置」。

### 后续方向

见下方「路线图」章节。护航期间以保证可用为主，路线图内容按需推进。

---

这个工具最初是为“和 AI 快速语音交流”做的：不需要打开复杂应用，不需要常驻一个大服务，也不需要把录音发到云端。它只做一件事：把你刚说的话，尽快变成可以粘贴的文字。

## 适合谁

- 经常和 ChatGPT、Claude、OpenCode、MiMoCode 等 AI 工具对话的人
- 想用语音快速写 prompt、笔记、搜索词或短消息的人
- 使用 Linux 桌面，尤其是 Wayland/niri/sway/hyprland 的用户
- 希望语音识别尽量本地完成，不想默认依赖在线服务的人

如果你需要完整的连续听写、自动标点修正、托盘应用、历史记录或富 GUI，这个项目还不是那个形态。它更像一个简单、透明、可改的桌面自动化小工具。

## 功能特性

- 本地语音识别：默认 `SenseVoiceSmall`（INT8，中文更准、速度更快），可切换回 `faster-whisper`
- 默认自动识别语言，适合中英混合短句
- 中文输出会尽量转换为简体
- 默认 CPU `int8` 模式，不需要 CUDA
- 双后端可切换：`VOICE_TO_TEXT_BACKEND=auto|sensevoice|whisper`
- Wayland 剪贴板：`wl-copy`
- X11 剪贴板回退：`xclip` 或 `xsel`
- 桌面通知：`notify-send`
- 中文小悬浮窗口：Python + GTK4/libadwaita，原生 Wayland、自动跟随显示器缩放（HiDPI）与系统深浅色主题
- 录音窗口支持录音时长、暂停/继续、停止录音和实时音量反馈；结果窗口自动复制到剪贴板
- 没听到声音时直接提示（不做无意义的识别），并弹出中文错误窗；无 GTK 时自动回退到 zenity
- 不常驻后台，按需启动
- 临时录音和日志放在 `${XDG_RUNTIME_DIR}/voice-to-text`
- 可选个人词库和纠错表
- 最近转写历史，方便找回上一条结果

## 快速开始

安装系统依赖。Arch Linux 示例：

```bash
sudo pacman -S ffmpeg uv zenity libnotify wl-clipboard python-gobject python-cairo gtk4 libadwaita
```

其中 `python-gobject python-cairo gtk4 libadwaita` 只服务于悬浮窗界面（GTK4/libadwaita）：装了就是最好看的那个窗口，没装会自动退回 `zenity` 对话框，功能不受影响。`voice-to-text --doctor` 会直接告诉你当前用的是哪个。

克隆并安装：

```bash
git clone https://github.com/chenshifanjian/voice-to-text.git
cd voice-to-text
./install.sh
voice-to-text --setup
voice-to-text --check
```

运行：

```bash
voice-to-text
```

使用流程：

1. 运行命令或按你绑定的快捷键。
2. 对着麦克风说话。
3. 在“语贴”录音窗口里查看时长和音量反馈，可以暂停/继续，也可以点击“停止录音”。
4. 等待转写完成。
5. 到目标输入框按 `Ctrl+V` 粘贴。

第一次转写时会下载模型（SenseVoice 约 900 MB，Whisper `medium` 约 1.5 GB），可能会慢一点。下载完成后会直接复用本地缓存，日常转写不再联网。

如果只是想检查环境是否正常，不开始录音，可以运行：

```bash
voice-to-text --check
```

如果是第一次配置个人词库，可以运行：

```bash
voice-to-text --init-config
```

## niri 快捷键

如果你使用 niri，可以把下面这行加入配置里的 `binds { ... }` 块：

```kdl
Mod+Alt+Space hotkey-overlay-title="语音转文字 Voice to text" { spawn "voice-to-text"; }
```

重新加载配置：

```bash
niri msg action load-config-file
```

之后按 `Mod+Alt+Space` 就能开始录音。

录音时会显示一个小悬浮窗口、录音时长和实时音频反馈。默认可视化是波形：语贴会用 `ffmpeg` 读取麦克风 PCM 音频，按时间振幅画出类似录音软件的音波线，安静时趋近平线，有声音时随振幅起伏。

界面是 GTK4/libadwaita 窗口（`data/voice-to-text-ui.py`），因此自动跟随系统缩放比例和深浅色主题，不再需要手动调字号。相关环境变量：

```bash
VOICE_TO_TEXT_THEME=light voice-to-text         # dark | light | auto（默认 auto，跟随系统）
VOICE_TO_TEXT_VISUALIZER=spectrum voice-to-text # waveform | spectrum（默认 waveform）
VOICE_TO_TEXT_RESULT_TIMEOUT=8 voice-to-text    # 结果窗自动关闭秒数，0 = 不自动关闭
VOICE_TO_TEXT_ERROR_TIMEOUT=8 voice-to-text     # 错误窗自动关闭秒数，0 = 不自动关闭
VOICE_TO_TEXT_UI=none voice-to-text             # auto | gtk | zenity | none（默认 auto）
VOICE_TO_TEXT_MAX_SECONDS=600 voice-to-text     # 单次录音最长秒数（默认 3600，防止无限源的录音把 /run 塞满）
VOICE_TO_TEXT_KEEP_FILES=5 voice-to-text        # 运行目录只保留最近 N 份录音/转写（默认 20）
```

界面后端按 `VOICE_TO_TEXT_UI` 选择：`gtk` 用 GTK4 悬浮窗，`zenity` 用系统对话框，`none` 完全不弹窗（纯终端/SSH 里 `read` 一个回车停止录音）。默认 `auto` 会依次挑可用的那个；GTK4 启动失败的兜底也一样。录音窗被关掉（点 ✕ 或进程被杀）与正常停止等价：语贴会继续收尾并转写，不会弹一个多余的"界面未能启动"。

音频长度会被 `VOICE_TO_TEXT_MAX_SECONDS` 兜底截断：麦克风是实时源，正常用不到；但如果你把 `VOICE_TO_TEXT_AUDIO_SOURCE` 指向文件或不限速的 `lavfi` 源，没有这个上限它能以近万倍速写盘——曾经真的把 `/run/user/1000`（1.6G tmpfs）写到 100%。记录只留在 `/run/user/$UID/voice-to-text/`，每次运行后会按 `VOICE_TO_TEXT_KEEP_FILES` 自动清理旧录音与转写。

如果使用 niri，可以给语贴的窗口加浮动规则（避免被平铺，并去掉跟随主题色的焦点描边）：

```kdl
window-rule {
    match app-id=r#"^dev\.inkblade\.VoiceToTextUI$"#
    open-floating true
    geometry-corner-radius 14
    clip-to-geometry true
    border { off }
    focus-ring { off }
}
window-rule {
    match app-id=r#"^dev\.inkblade\.VoiceToTextUI$"# title=r#"录音"#
    default-floating-position x=24 y=24 relative-to="bottom-right"
}
```

## 配置

### 识别后端（SenseVoice / Whisper）

默认 `auto`：装了 SenseVoice 就用 SenseVoice，否则回退 Whisper。

```bash
VOICE_TO_TEXT_BACKEND=sensevoice voice-to-text
VOICE_TO_TEXT_BACKEND=whisper voice-to-text
```

同一台 16 核 CPU 机器、同一段 8 秒中文录音实测：

| 后端 | 端到端耗时 | 中文准确率 |
| --- | --- | --- |
| `sensevoice`（INT8） | 约 2.2 秒 | 更高，中英混说更稳 |
| `whisper` `medium`（INT8） | 约 11 秒 | 略低 |

代价有三点：SenseVoice 不支持 hotwords 词库（改由纠错表兜底）、英文技术词比 Whisper 略弱、单段音频上限 30 秒（语贴会自动按静音切段，长录音不受影响）。

```bash
VOICE_TO_TEXT_SENSEVOICE_MODEL=iic/SenseVoiceSmall voice-to-text
VOICE_TO_TEXT_SENSEVOICE_THREADS=4 voice-to-text
VOICE_TO_TEXT_SENSEVOICE_MAX_SEGMENT=25 voice-to-text
```

### 语言

默认自动识别语言，适合中英混合：

```bash
voice-to-text
```

如果你只说中文，可以强制中文：

```bash
VOICE_TO_TEXT_LANGUAGE=zh voice-to-text
```

如果你只说英文，可以强制英文：

```bash
VOICE_TO_TEXT_LANGUAGE=en voice-to-text
```

Whisper 后端的默认模型是 `medium`（准确率和速度的最佳平衡）。如果你想更快，可以换成 `small`；如果追求最高准确率且不介意速度慢，可以换 `large-v3-turbo`（有 NVIDIA GPU 时才有速度优势）：

```bash
VOICE_TO_TEXT_MODEL=small voice-to-text
```

默认 beam size 是 `5`，准确率更好但会比贪心解码慢一点。可以调整：

```bash
VOICE_TO_TEXT_BEAM_SIZE=3 voice-to-text
```

默认会给 Whisper 一段简短的自然风格提示，作为转写结果的样子参考，帮助保留英文单词、产品名和阿拉伯数字。注意 Whisper 的 `initial_prompt` 不是指令，不能用"请……""不要……"这类命令式文字，否则可能把提示词本身回显成转写结果。可以覆盖：

```bash
VOICE_TO_TEXT_INITIAL_PROMPT="以下是一段语音转文字的结果，内容包含中文简体字、English words 和阿拉伯数字。" voice-to-text
```

词库（hotwords）只对 `whisper` 后端生效，SenseVoice 不接受 hotwords，改用下面的纠错表兜底。

安装脚本会额外安装一份计算机专有名词 starter 词库，来源参考了 Wikipedia 的计算机科学、计算机硬件和人工智能术语表，并补充了常见开发工具、AI 工具和 Linux 桌面词。运行时优先读取个人词库，再从内置词库补足，最多取前 `40` 个安全词作为 `faster-whisper` hotwords 使用，减少专有名词对普通中文和数字听写的干扰，基本不增加识别时间：

```text
~/.local/share/voice-to-text/computer-terms.txt
```

你自己的高频词放在这里，每行一个词：

```text
~/.config/voice-to-text/terms.txt
```

比如：

```text
墨刃工坊
语贴
OpenCode
MiMoCode
niri
Wayland
faster-whisper
```

也可以调整加入提示词的数量：

```bash
VOICE_TO_TEXT_TERMS_LIMIT=80 voice-to-text
```

如果某些词经常被识别错，可以加后处理纠错表。格式是 `错词<Tab>正确词`：

```text
~/.config/voice-to-text/replacements.tsv
```

示例：

```text
open code	OpenCode
git hub	GitHub
read me	README
```

这套机制适合慢慢养：starter 词库只放通用计算机词和常见工具名，个人词库更适合放你自己的项目名、产品名、同事名、缩写、命令、库名和常说的 prompt 术语。如果你发现某个计算机术语、AI 工具名、Linux 桌面词或常见误识别特别高频，欢迎通过 issue 或 pull request 投稿，把它加进默认词库或纠错表。

为了避免静音或不确定语音时出现 `UDP, UDP-8, UDP-8...` 这类 hotwords 幻觉，语贴默认不会把很短的全大写协议/编码缩写作为 hotwords 使用。转写阶段也启用了重复抑制，后处理会过滤明显的大段重复技术词输出。

建议优先贡献这类内容：

- 高频开发工具、AI 工具和开源项目名
- 中英混合场景里常被拆错的词，比如 `GitHub`、`README`、`OpenCode`
- Linux 桌面、终端、包管理和开发环境相关词
- 确认稳定的错词到正词映射

不建议把非常长、非常冷门或只在个人项目里出现一次的词放进默认词库。词库太大不会线性提升准确率，反而可能削弱提示效果；这类词更适合放进个人 `terms.txt`。

## 轻量辅助命令

语贴不做常驻服务，但提供几个按需运行的小命令，方便排错和找回文本。

初始化个人词库和纠错表：

```bash
voice-to-text --init-config
```

查看更完整的诊断报告：

```bash
voice-to-text --doctor
```

查看最近转写历史：

```bash
voice-to-text --history
```

把最近一次转写重新复制到剪贴板：

```bash
voice-to-text --copy-last
```

历史记录默认保存在：

```text
~/.local/share/voice-to-text/history.tsv
```

默认只保留最近 `20` 条，可以调整：

```bash
VOICE_TO_TEXT_HISTORY_LIMIT=50 voice-to-text
```

默认从 PulseAudio/PipeWire 的 `default` 麦克风录音。特殊情况下可以覆盖录音后端：

```bash
VOICE_TO_TEXT_AUDIO_FORMAT=pulse VOICE_TO_TEXT_AUDIO_SOURCE=default voice-to-text
```

界面默认跟随系统深浅色主题。也可以强制指定：

```bash
VOICE_TO_TEXT_THEME=light voice-to-text
```

可选值：`auto`（默认）、`light`、`dark`。

识别为空的情况会被提前拦下：用一次 `volumedetect,silencedetect=noise=-38dB:d=0.25` 统计出**有效语音时长**，低于 **0.3 秒**就直接提示“没听到声音”，不送后端识别。

这个 0.3 秒是按真机录音标定出来的，不是拍脑袋：真人成句 1.5–5.0 秒、很短的一句真话 0.38–0.43 秒、安静房间底噪 0.07 秒、合成静音 0.00 秒——0.3 秒正好卡在「最短的真实发音」和「最后一个噪声毛刺」之间。这里刻意**不用平均音量作判据**：静音段占多数时平均值会被拉低，真人说话也会被判成静音（第一版用 `-45 dB` 平均音量阈值，实测会误杀真实语音）。提示里会同时打印有效语音秒数、峰值 dB 和平均 dB，方便核对判据是否合理。只识别出标点的结果同样会被当作无效结果。

脚本带单实例保护：如果一次录音还没结束，再次触发快捷键会提示已有实例在运行，避免多个录音进程互相抢麦克风。

锁文件只由创建它的录音实例清理；运行 `--check` 或 `--doctor` 不会误删正在录音实例的锁。异常退出时，语贴会恢复可能处于暂停状态的录音进程，并按 `SIGINT`、`SIGTERM`、`SIGKILL` 顺序限时回收，降低残留录音进程的风险。

模型选择建议：

- `tiny`：最快，准确率最低
- `base`：较快，适合短句和轻量机器
- `small`：速度和准确率比较均衡
- `medium`：更准，但更慢
- `large-v3-turbo`：准确率最高，但 CPU 上较慢，需要 GPU 加速才能实用

## 安装后文件位置

安装脚本会写入：

```text
~/.local/bin/voice-to-text
~/.local/share/applications/voice-to-text.desktop
~/.local/share/voice-to-text/voice-to-text-ui.py   # GTK4 界面（录音窗/结果窗/错误窗）
```

`voice-to-text --setup` 会创建独立 Python 环境。SenseVoice 依赖的 `kaldi-native-fbank` 等包只有 Python 3.12 的轮子，所以单独建一个环境隔离，不污染 Whisper 环境：

```text
~/.local/share/voice-to-text/venv             # whisper 后端
~/.local/share/voice-to-text/venv-sensevoice  # sensevoice 后端（Python 3.12）
```

最近转写历史位于：

```text
~/.local/share/voice-to-text/history.tsv
```

Whisper 模型通常会缓存到 Hugging Face 缓存目录，例如：

```text
~/.cache/huggingface
```

语贴启动转写时会优先解析并使用本地 Hugging Face 缓存里的 `faster-whisper` 模型快照。如果本地已有模型，会直接传本地路径并启用 `local_files_only`，避免每次重启后因为无法访问 Hugging Face 而卡在联网检查。只有第一次使用某个模型、切换到未缓存模型，或缓存被删除时，才需要联网下载。

SenseVoice 模型缓存在 ModelScope 缓存目录：

```text
~/.cache/modelscope/models/iic--SenseVoiceSmall
```

语贴会把本地模型目录直接传给 `funasr-onnx`，所以日常转写不会再向 ModelScope 查询更新，离线也能用。如果首次安装时只下到了 PyTorch 版模型，`--setup` 会自动导出并量化 ONNX（首次需要临时安装 torch 和 funasr，仅一次）。

临时录音、转写文本和错误日志位于：

```text
${XDG_RUNTIME_DIR}/voice-to-text
```

这个运行时目录重启后会清空，这是正常行为。

## 故障排查

如果没有开始录音，先确认 `ffmpeg` 能访问默认麦克风：

```bash
ffmpeg -f pulse -i default -t 3 test.wav
```

也可以运行完整环境检查：

```bash
voice-to-text --check
```

如果需要更详细的诊断报告：

```bash
voice-to-text --doctor
```

如果转写失败，查看错误日志：

```text
${XDG_RUNTIME_DIR}/voice-to-text/error-*.log
```

如果录音启动失败，查看录音错误日志：

```text
${XDG_RUNTIME_DIR}/voice-to-text/recording-error-*.log
```

如果剪贴板没有内容：

- Wayland 用户确认安装了 `wl-clipboard`
- X11 用户确认安装了 `xclip` 或 `xsel`
- 确认当前会话里存在 `WAYLAND_DISPLAY` 或 `DISPLAY`

如果第一次运行很慢，通常是在下载或加载 Whisper 模型。等第一次完成后，再次使用会直接复用本地缓存。如果重启后不开代理仍然很慢，先确认模型缓存目录还在：

```text
~/.cache/huggingface/hub/models--Systran--faster-whisper-medium
```

如果你看到 CUDA 相关错误，这个项目默认已经强制使用 CPU `int8`，通常不需要安装 CUDA。请确认你使用的是当前版本脚本。

## 和其他听写工具的区别

Linux 上已经有更成熟的听写项目，比如 `nerd-dictation`。这个项目的目标更窄：

- 不做常驻服务
- 不追求完整听写系统
- 不默认模拟键盘输入
- 优先把识别结果放进剪贴板
- 优先服务“说一句 prompt，然后粘贴给 AI”的场景

这种设计牺牲了一些自动化程度，但换来的是简单、透明、容易排错。

## 路线图

可能会继续做的改进：

- 按一次开始、再按一次停止的 toggle 模式
- 可选自动粘贴到当前窗口
- GNOME/KDE/sway/hyprland 快捷键示例
- 持续扩充计算机术语和个人纠错词库
- 基于真实使用反馈筛选默认术语，而不是盲目堆大词库
- GPU 加速：本机只有 CUDA 13，而 `ctranslate2` 需要的 CUDA 12 运行库对不上，暂缓；等版本能对齐再开
- 预热常驻服务：降低每次开口前等待模型加载的延迟（目前刻意不做常驻，保持零后台进程）

## 卸载

删除安装文件：

```bash
rm -f ~/.local/bin/voice-to-text
rm -f ~/.local/share/applications/voice-to-text.desktop
rm -rf ~/.local/share/voice-to-text
```

如果你也想删除已下载的模型缓存，需要清理 Hugging Face 缓存目录。注意这个目录可能被其他项目共用。

## License

MIT

---

## English

**语贴 voice-to-text** is a tiny Linux desktop voice input helper.

The Chinese name means turning speech into text that you can paste wherever you are working.

Press a shortcut, speak, stop recording, and it transcribes your speech locally with Whisper. The result is copied to the clipboard so you can paste it into any chat box, editor, browser, or terminal workflow.

It was originally built for fast voice conversations with AI tools. It does not try to be a full dictation suite. It simply turns one short voice note into text as quickly and transparently as possible.

## Who It Is For

- People who often talk to AI coding or chat tools
- Linux desktop users who want quick voice prompts
- Wayland users who prefer clipboard-based workflows
- Users who want local speech recognition by default

## Features

- Local transcription with `SenseVoiceSmall` (INT8) by default, `faster-whisper` as fallback
- Switchable backend via `VOICE_TO_TEXT_BACKEND=auto|sensevoice|whisper`
- Automatic language detection by default, suitable for mixed Chinese and English
- Chinese output is converted to Simplified Chinese when possible
- CPU `int8` mode by default, no CUDA required
- Wayland clipboard support via `wl-copy`
- X11 fallback via `xclip` or `xsel`
- Desktop notifications via `notify-send`
- Chinese recording and result windows built with Python + GTK4/libadwaita: native Wayland, follows display scaling (HiDPI) and the system color scheme
- Recording window with elapsed time, pause/resume, stop, and live audio visualization; result window copies to the clipboard
- Silent recordings are detected and reported instead of sending noise to the ASR backend; falls back to `zenity` when GTK4 is unavailable
- No background daemon
- Personal terminology and correction files
- Small local transcript history

## Install

Arch Linux example:

```bash
sudo pacman -S ffmpeg uv zenity libnotify wl-clipboard python-gobject python-cairo gtk4 libadwaita
```

Install the tool:

```bash
git clone https://github.com/chenshifanjian/voice-to-text.git
cd voice-to-text
./install.sh
voice-to-text --setup
```

Run it:

```bash
voice-to-text
```

Speak, watch the waveform, pause/resume if needed, stop recording, then paste with `Ctrl+V`.

## Configuration

Change language:

```bash
VOICE_TO_TEXT_LANGUAGE=en voice-to-text
```

Change backend (default `auto`: use SenseVoice when installed, otherwise Whisper):

```bash
VOICE_TO_TEXT_BACKEND=whisper voice-to-text
```

On the same 16-core CPU machine, `SenseVoiceSmall` transcribes an 8-second Chinese clip end to end in about 2.2 seconds versus about 11 seconds for Whisper `medium`, with better mixed Chinese/English accuracy. It has no `hotwords` support (the correction table covers those cases) and is slightly weaker on English technical terms; audio longer than 30 seconds is split on detected silence automatically.

Change the Whisper model (default is `medium`):

```bash
VOICE_TO_TEXT_MODEL=small voice-to-text
```

The default prompt is a short, natural example of what the transcript should look like, covering Simplified Chinese, English words, product names, and Arabic numerals. Whisper's `initial_prompt` is not an instruction list: imperative phrases like "please..." or "do not..." can get echoed back as part of the transcript, so the default prompt avoids them.

Hotwords only apply to the `whisper` backend; `SenseVoice` ignores them, so fix recurring mistakes with the correction table below.

The installer also ships a starter computer terminology list and literal correction table. Personal terms are loaded first, then safe built-in terms fill the remaining slots up to `40`. They are passed to `faster-whisper` as `hotwords`, instead of being appended directly to the prompt, to reduce interference with ordinary Chinese and number dictation:

```text
~/.local/share/voice-to-text/computer-terms.txt
~/.local/share/voice-to-text/replacements.tsv
```

Add personal terms and corrections here:

```text
~/.config/voice-to-text/terms.txt
~/.config/voice-to-text/replacements.tsv
```

The starter list is intentionally bounded. Add project-specific words locally, and contribute broadly useful developer, AI, Linux desktop, and correction terms through issues or pull requests.

Short all-caps protocol or encoding tokens are filtered out of default hotwords to reduce hallucinated repeats such as `UDP, UDP-8...`. Decoding also uses repetition controls, and obvious repeated technical-token output is filtered after transcription.

The recording window follows the system color scheme. Force it when needed:

```bash
VOICE_TO_TEXT_THEME=light voice-to-text   # auto | light | dark
```

The default visualization is a waveform. You can switch to spectrum bars:

```bash
VOICE_TO_TEXT_VISUALIZER=spectrum voice-to-text
```

Available visualizers: `waveform`, `spectrum`.

Pick the UI backend with `VOICE_TO_TEXT_UI=auto|gtk|zenity|none`; `none` records in the terminal and stops on Enter, which is what you want over SSH. `VOICE_TO_TEXT_MAX_SECONDS` (default 3600) caps a single take, and `VOICE_TO_TEXT_KEEP_FILES` (default 20) prunes old recordings and transcripts in `${XDG_RUNTIME_DIR}/voice-to-text`.

Voice activity is gated on **effective speech duration**, not on mean volume: one pass of `volumedetect,silencedetect=noise=-38dB:d=0.25`, and at least 0.3 s of non-silence is required — otherwise the take is reported as "没听到声音" (with the measured seconds and dB levels) instead of being sent to the ASR backend. Calibrated on real recordings: full sentences 1.5–5.0 s, a single short utterance 0.38–0.43 s, quiet-room noise 0.07 s, synthetic silence 0.00 s. A mean-volume threshold was tried first and killed genuine speech, because the silent gaps dominate the average.

Transcription prefers local Hugging Face cache snapshots for `faster-whisper` models. If a cached model exists, the script passes the local snapshot path and enables `local_files_only`, avoiding slow network checks after reboot when Hugging Face is unreachable. A network connection is only needed for the first use of a model, switching to an uncached model, or after deleting the cache.

Useful commands:

```bash
voice-to-text --init-config
voice-to-text --doctor
voice-to-text --history
voice-to-text --copy-last
```

## niri Shortcut

Add this inside your `binds { ... }` block:

```kdl
Mod+Alt+Space hotkey-overlay-title="Voice to text" { spawn "voice-to-text"; }
```

Reload config:

```bash
niri msg action load-config-file
```

To open the `语贴` window as floating in niri:

```kdl
window-rule {
    match app-id=r#"^dev\.inkblade\.VoiceToTextUI$"#
    open-floating true
    geometry-corner-radius 14
    clip-to-geometry true
    border { off }
    focus-ring { off }
}
window-rule {
    match app-id=r#"^dev\.inkblade\.VoiceToTextUI$"# title=r#"录音"#
    default-floating-position x=24 y=24 relative-to="bottom-right"
}
```

## Troubleshooting

Error logs are written to:

```text
${XDG_RUNTIME_DIR}/voice-to-text/error-*.log
```

To test microphone access:

```bash
ffmpeg -f pulse -i default -t 3 test.wav
```

For Wayland clipboard support, install `wl-clipboard`. For X11, install `xclip` or `xsel`.

## License

MIT

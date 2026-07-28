# 语贴 voice-to-text

一个很小的 Linux 桌面语音输入工具。

中文名叫 **语贴**：语音变成文字，然后贴到你正在使用的地方。

按下快捷键，说一句话，停止录音。它会用本地 Whisper 模型把语音转成文字，并复制到剪贴板。接下来你只需要在聊天框、编辑器或浏览器输入框里按 `Ctrl+V`。

这个工具最初是为“和 AI 快速语音交流”做的：不需要打开复杂应用，不需要常驻一个大服务，也不需要把录音发到云端。它只做一件事：把你刚说的话，尽快变成可以粘贴的文字。

## 适合谁

- 经常和 ChatGPT、Claude、OpenCode、MiMoCode 等 AI 工具对话的人
- 想用语音快速写 prompt、笔记、搜索词或短消息的人
- 使用 Linux 桌面，尤其是 Wayland/niri/sway/hyprland 的用户
- 希望语音识别尽量本地完成，不想默认依赖在线服务的人

如果你需要完整的连续听写、自动标点修正、托盘应用、历史记录或富 GUI，这个项目还不是那个形态。它更像一个简单、透明、可改的桌面自动化小工具。

## 功能特性

- 本地语音识别：使用 `faster-whisper`
- 默认自动识别语言，适合中英混合短句
- 中文输出会尽量转换为简体
- 默认 CPU `int8` 模式，不需要 CUDA
- Wayland 剪贴板：`wl-copy`
- X11 剪贴板回退：`xclip` 或 `xsel`
- 桌面通知：`notify-send`
- 停止录音弹窗：`zenity`
- 不常驻后台，按需启动
- 临时录音和日志放在 `${XDG_RUNTIME_DIR}/voice-to-text`

## 快速开始

安装系统依赖。Arch Linux 示例：

```bash
sudo pacman -S ffmpeg uv zenity libnotify wl-clipboard
```

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
3. 点击弹窗里的停止按钮。
4. 等待转写完成。
5. 到目标输入框按 `Ctrl+V` 粘贴。

第一次转写时会下载 Whisper 模型，可能会慢一点。模型下载完成后，后续会直接复用缓存。

如果只是想检查环境是否正常，不开始录音，可以运行：

```bash
voice-to-text --check
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

## 配置

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

默认模型是 `small`。如果你想更快，可以换成 `base`：

```bash
VOICE_TO_TEXT_MODEL=base voice-to-text
```

默认 beam size 是 `5`，准确率更好但会比贪心解码慢一点。可以调整：

```bash
VOICE_TO_TEXT_BEAM_SIZE=3 voice-to-text
```

默认会给 Whisper 一段中英混合提示，帮助它保留英文单词、技术名词和产品名。可以覆盖：

```bash
VOICE_TO_TEXT_INITIAL_PROMPT="普通话和 English 混合输入，中文用简体。" voice-to-text
```

安装脚本会额外安装一份计算机专有名词 starter 词库，来源参考了 Wikipedia 的计算机科学、计算机硬件和人工智能术语表，并补充了常见开发工具、AI 工具和 Linux 桌面词。运行时会把前 `120` 个词加入 Whisper 提示词，基本不增加识别时间：

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
VOICE_TO_TEXT_TERMS_LIMIT=180 voice-to-text
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

建议优先贡献这类内容：

- 高频开发工具、AI 工具和开源项目名
- 中英混合场景里常被拆错的词，比如 `GitHub`、`README`、`OpenCode`
- Linux 桌面、终端、包管理和开发环境相关词
- 确认稳定的错词到正词映射

不建议把非常长、非常冷门或只在个人项目里出现一次的词放进默认词库。词库太大不会线性提升准确率，反而可能削弱提示效果；这类词更适合放进个人 `terms.txt`。

默认从 PulseAudio/PipeWire 的 `default` 麦克风录音。特殊情况下可以覆盖录音后端：

```bash
VOICE_TO_TEXT_AUDIO_FORMAT=pulse VOICE_TO_TEXT_AUDIO_SOURCE=default voice-to-text
```

脚本带单实例保护：如果一次录音还没结束，再次触发快捷键会提示已有实例在运行，避免多个录音进程互相抢麦克风。

模型选择建议：

- `tiny`：最快，准确率最低
- `base`：较快，适合短句和轻量机器
- `small`：默认选择，速度和准确率比较均衡
- `medium`：更准，但更慢，CPU 上等待时间会明显增加

## 安装后文件位置

安装脚本会写入：

```text
~/.local/bin/voice-to-text
~/.local/share/applications/voice-to-text.desktop
```

`voice-to-text --setup` 会创建独立 Python 环境：

```text
~/.local/share/voice-to-text/venv
```

Whisper 模型通常会缓存到 Hugging Face 缓存目录，例如：

```text
~/.cache/huggingface
```

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

如果第一次运行很慢，通常是在下载或加载 Whisper 模型。等第一次完成后，再次使用会快很多。

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
- 最近几次转写历史
- 更友好的安装检查
- GNOME/KDE/sway/hyprland 快捷键示例
- 持续扩充计算机术语和个人纠错词库
- 基于真实使用反馈筛选默认术语，而不是盲目堆大词库

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

- Local transcription with `faster-whisper`
- Automatic language detection by default, suitable for mixed Chinese and English
- Chinese output is converted to Simplified Chinese when possible
- CPU `int8` mode by default, no CUDA required
- Wayland clipboard support via `wl-copy`
- X11 fallback via `xclip` or `xsel`
- Desktop notifications via `notify-send`
- Stop-recording dialog via `zenity`
- No background daemon

## Install

Arch Linux example:

```bash
sudo pacman -S ffmpeg uv zenity libnotify wl-clipboard
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

Speak, stop recording, then paste with `Ctrl+V`.

## Configuration

Change language:

```bash
VOICE_TO_TEXT_LANGUAGE=en voice-to-text
```

Change model:

```bash
VOICE_TO_TEXT_MODEL=base voice-to-text
```

The installer also ships a starter computer terminology list and literal correction table:

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

## niri Shortcut

Add this inside your `binds { ... }` block:

```kdl
Mod+Alt+Space hotkey-overlay-title="Voice to text" { spawn "voice-to-text"; }
```

Reload config:

```bash
niri msg action load-config-file
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

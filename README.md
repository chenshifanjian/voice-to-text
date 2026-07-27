# voice-to-text

A small Linux desktop voice input helper. It records from the default microphone, transcribes speech locally with `faster-whisper`, copies the result to the clipboard, and shows desktop notifications.

It was built for quick voice prompts: press a shortcut, speak, stop recording, then paste the recognized text into any chat or editor.

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

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"

mkdir -p "$BIN_DIR" "$APP_DIR"
install -m 0755 "$ROOT_DIR/voice-to-text" "$BIN_DIR/voice-to-text"

cat > "$APP_DIR/voice-to-text.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Voice to Text
Name[zh_CN]=语音转文字
Comment=Record voice, transcribe it, and copy text to clipboard
Exec=$BIN_DIR/voice-to-text
Terminal=false
Categories=Utility;
EOF

printf 'Installed voice-to-text to %s\n' "$BIN_DIR/voice-to-text"
printf 'Install the ASR backend with: %s --setup\n' "$BIN_DIR/voice-to-text"

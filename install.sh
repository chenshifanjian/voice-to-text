#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/voice-to-text"

mkdir -p "$BIN_DIR" "$APP_DIR" "$DATA_DIR"
install -m 0755 "$ROOT_DIR/voice-to-text" "$BIN_DIR/voice-to-text"
install -m 0644 "$ROOT_DIR/data/computer-terms.txt" "$DATA_DIR/computer-terms.txt"
install -m 0644 "$ROOT_DIR/data/replacements.tsv" "$DATA_DIR/replacements.tsv"

cat > "$APP_DIR/voice-to-text.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Voice to Text
Name[zh_CN]=语贴
Comment=Record voice, transcribe it, and copy text to clipboard
Exec=$BIN_DIR/voice-to-text
Terminal=false
Categories=Utility;
EOF

printf 'Installed voice-to-text to %s\n' "$BIN_DIR/voice-to-text"
printf 'Installed starter terminology to %s\n' "$DATA_DIR"
printf 'Install the ASR backend with: %s --setup\n' "$BIN_DIR/voice-to-text"

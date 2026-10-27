#!/usr/bin/env bash
# Report what this machine has and lacks. Installs nothing.
# Usage: bash scripts/check_env.sh [premiere]
ok() { printf '  ok      %s\n' "$1"; }
miss() { printf '  MISSING %s  ->  %s\n' "$1" "$2"; }

case "$(uname -s)" in
  Darwin) OS=mac ;;
  MINGW*|MSYS*|CYGWIN*) OS=win ;;
  *) OS=linux ;;
esac
inst() { case $OS in mac) echo "brew install $1" ;; win) echo "winget install $2" ;; *) echo "apt install $1" ;; esac; }

echo "OS: $OS ($(uname -m))"
if [ "$OS" = mac ] && [ "$(uname -m)" != arm64 ]; then
  echo "  STOP: Intel Mac. WhisperX's torch has no build for it."; exit 1
fi

command -v ffmpeg  >/dev/null && ok ffmpeg  || miss ffmpeg  "$(inst ffmpeg Gyan.FFmpeg)"
command -v ffprobe >/dev/null && ok ffprobe || miss ffprobe "(ships with ffmpeg)"
command -v git     >/dev/null && ok git     || miss git     "$(inst git Git.Git)"
if command -v uv >/dev/null; then
  ok uv
  if py=$(uv python find 3.11 2>/dev/null); then ok "python 3.11 ($py)"; else miss "python 3.11" "uv python install 3.11"; fi
else
  miss uv "$(inst uv astral-sh.uv)"
fi

if [ "$1" = premiere ]; then
  if command -v node >/dev/null && [ "$(node -p 'process.versions.node.split(".")[0]')" -ge 22 ]; then
    ok "node $(node -v)"
  else
    miss "node 22+" "$(inst node OpenJS.NodeJS.LTS)"
  fi
fi

if [ "$OS" = win ]; then
  if echo test > .write-test 2>/dev/null; then rm -f .write-test; ok "folder writable"
  else echo "  BLOCKED: Controlled Folder Access blocks this folder. Allow it or move the folder."; fi
fi

venv=~/.cache/video-editor/whisperx-venv
[ -d "$venv" ] && ok "whisperx venv ($venv)" || echo "  todo    whisperx venv (created on first transcribe)"

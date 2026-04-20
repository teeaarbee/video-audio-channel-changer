#!/usr/bin/env bash
# Audio Track Swapper — macOS launcher (double-click to run)
set -e

cd "$(dirname "$0")"

# Pick a Python interpreter
if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    osascript -e 'display alert "Python not found" message "Install Python 3.9+ from https://www.python.org or via Homebrew: brew install python" as critical'
    exit 1
fi

# Warn if ffmpeg is missing (the app will also warn, but catch it early here)
if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
    osascript -e 'display alert "ffmpeg not found" message "Install ffmpeg first:\n\n  brew install ffmpeg\n\nThen double-click this launcher again." as critical' || true
    exit 1
fi

# Create venv on first run
if [ ! -d ".venv" ]; then
    echo "First run — creating virtual environment…"
    "$PY" -m venv .venv
    ./.venv/bin/pip install --upgrade pip >/dev/null
    ./.venv/bin/pip install -r requirements.txt
fi

# Make sure dependencies are present (covers requirements.txt updates)
if ! ./.venv/bin/python -c "import PySide6" >/dev/null 2>&1; then
    ./.venv/bin/pip install -r requirements.txt
fi

exec ./.venv/bin/python main.py

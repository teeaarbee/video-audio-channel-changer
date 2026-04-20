@echo off
REM Audio Track Swapper — Windows launcher (double-click to run)
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM Pick a Python interpreter (prefer the launcher `py`, fall back to `python`)
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo Python 3.9+ not found.
    echo Install it from https://www.python.org/downloads/ ^(check "Add python.exe to PATH"^).
    pause
    exit /b 1
)

REM Check ffmpeg / ffprobe
where ffmpeg >nul 2>nul
if errorlevel 1 (
    echo ffmpeg is not on PATH.
    echo Install it via:  winget install Gyan.FFmpeg
    echo Or download from https://ffmpeg.org/download.html and add the bin\ folder to PATH.
    pause
    exit /b 1
)
where ffprobe >nul 2>nul
if errorlevel 1 (
    echo ffprobe is not on PATH ^(usually ships with ffmpeg^).
    pause
    exit /b 1
)

REM Create venv on first run
if not exist ".venv\Scripts\python.exe" (
    echo First run - creating virtual environment...
    %PY% -m venv .venv
    if errorlevel 1 ( pause & exit /b 1 )
    ".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 ( pause & exit /b 1 )
)

REM Ensure dependencies are present
".venv\Scripts\python.exe" -c "import PySide6" >nul 2>nul
if errorlevel 1 (
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 ( pause & exit /b 1 )
)

REM Launch (use pythonw to avoid a console window staying open)
start "" ".venv\Scripts\pythonw.exe" main.py
exit /b 0

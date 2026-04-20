# Audio Track Swapper

A cross-platform desktop app (macOS · Windows · Linux) for **visually reordering, swapping, and setting the default audio track** in videos that contain multiple audio streams — with **batch support** and a modern dark GUI.

Processing is **lossless**: ffmpeg `stream-copy` remapping, no re-encoding, no quality loss, no long wait for big files. Swapping a 1.4 GB 4K episode takes seconds.

![python](https://img.shields.io/badge/python-3.9%2B-blue) ![qt](https://img.shields.io/badge/Qt-PySide6-41cd52) ![ffmpeg](https://img.shields.io/badge/ffmpeg-required-green) ![platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey)

---

## Why this exists

Multi-audio videos (multiple dubs, director's commentary, descriptive audio, alt mixes) are common, but many players stubbornly default to the *first* track. Re-muxing with the right default or a different order usually means command-line `ffmpeg` incantations. This app is the visual shortcut:

- drag audio tracks around like cards,
- hit **▶** to hear each one (critical when tracks lack language tags),
- hit **★** to pick the default,
- apply the same reorder to a whole folder/season at once,
- get lossless output in seconds.

---

## Features

- **Modern GUI** — PySide6 (Qt 6), dark theme, rounded cards, drag-and-drop reorder.
- **Visual track cards** — per-track codec, language, channel layout, sample rate, bitrate.
- **Preview button (▶)** — plays ~6 seconds of a single track via `ffplay`. Essential when tracks have no language metadata (e.g. all labeled "USP Sound Handler").
- **Default chooser (★)** — set which track a player should pick first.
- **Quick swap** dropdowns — "Track 1 ⇄ Track 3".
- **Drag to reorder** — rearrange tracks freely, any permutation.
- **Batch mode** — drag an entire folder; "Apply to all files" uses one reorder for every file (ideal for a whole season with matching track layouts).
- **Lossless stream copy** — no re-encode, no generational loss. Verified byte-identical.
- **Reversible** — run the same swap again and you're back to the original.
- **Three output modes**
  1. Same folder with suffix (default, safe)
  2. Custom output folder
  3. Overwrite originals in place (with confirmation dialog)
- **Live progress** — overall + per-file progress, optional ffmpeg log pane, cancel button.
- **Supported containers** — `.mp4 .mkv .mov .m4v .avi .webm .ts .mts .m2ts` (anything ffmpeg can mux).

---

## Screenshots

Drop files in, reorder the cards, hit **Apply & Process**:

```
┌────────────────────────────────────────────────────────────────────────┐
│ Audio Track Swapper    Swap audio tracks in videos — lossless, batch…  │
│                                     [＋ Add files] [＋ Add folder] [Clear] │
├────────────────┬───────────────────────────────────────────────────────┤
│ Files     [4]  │ The Boys_S05E03_… (3 of 6 tracks reordered)          │
│ ● S05E01.mp4   │                                                       │
│ ● S05E02.mp4   │ Quick: [Track 1 ▾] ⇄ [Track 2 ▾] [Swap] [Reset]      │
│ ● S05E03.mp4   │                                   [x] Apply to all   │
│ ● S05E04.mp4   │ ┌─────────────────────────────────────────────────┐  │
│                │ │ 1  Track 2 — USP Sound Handler   [AAC][EN][2ch] ▶★│ │
│                │ │ 2  Track 1 — USP Sound Handler   [AAC][EN][2ch] ▶★│ │
│                │ │ 3  Track 3 — USP Sound Handler   [AAC][—][2ch] ▶★ │ │
│                │ └─────────────────────────────────────────────────┘  │
│                │ Output: [Same folder, add suffix ▾]  Suffix [_swapped]│
│                │ [Apply & Process]  [■■■■■□□□] Processing 2/4          │
└────────────────┴───────────────────────────────────────────────────────┘
```

---

## Installation

### Prerequisites

- **Python 3.9 or newer**
- **ffmpeg + ffprobe** on `PATH`
- (optional but recommended) **ffplay** — ships with ffmpeg, enables the ▶ preview button

Check you have everything:

```bash
python3 --version
ffmpeg -version
ffprobe -version
ffplay -version   # optional
```

### Install ffmpeg

| Platform | Command |
|---|---|
| **macOS** (Homebrew) | `brew install ffmpeg` |
| **Windows** (winget) | `winget install Gyan.FFmpeg` |
| **Windows** (Chocolatey) | `choco install ffmpeg-full` |
| **Windows** (manual) | Download from [ffmpeg.org/download.html](https://ffmpeg.org/download.html), extract, add the `bin/` folder to your `PATH`. |
| **Linux** (Debian/Ubuntu) | `sudo apt install ffmpeg` |
| **Linux** (Fedora) | `sudo dnf install ffmpeg` |
| **Linux** (Arch) | `sudo pacman -S ffmpeg` |

### Install the app

```bash
git clone https://github.com/teeaarbee/video-audio-channel-changer.git
cd video-audio-channel-changer
```

#### Option A — virtual environment (recommended)

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell):**
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Windows (cmd.exe):**
```cmd
py -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
```

#### Option B — global install

```bash
pip install -r requirements.txt
```

---

## Running

```bash
python3 main.py            # macOS / Linux
py main.py                 # Windows
```

If you used a virtual environment, make sure it's activated first.

On first launch the app checks for `ffmpeg` and `ffprobe`. If either is missing you'll see a warning dialog — install them and relaunch.

---

## How to use

### One file

1. Click **＋ Add files** (or drag a file onto the left panel).
2. Select the file in the Files list. Its audio tracks appear as cards on the right.
3. Identify tracks:
   - Read the codec / language / channel badges.
   - Click **▶** on a card to hear ~6 s of that track. This is the killer feature when tracks have no language metadata.
4. Change the order:
   - **Drag a card** up or down to reorder.
   - Or use **Quick swap**: pick two tracks from the dropdowns → **Swap**.
   - Click **★** on a card to mark it as the default track (what a player picks first).
5. **Apply & Process**. Output goes to the same folder with `_swapped` suffix by default.

### Many files (a whole season)

1. Click **＋ Add folder** and pick the folder. Every supported video inside (recursively) is added.
2. Select any one file and rearrange its tracks.
3. Tick **Apply to all files**. The same order/default is applied to every file.
   - Files whose audio-track count doesn't match are safely skipped (marked in the list).
4. **Apply & Process**. All files are processed sequentially with live progress.

### Reverting

Run the same swap again. Because the operation is byte-perfect lossless, a second round-trip restores the original file exactly.

### Output modes

| Mode | Behavior |
|---|---|
| **Same folder, add suffix** | `movie.mp4` → `movie_swapped.mp4` in the same directory (default, safe). Suffix is editable. |
| **Custom folder…** | Pick any folder; outputs are written there. |
| **Overwrite original** | Writes to a temp sibling file, then atomically renames over the original. Confirmation dialog required. |

---

## How it works

ffmpeg is invoked once per file with a stream-copy remap:

```
ffmpeg -i input.mp4 \
       -map 0:v -map 0:a:1 -map 0:a:0 -map 0:a:2 \
       -map 0:s? -map 0:t? \
       -c copy -map_metadata 0 -map_chapters 0 \
       -disposition:a:0 default -disposition:a:1 0 ... \
       output.mp4
```

- `-c copy` — no re-encoding. Audio bytes are copied verbatim.
- All video, subtitle, attachment, and data streams are preserved.
- Metadata and chapters carry over.
- `-disposition` is reset so the chosen track is marked as default.

### Verified losslessness

Swapping audio tracks 1 and 2 of a real multi-track MP4:

```
source  a:0  MD5=214e5e52e0ffaa56a2726f161ea8b70d
source  a:1  MD5=0a777b6e4e3220abb2de660a4bf9597b
output  a:0  MD5=0a777b6e4e3220abb2de660a4bf9597b   ← source's a:1
output  a:1  MD5=214e5e52e0ffaa56a2726f161ea8b70d   ← source's a:0
```

---

## Project structure

```
video-audio-channel-changer/
├── main.py                     # Entry point
├── requirements.txt            # PySide6
├── app/
│   ├── probe.py                # ffprobe wrapper, Stream / ProbeResult dataclasses
│   ├── remap.py                # ffmpeg command builder + runner with progress
│   ├── worker.py               # QThread workers for probe and batch remap
│   └── gui/
│       ├── main_window.py      # Top-level window, file list, batch logic
│       ├── track_panel.py      # Drag-to-reorder stack of track cards
│       ├── track_card.py       # Draggable QFrame per audio track
│       └── style.py            # QSS dark theme
└── README.md
```

---

## Troubleshooting

**"ffmpeg not found on PATH"**
Install ffmpeg (see [Install ffmpeg](#install-ffmpeg)) and restart your shell so `PATH` picks it up. Verify with `ffmpeg -version`.

**▶ preview button does nothing**
`ffplay` is missing. It normally ships with ffmpeg — if you installed a stripped-down build, reinstall the full package (`brew install ffmpeg`, Gyan.FFmpeg "full" build, `ffmpeg-full` on Chocolatey).

**"skipped: audio-track count differs"**
You enabled *Apply to all files* but one file has a different number of audio tracks. That file is skipped — process it individually.

**Output file won't play one of the tracks**
Some older players hide non-default tracks. Click **★** on the track you want as default and re-run. Or check your player's audio-track menu (usually right-click → Audio Track).

**GUI complains about Qt platform plugin on Linux**
Install system Qt dependencies: `sudo apt install libxcb-cursor0 libxkbcommon-x11-0` (Debian/Ubuntu).

---

## License

MIT

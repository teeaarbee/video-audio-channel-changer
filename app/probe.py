from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Stream:
    index: int
    codec_type: str
    codec_name: str = ""
    language: str = ""
    title: str = ""
    channels: int = 0
    channel_layout: str = ""
    sample_rate: str = ""
    bit_rate: str = ""
    default: bool = False
    forced: bool = False
    attached_pic: bool = False
    width: int = 0
    height: int = 0
    raw: dict = field(default_factory=dict)

    @property
    def pretty_channels(self) -> str:
        if self.channel_layout:
            return self.channel_layout
        if self.channels:
            return f"{self.channels}ch"
        return ""


@dataclass
class ProbeResult:
    path: Path
    format_name: str
    duration: float
    size_bytes: int
    streams: list[Stream]

    @property
    def audio_streams(self) -> list[Stream]:
        return [s for s in self.streams if s.codec_type == "audio"]

    @property
    def video_streams(self) -> list[Stream]:
        return [s for s in self.streams if s.codec_type == "video"]

    @property
    def subtitle_streams(self) -> list[Stream]:
        return [s for s in self.streams if s.codec_type == "subtitle"]

    def audio_relative_index(self, stream: Stream) -> int:
        return self.audio_streams.index(stream)


class FfprobeError(RuntimeError):
    pass


def ensure_tools() -> tuple[str, str]:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise FfprobeError(
            "ffmpeg/ffprobe not found on PATH. Install via `brew install ffmpeg` (macOS) "
            "or download from https://ffmpeg.org/ (Windows) and ensure both are on PATH."
        )
    return ffmpeg, ffprobe


def probe(path: str | Path) -> ProbeResult:
    _, ffprobe = ensure_tools()
    path = Path(path)
    cmd = [
        ffprobe, "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", str(path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise FfprobeError(f"ffprobe failed: {proc.stderr.strip()}")
    data = json.loads(proc.stdout)

    streams: list[Stream] = []
    for s in data.get("streams", []):
        tags = s.get("tags", {}) or {}
        disp = s.get("disposition", {}) or {}
        streams.append(Stream(
            index=int(s["index"]),
            codec_type=s.get("codec_type", ""),
            codec_name=s.get("codec_name", ""),
            language=tags.get("language", "") or "",
            title=tags.get("title", "") or tags.get("handler_name", "") or "",
            channels=int(s.get("channels", 0) or 0),
            channel_layout=s.get("channel_layout", "") or "",
            sample_rate=str(s.get("sample_rate", "") or ""),
            bit_rate=str(s.get("bit_rate", "") or ""),
            default=bool(disp.get("default", 0)),
            forced=bool(disp.get("forced", 0)),
            attached_pic=bool(disp.get("attached_pic", 0)),
            width=int(s.get("width", 0) or 0),
            height=int(s.get("height", 0) or 0),
            raw=s,
        ))

    fmt = data.get("format", {}) or {}
    return ProbeResult(
        path=path,
        format_name=fmt.get("format_name", "") or "",
        duration=float(fmt.get("duration", 0) or 0),
        size_bytes=int(fmt.get("size", 0) or 0),
        streams=streams,
    )


def default_output_path(src: Path, suffix: str = "_swapped") -> Path:
    return src.with_name(f"{src.stem}{suffix}{src.suffix}")


LANG_FLAGS = {
    "eng": "EN", "en": "EN", "en-us": "EN",
    "hin": "HI", "hi": "HI",
    "tam": "TA", "ta": "TA",
    "tel": "TE", "te": "TE",
    "spa": "ES", "es": "ES",
    "fre": "FR", "fra": "FR", "fr": "FR",
    "ger": "DE", "deu": "DE", "de": "DE",
    "jpn": "JA", "ja": "JA",
    "kor": "KO", "ko": "KO",
    "por": "PT", "pt": "PT",
    "rus": "RU", "ru": "RU",
    "ara": "AR", "ar": "AR",
    "chi": "ZH", "zho": "ZH", "zh": "ZH",
    "ita": "IT", "it": "IT",
    "und": "—",
}


def language_badge(lang: Optional[str]) -> str:
    if not lang:
        return "—"
    return LANG_FLAGS.get(lang.lower(), lang.upper()[:3])

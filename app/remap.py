from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Optional

from .probe import ProbeResult, Stream, ensure_tools


@dataclass
class RemapPlan:
    """
    audio_order: list of ORIGINAL audio positions (0-based, relative to audio streams)
    in the order they should appear in the output.
    e.g. for 3 audio tracks [0,1,2], swapping 0<->1 -> [1,0,2]
    """
    audio_order: list[int]
    output_path: Path
    default_audio: int = 0  # index within new audio order to mark default
    overwrite: bool = True


def build_ffmpeg_cmd(ffmpeg: str, src: Path, probe: ProbeResult, plan: RemapPlan) -> list[str]:
    cmd = [ffmpeg, "-hide_banner", "-nostdin", "-y" if plan.overwrite else "-n", "-i", str(src)]

    # Video streams first (keep original order incl. cover art / attached_pic)
    for s in probe.video_streams:
        cmd += ["-map", f"0:{s.index}"]

    # Audio streams in new order
    for a_pos in plan.audio_order:
        cmd += ["-map", f"0:a:{a_pos}"]

    # Subtitles
    for s in probe.subtitle_streams:
        cmd += ["-map", f"0:{s.index}"]

    # Data / attachments (fonts, chapters come via -map_chapters)
    for s in probe.streams:
        if s.codec_type in ("data", "attachment"):
            cmd += ["-map", f"0:{s.index}"]

    cmd += [
        "-c", "copy",
        "-map_metadata", "0",
        "-map_chapters", "0",
    ]

    # Reset audio dispositions and set a new default so players pick the intended track
    n_audio = len(plan.audio_order)
    for i in range(n_audio):
        disp = "default" if i == plan.default_audio else "0"
        cmd += [f"-disposition:a:{i}", disp]

    cmd += [str(plan.output_path)]
    return cmd


# ffmpeg progress lines look like:  out_time_ms=12345678  progress=continue  ...
_PROGRESS_RE = re.compile(r"out_time_ms=(\d+)")


def run_remap(
    src: Path,
    probe: ProbeResult,
    plan: RemapPlan,
    on_progress: Optional[Callable[[float], None]] = None,
    on_log: Optional[Callable[[str], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> None:
    ffmpeg, _ = ensure_tools()
    cmd = build_ffmpeg_cmd(ffmpeg, src, probe, plan)
    # Add machine-readable progress on stdout
    cmd = cmd[:1] + ["-progress", "pipe:1", "-nostats"] + cmd[1:]

    if on_log:
        on_log("$ " + " ".join(_quote(c) for c in cmd))

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    duration = probe.duration or 0.0
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            if cancel_check and cancel_check():
                proc.terminate()
                break
            m = _PROGRESS_RE.search(line)
            if m and duration > 0 and on_progress:
                secs = int(m.group(1)) / 1_000_000.0
                on_progress(min(1.0, secs / duration))
        proc.wait()
    finally:
        if proc.stderr:
            err = proc.stderr.read()
            if err and on_log:
                on_log(err.strip())

    if proc.returncode != 0 and not (cancel_check and cancel_check()):
        raise RuntimeError(f"ffmpeg exited with code {proc.returncode}")


def _quote(s: str) -> str:
    if any(ch in s for ch in " '\"\t"):
        return '"' + s.replace('"', '\\"') + '"'
    return s


def swap_pair(n_tracks: int, a: int, b: int) -> list[int]:
    order = list(range(n_tracks))
    order[a], order[b] = order[b], order[a]
    return order


def pretty_order(order: Iterable[int]) -> str:
    return " → ".join(str(i + 1) for i in order)

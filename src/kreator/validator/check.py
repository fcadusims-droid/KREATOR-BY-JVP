"""Render-integrity checks: does the output match the plan?"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from ..ffmpeg import ffmpeg_bin


def _parse_probe(stderr: str) -> dict:
    """Pull duration, stream presence and dimensions out of ``ffmpeg -i`` output."""
    dur = 0.0
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", stderr)
    if m:
        dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    # Two-plus digits per side so stream ids like "[0x1]" never match.
    dims = re.search(r": Video:.*?(\d{2,5})x(\d{2,5})", stderr)
    return {
        "duration": dur,
        "has_video": bool(re.search(r"Stream #\d+:\d+.*: Video:", stderr)),
        "has_audio": bool(re.search(r"Stream #\d+:\d+.*: Audio:", stderr)),
        "width": int(dims.group(1)) if dims else 0,
        "height": int(dims.group(2)) if dims else 0,
    }


def probe(video_path: str) -> dict:
    proc = subprocess.run([ffmpeg_bin(), "-i", video_path, "-hide_banner"],
                          capture_output=True, text=True)
    return _parse_probe(proc.stderr)


@dataclass
class ValidationReport:
    ok: bool
    duration: float
    expected: float
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"ok": self.ok, "duration": round(self.duration, 2),
                "expected": round(self.expected, 2), "issues": self.issues}


def _aspect_ok(width: int, height: int, aspect: str, tol: float = 0.02) -> bool:
    """Do the dimensions match ``aspect`` ("9:16") within ``tol``? The
    tolerance absorbs the even-rounding the encoder forces on crop widths."""
    if width <= 0 or height <= 0:
        return False
    aw, ah = aspect.split(":")
    return abs(width / height - int(aw) / int(ah)) <= tol


def validate_render(
    out_path: str, program, *, has_audio: bool, duration_tol: float = 1.5
) -> ValidationReport:
    """Check the rendered file matches ``program``: exists, right streams, a
    duration close to the plan (accounting for crossfade shortening), and —
    when the program reframes — the target aspect ratio."""
    issues: list[str] = []
    p = Path(out_path)
    expected = program.edited_duration - sum(t.duration for t in program.transitions)

    if not p.exists() or p.stat().st_size == 0:
        return ValidationReport(False, 0.0, expected, ["output file is missing or empty"])

    info = probe(out_path)
    if not info["has_video"]:
        issues.append("no video stream in the output")
    if has_audio and not info["has_audio"]:
        issues.append("expected an audio track but none was written")
    if abs(info["duration"] - expected) > duration_tol:
        issues.append(f"duration {info['duration']:.1f}s differs from the planned "
                      f"{expected:.1f}s")
    reframe = getattr(program, "reframe", None)
    if reframe and not _aspect_ok(info["width"], info["height"], reframe.aspect):
        issues.append(f"output is {info['width']}x{info['height']}, not the "
                      f"planned {reframe.aspect} aspect")

    return ValidationReport(not issues, info["duration"], expected, issues)

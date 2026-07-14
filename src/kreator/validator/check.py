"""Render-integrity checks: does the output match the plan?"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


def _ffmpeg_bin() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # pragma: no cover
        return "ffmpeg"


def _parse_probe(stderr: str) -> dict:
    """Pull duration + stream presence out of ``ffmpeg -i`` output."""
    dur = 0.0
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", stderr)
    if m:
        dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    return {
        "duration": dur,
        "has_video": bool(re.search(r"Stream #\d+:\d+.*: Video:", stderr)),
        "has_audio": bool(re.search(r"Stream #\d+:\d+.*: Audio:", stderr)),
    }


def probe(video_path: str) -> dict:
    proc = subprocess.run([_ffmpeg_bin(), "-i", video_path, "-hide_banner"],
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


def validate_render(
    out_path: str, program, *, has_audio: bool, duration_tol: float = 1.5
) -> ValidationReport:
    """Check the rendered file matches ``program``: exists, right streams, and
    a duration close to the plan (accounting for crossfade shortening)."""
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

    return ValidationReport(not issues, info["duration"], expected, issues)

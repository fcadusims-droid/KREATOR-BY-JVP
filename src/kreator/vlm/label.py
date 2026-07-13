"""Label sampled keyframes with a VLM, and turn the labels into a keep signal.

Ties the pieces together: keyframes (from ``keyframes.py``) → a frame image per
keyframe (ffmpeg) → a description (VLM backend) → a scene type (``classify``) →
a dense "keep" signal the condenser rescues on, exactly like speech presence.

The point: this rescues the *scenic / dialogue / briefing* moments the signal
proxy reads as boring, using the VLM only on the few sampled frames.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ..types import format_tc
from .classify import KEEP_TYPES, scene_type
from .keyframes import Keyframe


@dataclass(frozen=True)
class SceneLabel:
    time: float
    scene_type: str
    description: str

    def to_dict(self) -> dict[str, object]:
        return {"time": round(self.time, 2), "tc": format_tc(self.time),
                "scene_type": self.scene_type, "description": self.description}


def _ffmpeg_bin() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # pragma: no cover
        return "ffmpeg"


def _extract_frame(video_path: str, t: float, dest: str) -> bool:
    proc = subprocess.run(
        [_ffmpeg_bin(), "-y", "-ss", str(t), "-i", video_path,
         "-frames:v", "1", "-q:v", "3", dest],
        capture_output=True,
    )
    return proc.returncode == 0 and Path(dest).exists()


def label_keyframes(
    video_path: str, keyframes: list[Keyframe], backend, *, verbose: bool = False
) -> list[SceneLabel]:  # pragma: no cover - drives the heavy VLM
    """Describe and classify each keyframe. ``backend`` needs ``.describe(path)``."""
    labels: list[SceneLabel] = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, kf in enumerate(keyframes):
            frame = str(Path(tmp) / f"kf_{i}.jpg")
            if not _extract_frame(video_path, kf.time, frame):
                continue
            desc = backend.describe(frame)
            st = scene_type(desc)
            if verbose:
                print(f"  {format_tc(kf.time)} [{kf.reason}] -> {st}: {desc}")
            labels.append(SceneLabel(kf.time, st, desc))
    return labels


def visual_keep_series(
    labels: list[SceneLabel], times: list[float], *, window: float = 6.0
) -> list[float]:
    """A 0/1 presence signal: 1 near any keyframe whose scene type is worth
    keeping (action/scenic/dialogue). The condenser rescues these like speech."""
    if not times:
        return []
    presence = [0.0] * len(times)
    keeps = [lab.time for lab in labels if lab.scene_type in KEEP_TYPES]
    if not keeps:
        return presence
    for i, t in enumerate(times):
        if any(abs(t - kt) <= window for kt in keeps):
            presence[i] = 1.0
    return presence

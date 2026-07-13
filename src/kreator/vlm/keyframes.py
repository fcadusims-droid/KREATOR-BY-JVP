"""Signal-driven keyframe selection — choose the few frames worth a VLM label.

This is the frame-sampling the spec calls the single biggest cost lever. It runs
entirely on CPU from an already-computed SignalBundle; no model, no GPU. The
output is a small, deduplicated, time-ordered set of timestamps with a reason
tag, which a VLM backend (cloud API or small CPU model) then labels.

The reason tags matter: ``scenic_candidate`` marks a low-action-but-not-idle
stretch — the exact case (a beautiful pause, admiring the view) that motion and
audio energy read as "boring" and that only a VLM can rescue.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..editor.interest import interest_curve, percentile
from ..types import SignalBundle, format_tc


@dataclass(frozen=True)
class Keyframe:
    time: float
    reason: str  # "episode" | "scene_cut" | "interest_peak" | "scenic_candidate"

    def to_dict(self) -> dict[str, object]:
        return {"time": round(self.time, 2), "tc": format_tc(self.time),
                "reason": self.reason}


def select_keyframes(
    bundle: SignalBundle,
    *,
    max_frames: int = 30,
    min_gap: float = 6.0,
) -> list[Keyframe]:
    """Select up to ``max_frames`` keyframes, at least ``min_gap`` s apart.

    Priority order when deduping (a stronger reason wins a contested slot):
    interest_peak > episode > scenic_candidate > scene_cut.
    """
    times, interest = interest_curve(bundle)
    if not times:
        return []

    hi = percentile(interest, 0.90)
    lo = percentile(interest, 0.35)

    candidates: list[Keyframe] = []

    # Interest peaks — the clearly-active moments.
    peaks = _local_maxima(times, interest, threshold=hi)
    candidates += [Keyframe(t, "interest_peak") for t in peaks]

    # Scene-cut boundaries — where the scene changed.
    candidates += [Keyframe(t, "scene_cut") for t in bundle.scene_cuts]

    # Scenic candidates: sustained low-action-but-not-idle stretches. These are
    # what the signal proxy would cut and only a VLM can judge.
    candidates += [Keyframe(t, "scenic_candidate")
                   for t in _sustained_low(times, interest, lo)]

    # Evenly spread coverage so long uniform stretches still get a look.
    candidates += [Keyframe(t, "episode")
                   for t in _coverage(bundle.duration, every=max(min_gap * 4, 30.0))]

    return _dedup(candidates, min_gap, max_frames)


_PRIORITY = {"interest_peak": 0, "episode": 1, "scenic_candidate": 2, "scene_cut": 3}


def _dedup(frames: list[Keyframe], min_gap: float, cap: int) -> list[Keyframe]:
    ordered = sorted(frames, key=lambda k: (_PRIORITY.get(k.reason, 9), k.time))
    kept: list[Keyframe] = []
    for kf in ordered:
        if all(abs(kf.time - k.time) >= min_gap for k in kept):
            kept.append(kf)
        if len(kept) >= cap:
            break
    return sorted(kept, key=lambda k: k.time)


def _local_maxima(times: list[float], series: list[float], *, threshold: float) -> list[float]:
    out = []
    for i in range(1, len(series) - 1):
        if series[i] >= threshold and series[i] >= series[i - 1] and series[i] >= series[i + 1]:
            out.append(times[i])
    return out


def _sustained_low(times: list[float], series: list[float], lo: float,
                   *, min_run: float = 6.0) -> list[float]:
    """Midpoints of runs where interest sits in a low-but-nonzero band for at
    least ``min_run`` seconds — deliberate calm, not a one-frame dip."""
    out: list[float] = []
    start = None
    for i, t in enumerate(times):
        calm = 0.02 < series[i] <= lo
        if calm and start is None:
            start = t
        elif not calm and start is not None:
            if t - start >= min_run:
                out.append((start + t) / 2.0)
            start = None
    return out


def _coverage(duration: float, *, every: float) -> list[float]:
    out, t = [], every / 2.0
    while t < duration:
        out.append(t)
        t += every
    return out

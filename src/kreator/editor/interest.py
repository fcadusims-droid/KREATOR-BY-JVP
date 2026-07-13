"""The interest curve — a dense, whole-timeline "is this worth keeping?" score.

Unlike K Clipper, which only looks around trigger events, the editor needs an
opinion about *every* second of the video. This module turns the Signal
Layer's dense series into one smoothed interest value per time step.

Kept deliberately simple and deterministic: interest is a blend of visual
motion and audio energy, smoothed over a short window so a single-frame spike
doesn't carve out a one-second keep, and a brief dip inside an action scene
doesn't punch a hole in it.
"""

from __future__ import annotations

from ..types import SignalBundle


def _moving_average(xs: list[float], radius: int) -> list[float]:
    """Centered moving average with a half-window of ``radius`` samples."""
    if radius <= 0 or len(xs) <= 1:
        return list(xs)
    n = len(xs)
    out = [0.0] * n
    acc = 0.0
    # Prefix sums keep this O(n) rather than O(n·window).
    prefix = [0.0]
    for x in xs:
        acc += x
        prefix.append(acc)
    for i in range(n):
        lo = max(0, i - radius)
        hi = min(n, i + radius + 1)
        out[i] = (prefix[hi] - prefix[lo]) / (hi - lo)
    return out


def interest_curve(
    bundle: SignalBundle,
    *,
    motion_weight: float = 0.5,
    audio_weight: float = 0.5,
    smooth_seconds: float = 2.0,
) -> tuple[list[float], list[float]]:
    """Return ``(times, interest)`` — one smoothed interest value per step.

    ``interest`` is in [0, 1]: a weighted blend of normalized motion and audio,
    smoothed over ``smooth_seconds``. When audio is unavailable (silent track
    or no decoder), it falls back to motion alone so the editor still works.
    """
    times = bundle.times
    if not times:
        return [], []

    motion = bundle.motion or [0.0] * len(times)
    audio = bundle.audio or []
    has_audio = any(a > 0.0 for a in audio)

    raw: list[float] = []
    for i in range(len(times)):
        m = motion[i] if i < len(motion) else 0.0
        if has_audio:
            a = audio[i] if i < len(audio) else 0.0
            raw.append(motion_weight * m + audio_weight * a)
        else:
            raw.append(m)  # motion-only fallback

    # Convert smoothing window (seconds) to samples on the signal grid.
    step = times[1] - times[0] if len(times) > 1 else smooth_seconds
    radius = max(0, int(round((smooth_seconds / step - 1) / 2))) if step > 0 else 0
    return times, _moving_average(raw, radius)


def percentile(xs: list[float], q: float) -> float:
    """Value at quantile ``q`` (0..1) via nearest-rank on a sorted copy."""
    if not xs:
        return 0.0
    q = min(1.0, max(0.0, q))
    ordered = sorted(xs)
    idx = int(round(q * (len(ordered) - 1)))
    return ordered[idx]

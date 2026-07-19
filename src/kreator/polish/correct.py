"""Measure color statistics and compute a gray-world correction.

``gray_world_fix`` is pure (takes measured means); ``measure_color`` is the
light driver that samples frames. Gains are clamped so a correction stays a
correction — it never swings a scene to a new look.
"""

from __future__ import annotations

from ..dsl.program import ColorFix

# How far a single correction may push a channel or exposure.
_MAX_GAIN = 1.6
_MIN_GAIN = 0.7
_MAX_BRIGHT = 0.15


def _clamp(x: float, lo: float, hi: float) -> float:
    return min(max(x, lo), hi)


def gray_world_fix(mean_r: float, mean_g: float, mean_b: float,
                   *, target_luma: float = 0.5) -> ColorFix | None:
    """Gray-world white balance + exposure from per-channel means (0..1).

    White balance: scale each channel so their averages meet at the overall
    gray. Exposure: lift brightness toward ``target_luma``. Returns None when
    the frame is already close to neutral and well-exposed (no-op correction).
    """
    means = [mean_r, mean_g, mean_b]
    if min(means) <= 1e-4:
        return None
    gray = sum(means) / 3.0
    gains = [_clamp(gray / m, _MIN_GAIN, _MAX_GAIN) for m in means]
    # Luma of the corrected image, roughly (Rec.601 on the balanced means).
    corrected = [m * g for m, g in zip(means, gains)]
    luma = 0.299 * corrected[0] + 0.587 * corrected[1] + 0.114 * corrected[2]
    brightness = _clamp(target_luma - luma, -_MAX_BRIGHT, _MAX_BRIGHT)

    cast = max(gains) - min(gains)
    if cast < 0.04 and abs(brightness) < 0.03:
        return None   # already neutral and well-exposed
    return ColorFix(gains[0], gains[1], gains[2], brightness,
                    reason="auto white-balance + exposure (gray-world)")


def measure_color(video_path: str, *, samples: int = 8) -> ColorFix | None:
    """Sample frames, average per channel, and return a ColorFix (or None)."""
    try:
        import cv2  # type: ignore
    except Exception:
        return None
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None
    frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    duration = frames / fps if fps else 0.0
    sums = [0.0, 0.0, 0.0]
    n = 0
    for k in range(samples):
        if duration > 0:
            cap.set(cv2.CAP_PROP_POS_MSEC, duration * (k + 0.5) / samples * 1000.0)
        ok, frame = cap.read()
        if not ok:
            continue
        # OpenCV is BGR; mean() over each plane, normalized to 0..1.
        b, g, r = [float(frame[:, :, c].mean()) / 255.0 for c in range(3)]
        sums[0] += r
        sums[1] += g
        sums[2] += b
        n += 1
    cap.release()
    if n == 0:
        return None
    return gray_world_fix(sums[0] / n, sums[1] / n, sums[2] / n)

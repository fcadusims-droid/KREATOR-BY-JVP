"""Turn per-frame face detections into a smooth per-cut focus. Pure + driver.

``smooth_track`` (pure, testable) is the core: pick the subject face in each
sample, carry the last position through misses, and low-pass the result so the
crop glides. ``face_focus_centers`` is the driver that samples the video.
"""

from __future__ import annotations

from statistics import median


def _subject_cx(faces: list, frame_w: float, prev: float | None) -> float | None:
    """Choose the subject's normalized center-x among detected faces.

    Prefer the face closest to the previous subject position (temporal
    continuity — don't jump to a passer-by), tie-broken by area (the person
    in front, not someone in the background). Returns None if no faces.
    """
    if not faces:
        return None
    if prev is None:
        best = max(faces, key=lambda f: f.area)
    else:
        best = min(faces, key=lambda f: (abs(f.cx / frame_w - prev), -f.area))
    return best.cx / frame_w


def smooth_track(
    samples: list, frame_w: float, *, alpha: float = 0.4,
    max_hold: int = 3,
) -> list[float]:
    """A list of per-sample face lists → one smoothed normalized focus per
    sample. Misses hold the last value (up to ``max_hold`` in a row, then
    ease to center); ``alpha`` is the low-pass factor (lower = smoother)."""
    out: list[float] = []
    cur: float | None = None
    misses = 0
    for faces in samples:
        target = _subject_cx(faces, frame_w, cur)
        if target is None:
            misses += 1
            if cur is None:
                out.append(0.5)
                continue
            if misses > max_hold:
                cur = cur + alpha * (0.5 - cur)   # drift back to center
            out.append(cur)
            continue
        misses = 0
        cur = target if cur is None else cur + alpha * (target - cur)
        out.append(cur)
    return out


def face_focus_centers(
    video_path: str,
    spans: list[tuple[float, float]],
    detector=None,
    *,
    samples_per_span: int = 9,
) -> list[float] | None:
    """One face-based focus (0..1) per span, or None if faces can't be
    detected here (caller then falls back to motion focus).

    More samples than the motion tracker uses, because a face moves within a
    shot and the per-cut focus is the median of the smoothed track — steady,
    but placed where the speaker actually sits.
    """
    if not spans:
        return []
    from .faces import FaceDetector

    det = detector or FaceDetector()
    if not det.available:
        return None
    import cv2  # type: ignore

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video: {video_path}")

    centers: list[float] = []
    any_face = False
    for start, end in spans:
        span_len = max(end - start, 0.0)
        samples = []
        frame_w = 0
        for k in range(samples_per_span):
            t = start + span_len * (k + 1) / (samples_per_span + 1)
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
            ok, frame = cap.read()
            if not ok:
                samples.append([])
                continue
            frame_w = frame.shape[1]
            faces = det.detect(frame)
            if faces:
                any_face = True
            samples.append(faces)
        track = smooth_track(samples, frame_w or 1)
        # Focus is the median of the frames that actually saw a face.
        seen = [c for c, fs in zip(track, samples) if fs]
        centers.append(float(median(seen)) if seen else 0.5)
    cap.release()
    # If not a single face turned up, this isn't face content — let the caller
    # fall back rather than returning a column of 0.5 center crops.
    return centers if any_face else None

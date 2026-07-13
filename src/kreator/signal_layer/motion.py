"""Motion intensity via frame-difference optical flow (OpenCV), lazily imported.

For gameplay, motion magnitude is one of the strongest cheap proxies for
"something is happening" — chases, fights, explosions all spike it. We sample
frames at a fixed hop (not every frame — the single largest cost lever is not
touching every frame) and measure mean absolute frame difference.
"""

from __future__ import annotations


def motion_series(
    video_path: str, hop_seconds: float = 0.5
) -> tuple[list[float], list[float], float, float]:
    """Return ``(times, motion, duration, fps)``.

    ``motion`` is the mean absolute grayscale frame difference at each sampled
    instant, normalized to [0, 1] across the video. Sampling every
    ``hop_seconds`` keeps this linear and cheap regardless of resolution.
    """
    import cv2  # type: ignore

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
    duration = frame_count / fps if fps else 0.0
    hop_frames = max(1, int(round(hop_seconds * fps)))

    times: list[float] = []
    raw: list[float] = []
    prev_gray = None
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % hop_frames == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if prev_gray is not None:
                diff = cv2.absdiff(gray, prev_gray)
                raw.append(float(diff.mean()))
                times.append(idx / fps)
            prev_gray = gray
        idx += 1
    cap.release()

    if duration == 0.0 and times:
        duration = times[-1] + hop_seconds

    motion = _normalize(raw)
    return times, motion, duration, fps


def _normalize(xs: list[float]) -> list[float]:
    if not xs:
        return []
    hi = max(xs)
    if hi <= 0:
        return [0.0 for _ in xs]
    return [x / hi for x in xs]

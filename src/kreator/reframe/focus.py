"""Per-cut horizontal focus from frame-difference motion (OpenCV, lazy import).

For each kept span we sample a handful of instants, diff two nearby frames at
each, collapse the difference to per-column energy, and take the center of
mass. The median across samples is the span's focus — one steady number per
cut, so the vertical crop doesn't wobble frame to frame. Deterministic given
the video and the spans.
"""

from __future__ import annotations

from statistics import median

from .geometry import center_of_mass


def cut_focus_centers(
    video_path: str,
    spans: list[tuple[float, float]],
    *,
    samples_per_span: int = 5,
    frame_gap: int = 3,
) -> list[float]:
    """Return one normalized horizontal focus (0..1) per ``(start, end)`` span.

    ``samples_per_span`` instants are spread evenly inside each span; at each,
    the frame and the one ``frame_gap`` frames later are diffed. Spans where
    nothing readable moves fall back to 0.5 (center crop).
    """
    if not spans:
        return []
    import cv2  # type: ignore

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video: {video_path}")

    centers: list[float] = []
    for start, end in spans:
        span_len = max(end - start, 0.0)
        values: list[float] = []
        for k in range(samples_per_span):
            t = start + span_len * (k + 1) / (samples_per_span + 1)
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
            ok, first = cap.read()
            if not ok:
                continue
            for _ in range(frame_gap - 1):  # skip to the comparison frame
                cap.read()
            ok, second = cap.read()
            if not ok:
                continue
            g1 = cv2.cvtColor(first, cv2.COLOR_BGR2GRAY)
            g2 = cv2.cvtColor(second, cv2.COLOR_BGR2GRAY)
            columns = cv2.absdiff(g1, g2).sum(axis=0).tolist()
            values.append(center_of_mass(columns))
        centers.append(float(median(values)) if values else 0.5)
    cap.release()
    return centers

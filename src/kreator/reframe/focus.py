"""Per-cut horizontal focus from frame-difference motion (OpenCV, lazy import).

For each kept span we sample a handful of instants, diff two nearby frames at
each, collapse the difference to per-column energy, and take the center of
mass. The median across samples is the span's focus — one steady number per
cut, so the vertical crop doesn't wobble frame to frame. Deterministic given
the video and the spans.

Measured on real FPS footage, raw motion energy is a trap: kill feeds,
minimaps, and hit notifications flicker off-center and drag the crop away
from the crosshair (observed offsets up to 0.17 of the frame width). So the
computation runs under a *focus profile*: HUD bands are masked out, energy is
center-weighted, and the final focus is clamped near center — strongly for
``fps`` content, mildly for ``follow`` (open-world), not at all needed for
``center`` (a fixed center crop).
"""

from __future__ import annotations

from statistics import median

from .geometry import center_of_mass, center_weighted, clamp_focus

# How each kind of content maps to a crop policy.
#   row_band: fraction of rows (top, bottom) actually read — masks the HUD
#   col_band: fraction of columns read — masks edge notifications
#   center_weight: strength of the anti-HUD center prior (0..1)
#   max_offset: how far from center the crop may commit
FOCUS_PROFILES: dict[str, dict | None] = {
    # HUD-centered shooters: the subject IS the crosshair. Read only the
    # central band, weight hard toward center, allow small drift.
    "fps": {"row_band": (0.25, 0.80), "col_band": (0.12, 0.88),
            "center_weight": 0.7, "max_offset": 0.12},
    # Open-world / third-person: the action can genuinely live off-center;
    # mask less, weight mildly, allow real excursions.
    "follow": {"row_band": (0.15, 0.90), "col_band": (0.05, 0.95),
               "center_weight": 0.3, "max_offset": 0.35},
    # Fixed center crop — no video reads at all.
    "center": None,
}


def cut_focus_centers(
    video_path: str,
    spans: list[tuple[float, float]],
    *,
    profile: str = "follow",
    samples_per_span: int = 5,
    frame_gap: int = 3,
) -> list[float]:
    """Return one normalized horizontal focus (0..1) per ``(start, end)`` span.

    ``profile`` names a FOCUS_PROFILES policy (``fps``/``follow``/``center``).
    ``samples_per_span`` instants are spread evenly inside each span; at each,
    the frame and the one ``frame_gap`` frames later are diffed. Spans where
    nothing readable moves fall back to 0.5 (center crop).
    """
    if not spans:
        return []
    policy = FOCUS_PROFILES.get(profile, FOCUS_PROFILES["follow"])
    if policy is None:  # "center"
        return [0.5] * len(spans)

    import cv2  # type: ignore

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video: {video_path}")

    r_lo, r_hi = policy["row_band"]
    c_lo, c_hi = policy["col_band"]

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
            h, w = g1.shape
            rows = slice(int(h * r_lo), int(h * r_hi))
            cols = slice(int(w * c_lo), int(w * c_hi))
            diff = cv2.absdiff(g1[rows, cols], g2[rows, cols])
            energies = center_weighted(diff.sum(axis=0).tolist(),
                                       policy["center_weight"])
            band_com = center_of_mass(energies)
            # Map the in-band position back to full-frame coordinates.
            values.append(c_lo + band_com * (c_hi - c_lo))
        raw = float(median(values)) if values else 0.5
        centers.append(clamp_focus(raw, policy["max_offset"]))
    cap.release()
    return centers

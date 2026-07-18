"""Pure reframe geometry — no cv2, no ffmpeg, fully testable.

The one convention to hold on to: a *focus* is the normalized horizontal
position (0..1 of the source width) where the action's center of mass sits.
``crop_window`` turns that into a pixel rectangle; the DSL executor emits the
same math as a resolution-independent FFmpeg expression.
"""

from __future__ import annotations


def parse_aspect(aspect: str) -> float:
    """``"9:16"`` → 0.5625 (width/height). Raises on malformed input."""
    try:
        w_s, h_s = aspect.split(":")
        w, h = int(w_s), int(h_s)
    except ValueError as exc:
        raise ValueError(f"aspect must look like '9:16', got {aspect!r}") from exc
    if w <= 0 or h <= 0:
        raise ValueError(f"aspect sides must be positive, got {aspect!r}")
    return w / h


def _even_floor(x: float) -> int:
    """Largest even integer ≤ x — x264 requires even dimensions."""
    return int(x // 2) * 2


def center_of_mass(energies: list[float]) -> float:
    """Normalized center of mass (0..1) of per-column energies.

    This is what turns "where did pixels change" into a focus point. A flat or
    all-zero profile (nothing moving, or everything moving — a camera pan)
    degrades gracefully to 0.5, i.e. a center crop.
    """
    total = sum(energies)
    if not energies or total <= 0:
        return 0.5
    weighted = sum((i + 0.5) * e for i, e in enumerate(energies))
    return weighted / (total * len(energies))


def center_weighted(energies: list[float], strength: float) -> list[float]:
    """Down-weight energy near the frame edges by a Hann-like window.

    This is the anti-HUD prior: in HUD-heavy games (FPS especially) the
    subject sits at the crosshair while kill feeds, minimaps, and hit
    notifications flicker off-center — raw motion energy follows the flicker
    and drags the crop off the action. ``strength`` blends between no
    weighting (0) and a full cosine window (1).
    """
    import math

    n = len(energies)
    if n == 0 or strength <= 0:
        return list(energies)
    out = []
    for i, e in enumerate(energies):
        x = (i + 0.5) / n
        hann = 0.5 - 0.5 * math.cos(2 * math.pi * x)   # 0 at edges, 1 center
        out.append(e * ((1.0 - strength) + strength * hann))
    return out


def clamp_focus(focus: float, max_offset: float) -> float:
    """Keep the focus within ``max_offset`` of center — the crop never
    commits to the edge unless the caller explicitly allows it."""
    return min(max(focus, 0.5 - max_offset), 0.5 + max_offset)


def crop_window(
    src_w: int, src_h: int, aspect: str, focus_x: float = 0.5
) -> tuple[int, int, int, int]:
    """The crop rect ``(x, y, w, h)`` for reframing ``src`` to ``aspect``.

    Keeps the full height when narrowing (16:9 → 9:16) or the full width when
    shortening, centers the window on ``focus_x`` horizontally (clamped so it
    never leaves the frame), and centers vertically. Output dimensions are
    floored to even for the encoder.
    """
    ratio = parse_aspect(aspect)
    w = _even_floor(min(src_w, src_h * ratio))
    h = _even_floor(min(src_h, src_w / ratio))
    x = min(max(src_w * focus_x - w / 2, 0.0), float(src_w - w))
    y = (src_h - h) / 2
    return int(round(x)), int(round(y)), w, h

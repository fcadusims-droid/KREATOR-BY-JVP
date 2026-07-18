"""Read the whole screen's text with OCR — any game, any HUD layout.

No game-specific regions: the full frame is OCR'd (sparse-text mode) and every
line comes back with its coarse screen position. Two kinds of events emerge:

- **Vocabulary hits** — lines matching the multi-game vocabulary (kills,
  deaths, victories, objectives), wherever they appear.
- **Novel center announcements** — a line that *newly appears* in the middle
  of the screen. Games stamp their big moments center-screen in large type;
  even for a game whose words we've never seen, "new big text at center"
  means *something happened*.

Lazy imports; if tesseract/pytesseract are missing this returns no events and
the pipeline continues on signals alone (same graceful-degrade contract as
speech and the VLM).
"""

from __future__ import annotations

from .events import GameEvent, collapse_events
from .keywords import classify_text

# OCR words below this confidence are noise (HUD fonts read well above it).
_MIN_CONF = 55
# A novel center line this short is likely an OCR fragment, not a banner.
_MIN_ANNOUNCE_LEN = 8


def _region(cx: float, cy: float, w: int, h: int) -> str:
    col = "left" if cx < w / 3 else "center" if cx < 2 * w / 3 else "right"
    row = "top" if cy < h / 3 else "middle" if cy < 2 * h / 3 else "bottom"
    return f"{row}-{col}"


def _lines_with_regions(data: dict, w: int, h: int) -> list[tuple[str, str]]:
    """Group pytesseract image_to_data words into (line_text, region)."""
    lines: dict[tuple, list[tuple[float, str, float, float]]] = {}
    n = len(data.get("text", []))
    for i in range(n):
        word = (data["text"][i] or "").strip()
        try:
            conf = float(data["conf"][i])
        except (TypeError, ValueError):
            continue
        if not word or conf < _MIN_CONF:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        cx = data["left"][i] + data["width"][i] / 2
        cy = data["top"][i] + data["height"][i] / 2
        lines.setdefault(key, []).append((data["left"][i], word, cx, cy))
    out = []
    for words in lines.values():
        words.sort()
        text = " ".join(w for _, w, _, _ in words)
        cx = sum(x for _, _, x, _ in words) / len(words)
        cy = sum(y for _, _, _, y in words) / len(words)
        out.append((text, _region(cx, cy, w, h)))
    return out


def read_screen_events(
    video_path: str,
    spans: list[tuple[float, float]],
    *,
    samples_per_span: int = 5,
    verbose: bool = False,
) -> list[GameEvent]:
    """OCR sampled frames inside each span and return the game's events.

    Sampling (not every frame) is the same cost lever the VLM uses: a banner
    stays on screen for seconds, so a handful of reads per span catches it.
    """
    if not spans:
        return []
    try:
        import cv2  # type: ignore
        import pytesseract  # type: ignore

        pytesseract.get_tesseract_version()
    except Exception:
        return []  # no OCR available → no events, pipeline continues

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video: {video_path}")

    events: list[GameEvent] = []
    for start, end in spans:
        span_len = max(end - start, 0.0)
        seen_lines: set[str] = set()
        for k in range(samples_per_span):
            t = start + span_len * (k + 1) / (samples_per_span + 1)
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
            ok, frame = cap.read()
            if not ok:
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape
            data = pytesseract.image_to_data(
                gray, config="--psm 11", output_type=pytesseract.Output.DICT)
            for text, region in _lines_with_regions(data, w, h):
                norm = " ".join(text.lower().split())
                kinds = classify_text(norm)
                for kind in kinds:
                    events.append(GameEvent(t, kind, "hud", text, region))
                    if verbose:
                        print(f"[gamesense] {t:7.1f}s {kind:<10} {region:<13} {text!r}")
                # A brand-new mid-screen line with no known meaning still
                # signals "the game announced something".
                if (not kinds and norm not in seen_lines
                        and region in ("middle-center", "top-center")
                        and len(norm) >= _MIN_ANNOUNCE_LEN):
                    events.append(GameEvent(t, "announcement", "hud", text, region))
                    if verbose:
                        print(f"[gamesense] {t:7.1f}s announce   {region:<13} {text!r}")
                seen_lines.add(norm)
    cap.release()
    return collapse_events(events)

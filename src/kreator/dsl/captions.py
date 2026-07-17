"""Karaoke captions: remap word timings to the edited timeline and write ASS.

The mechanics are the same as plain subtitles (a caption survives only if its
segment survived the cut), but each *word* is remapped individually so the
highlight lands exactly when the word is spoken in the edited video. The burn
is a standard libass karaoke line: ``{\\kNN}word`` where NN is the word's
display duration in centiseconds — deterministic text, no model involved.
"""

from __future__ import annotations

from .program import Caption, CaptionStyle, Cut
from .timeline import source_to_edited


def captions_from_transcript(
    speech_segments: list, cuts: list[Cut], *, reason: str = "",
) -> list[Caption]:
    """Turn source-time segments *with word timings* into edited-time Captions.

    Segments without word data are skipped (the caller falls back to plain
    subtitles for those). A word is kept if its start survived the cut; ends
    are clamped to the containing cut like plain subtitles are.
    """
    caps: list[Caption] = []
    for seg in speech_segments:
        words = getattr(seg, "words", ()) or ()
        if not words:
            continue
        containing = next(
            (c for c in cuts if c.source_start <= seg.start < c.source_end), None)
        if containing is None:
            continue
        mapped: list[tuple[float, float, str]] = []
        for w in words:
            # A word must live in the same cut as its segment — otherwise it
            # would leap across the removed gap into unrelated footage.
            if not (containing.source_start <= w.start < containing.source_end):
                continue
            ws = source_to_edited(w.start, cuts)
            if ws is None:
                continue
            we_source = min(w.end, containing.source_end)
            we = source_to_edited(we_source - 1e-6, cuts)
            if we is None or we <= ws:
                we = ws + 0.05
            mapped.append((ws, we, w.text))
        if mapped:
            caps.append(Caption(mapped[0][0], mapped[-1][1], tuple(mapped),
                                reason=reason))
    return caps


def _ass_time(t: float) -> str:
    t = max(0.0, t)
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    cs = int(round((t - int(t)) * 100))
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def write_ass(
    captions: list[Caption], path: str, *, style: CaptionStyle | None = None,
) -> None:
    """Write karaoke captions as an ASS file libass can burn.

    Each word gets ``{\\kNN}`` covering from its start to the next word's start
    (gaps fold into the previous word, so the highlight sweeps smoothly).
    """
    st = style or CaptionStyle()
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "PlayResX: 1280\nPlayResY: 720\n"
        "ScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: K,{st.font},{st.size},{st.primary},{st.upcoming},"
        f"{st.outline},&H00000000,{-1 if st.bold else 0},0,0,0,"
        f"100,100,0,0,1,2,0,{st.alignment},30,30,{st.margin_v},1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
        "Text\n"
    )
    lines = [header]
    for cap in sorted(captions, key=lambda c: c.start):
        parts = []
        words = cap.words
        for i, (ws, we, text) in enumerate(words):
            until = words[i + 1][0] if i + 1 < len(words) else we
            dur_cs = max(1, int(round((until - ws) * 100)))
            parts.append(f"{{\\k{dur_cs}}}{text}")
        lines.append(
            f"Dialogue: 0,{_ass_time(cap.start)},{_ass_time(cap.end)},K,,0,0,0,"
            + " ".join(parts) + "\n")
    from pathlib import Path

    Path(path).write_text("".join(lines), encoding="utf-8")

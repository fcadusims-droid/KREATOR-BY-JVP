"""Convert source-timeline positions to edited-timeline positions.

When Kreator cuts segments out and concatenates the rest, every timestamp
shifts. A word spoken at 03:41 in the upload might land at 01:12 in the edit —
or be cut entirely. Subtitles (and any future overlay) must be placed in
*edited* time, so this is where that conversion lives. Pure and testable.
"""

from __future__ import annotations

from .program import Cut, Subtitle


def source_to_edited(source_t: float, cuts: list[Cut]) -> float | None:
    """Map a source-timeline time to its position in the edited video.

    Returns ``None`` if that moment was cut out. Cuts are consumed in order, so
    the edited position is the total kept duration before the containing cut,
    plus the offset within it.
    """
    elapsed = 0.0
    for c in cuts:
        if c.source_start <= source_t < c.source_end:
            return elapsed + (source_t - c.source_start)
        elapsed += c.duration
    return None


def subtitles_from_transcript(
    speech_segments: list, cuts: list[Cut], *, min_len: float = 0.4
) -> list[Subtitle]:
    """Turn source-time transcript segments into edited-time subtitles.

    A segment is kept if its start survived the cut; its end is clamped to the
    end of the cut that contains the start, so a caption never runs past the
    footage it belongs to. ``speech_segments`` are objects with ``.start``,
    ``.end`` and ``.text`` (e.g. ``kreator.speech.SpeechSegment``).
    """
    subs: list[Subtitle] = []
    for seg in speech_segments:
        start = getattr(seg, "start", None)
        end = getattr(seg, "end", None)
        text = (getattr(seg, "text", "") or "").strip()
        if start is None or end is None or not text:
            continue

        containing = next(
            (c for c in cuts if c.source_start <= start < c.source_end), None)
        if containing is None:  # this line was cut out
            continue

        edited_start = source_to_edited(start, cuts)
        clamped_end_source = min(end, containing.source_end)
        edited_end = source_to_edited(clamped_end_source - 1e-6, cuts)
        if edited_start is None or edited_end is None:
            continue
        edited_end = max(edited_end, edited_start + min_len)
        subs.append(Subtitle(edited_start, edited_end, text))
    return subs

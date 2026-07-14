"""Compose an EditProgram from a condense plan + understanding.

This is where the Director's decisions become operations *with justifications*.
Today it lays down the cut spine (each cut carrying why it was kept) and,
optionally, subtitles from the transcript. Zoom / transitions / music are wired
in here as the executor learns to run them.
"""

from __future__ import annotations

from .program import Cut, EditProgram, Transition, Zoom
from .timeline import subtitles_from_transcript

# A segment this interesting gets a subtle punch-in.
_ZOOM_INTEREST = 0.5
_ZOOM_SCALE = 1.12
_XFADE = 0.4  # crossfade duration when transitions are used


def _cut_reason(mean_interest: float) -> str:
    if mean_interest >= 0.45:
        return f"high action (interest {mean_interest:.2f})"
    if mean_interest >= 0.3:
        return f"kept for continuity/interest ({mean_interest:.2f})"
    return f"rescued (dialogue/scene) at low motion ({mean_interest:.2f})"


def compose_program(
    plan,
    *,
    transcript: list | None = None,
    subtitles: bool = False,
    zoom: bool = False,
    transitions: bool = False,
    height: int | None = None,
    rationale: list[str] | None = None,
) -> EditProgram:
    """Build the program. ``plan`` is a ``kreator.editor.EditPlan``;
    ``transcript`` is a list of ``SpeechSegment`` (source time). ``rationale``
    is the Director's high-level decision log.

    Note: ``transitions`` (crossfades) shorten the edited timeline, which would
    drift burned subtitle timing — so the two are not combined here.
    """
    cuts = [
        Cut(s.span.start, s.span.end, reason=_cut_reason(s.mean_interest))
        for s in plan.segments
    ]
    subs = (subtitles_from_transcript(transcript, cuts, reason="spoken dialogue")
            if subtitles and transcript else [])

    zooms: list[Zoom] = []
    if zoom:
        # Punch in on the most intense segments, in edited-timeline coords.
        elapsed = 0.0
        for seg in plan.segments:
            dur = seg.span.duration
            if seg.mean_interest >= _ZOOM_INTEREST:
                zooms.append(Zoom(elapsed, elapsed + dur, _ZOOM_SCALE))
            elapsed += dur

    trans: list[Transition] = []
    if transitions and not subs and len(cuts) > 1:
        elapsed = 0.0
        for c in cuts[:-1]:
            elapsed += c.duration
            trans.append(Transition(elapsed, "crossfade", _XFADE))

    return EditProgram(cuts=cuts, subtitles=subs, zooms=zooms, transitions=trans,
                       height=height, rationale=list(rationale or []))

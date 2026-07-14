"""Compose an EditProgram from a condense plan + understanding.

This is where the Director's decisions become operations. Today it lays down the
cut spine and (optionally) subtitles from the transcript. Zoom / transitions /
music are wired in here as the executor learns to run them.
"""

from __future__ import annotations

from .program import Cut, EditProgram
from .timeline import subtitles_from_transcript


def compose_program(
    plan,
    *,
    transcript: list | None = None,
    subtitles: bool = False,
    height: int | None = None,
) -> EditProgram:
    """Build the program. ``plan`` is a ``kreator.editor.EditPlan``;
    ``transcript`` is a list of ``SpeechSegment`` (source time)."""
    cuts = [Cut(s.span.start, s.span.end) for s in plan.segments]
    subs = (subtitles_from_transcript(transcript, cuts)
            if subtitles and transcript else [])
    return EditProgram(cuts=cuts, subtitles=subs, height=height)

"""K DSL — Kreator's editing operations as data.

An edit is a *program*: a spine of `cut`s (the source spans that survive, in
order) plus operations applied on the edited timeline — subtitles, zoom
punch-ins, crossfade transitions, a K Library music bed, and aspect reframing
(9:16 Shorts); `broll` is declared but its executor is future work. A
deterministic executor turns the program into a video with FFmpeg — the AI
describes, the Director decides the operations, the executor runs them.

This is Level 3 of the proposed training plan (an operations DSL + executor),
built with rules instead of a trained model — see ``docs/training-vs-dsl.md``.
"""

from .program import (Broll, Caption, CaptionStyle, Cut, EditProgram, Grade,
                      KenBurns, Music, PunchZoom, Reframe, Sfx, Shake,
                      Subtitle, Transition, Zoom)
from .timeline import source_to_edited, subtitles_from_transcript
from .captions import captions_from_transcript, write_ass
from .compose import compose_program
from .execute import execute_program

__all__ = [
    "Cut", "Subtitle", "Caption", "CaptionStyle", "Zoom", "PunchZoom",
    "KenBurns", "Shake", "Grade", "Transition",
    "Music", "Sfx", "Broll", "Reframe", "EditProgram",
    "source_to_edited", "subtitles_from_transcript",
    "captions_from_transcript", "write_ass",
    "compose_program", "execute_program",
]

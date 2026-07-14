"""K DSL — Kreator's editing operations as data.

An edit is a *program*: a spine of `cut`s (the source spans that survive, in
order) plus overlay operations applied on the edited timeline (subtitles today;
zoom, transitions, and library assets later). A deterministic executor turns the
program into a video with FFmpeg — the AI describes, the Director decides the
operations, the executor runs them.

This is Level 3 of the proposed training plan (an operations DSL + executor),
built with rules instead of a trained model — see ``docs/training-vs-dsl.md``.
"""

from .program import (Broll, Cut, EditProgram, Music, Subtitle, Transition,
                      Zoom)
from .timeline import source_to_edited, subtitles_from_transcript
from .compose import compose_program
from .execute import execute_program

__all__ = [
    "Cut", "Subtitle", "Zoom", "Transition", "Music", "Broll", "EditProgram",
    "source_to_edited", "subtitles_from_transcript",
    "compose_program", "execute_program",
]

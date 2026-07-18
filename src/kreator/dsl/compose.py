"""Compose an EditProgram from a condense plan + understanding.

This is where the Director's decisions become operations *with justifications*.
It lays down the cut spine (each cut carrying why it was kept) and, optionally,
subtitles from the transcript, zoom punch-ins, crossfade transitions, and a
background music bed from the K Library — each executed by the DSL runner.
"""

from __future__ import annotations

from .captions import captions_from_transcript
from .program import (CaptionStyle, Cut, EditProgram, Grade, Music, Reframe,
                      Transition, Zoom)
from .timeline import subtitles_from_transcript

# A segment this interesting gets a subtle punch-in.
_ZOOM_INTEREST = 0.5
_ZOOM_SCALE = 1.12
_XFADE = 0.4  # crossfade duration when transitions are used
_MUSIC_VOLUME = 0.22  # background bed, kept well under the creator's own audio


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
    captions: bool = False,
    caption_style: CaptionStyle | None = None,
    zoom: bool = False,
    transitions: bool = False,
    music_track: str | None = None,
    music_volume: float = _MUSIC_VOLUME,
    height: int | None = None,
    aspect: str | None = None,
    reframe_strategy: str = "crop",
    focus_x: list[float] | None = None,
    grade: str | None = None,
    rationale: list[str] | None = None,
) -> EditProgram:
    """Build the program. ``plan`` is a ``kreator.editor.EditPlan``;
    ``transcript`` is a list of ``SpeechSegment`` (source time). ``rationale``
    is the Director's high-level decision log. ``music_track`` is a path to a
    real K Library asset to lay under the whole edit (or ``None`` for no music).

    ``aspect`` (e.g. ``"9:16"``) attaches a Reframe: ``reframe_strategy`` is
    ``"crop"`` or ``"pad"``, and ``focus_x`` gives one horizontal focus per
    plan segment (from ``kreator.reframe.cut_focus_centers``; omitted → center).

    Note: ``transitions`` (crossfades) shorten the edited timeline, which would
    drift burned subtitle timing — so the two are not combined here.
    """
    cuts = [
        Cut(s.span.start, s.span.end, reason=_cut_reason(s.mean_interest))
        for s in plan.segments
    ]
    # Karaoke captions need word timings; segments without them fall back to
    # plain subtitles (the executor burns one subtitle track, so it's either).
    caps = (captions_from_transcript(transcript, cuts, reason="spoken dialogue")
            if captions and transcript else [])
    subs = (subtitles_from_transcript(transcript, cuts, reason="spoken dialogue")
            if (subtitles or captions) and transcript and not caps else [])

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
    if transitions and not subs and not caps and len(cuts) > 1:
        elapsed = 0.0
        for c in cuts[:-1]:
            elapsed += c.duration
            trans.append(Transition(elapsed, "crossfade", _XFADE))

    music: list[Music] = []
    if music_track and cuts:
        # One background bed spanning the whole edited timeline. The executor
        # loops it and trims to the video length, so an exact end isn't needed.
        edited_duration = sum(c.duration for c in cuts)
        music.append(Music(music_track, 0.0, edited_duration, music_volume))

    reframe = None
    if aspect:
        fx = tuple(focus_x) if focus_x else ()
        how = ("following the action" if reframe_strategy == "crop" and fx
               else "fit with bars" if reframe_strategy == "pad" else "centered")
        reframe = Reframe(aspect=aspect, strategy=reframe_strategy, focus_x=fx,
                          reason=f"reframed to {aspect} ({how})")

    return EditProgram(cuts=cuts, subtitles=subs, captions=caps,
                       caption_style=caption_style if caps else None,
                       zooms=zooms, transitions=trans,
                       music=music, reframe=reframe,
                       grade=Grade(grade) if grade else None,
                       height=height,
                       rationale=list(rationale or []))

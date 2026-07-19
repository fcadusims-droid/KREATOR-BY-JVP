"""Plan Ken Burns pushes and B-roll cutaways over an edit. Pure + light driver.

Both work in *edited-time* coordinates (the cut spine already laid down), so
they compose with reframing and captions downstream.
"""

from __future__ import annotations

from ..dsl.program import Broll, KenBurns


def plan_ken_burns(
    cuts: list, *, min_seconds: float = 3.0, zoom: float = 0.12,
    max_moves: int = 6,
) -> list[KenBurns]:
    """A slow push on the longest held shots — where a static frame would
    otherwise sit dead. Alternates zoom-in / zoom-out and pan direction so a
    sequence of shots doesn't feel mechanical. Edited-time windows.
    """
    # Edited-time span of each cut.
    spans = []
    elapsed = 0.0
    for c in cuts:
        dur = c.edited_duration if hasattr(c, "edited_duration") else \
            (c.source_end - c.source_start)
        spans.append((elapsed, elapsed + dur, dur))
        elapsed += dur

    # Longest shots first, but keep at most max_moves, then restore order.
    candidates = sorted((s for s in spans if s[2] >= min_seconds),
                        key=lambda s: -s[2])[:max_moves]
    candidates.sort()
    moves: list[KenBurns] = []
    for i, (start, end, _dur) in enumerate(candidates):
        z_in = (i % 2 == 0)
        pan = (0.10 if i % 4 == 1 else -0.10 if i % 4 == 3 else 0.0)
        moves.append(KenBurns(
            start, end,
            z_from=1.0 if z_in else 1.0 + zoom,
            z_to=1.0 + zoom if z_in else 1.0,
            pan=pan,
            reason="slow push to keep a held shot alive"))
    return moves


def plan_broll(
    cuts: list, transcript: list, library_root, *,
    clip_seconds: float = 3.0, gap_seconds: float = 8.0, max_inserts: int = 4,
):
    """Lay K Library B-roll cutaways over stretches of narration.

    Returns ``(broll_ops, notes)``. A cutaway is placed where the narrator is
    talking (a subtitle is on screen) but only every ``gap_seconds`` so the
    piece keeps returning to the speaker. Needs a K Library with a ``broll/``
    folder; returns nothing otherwise. Edited-time.
    """
    if not (library_root and transcript and cuts):
        return [], []
    from ..dsl.timeline import subtitles_from_transcript
    from ..library import KLibrary

    lib = KLibrary(library_root)
    clips = lib._assets_of_kind("broll") if hasattr(lib, "_assets_of_kind") else []
    if not clips:
        return [], []

    subs = subtitles_from_transcript(transcript, cuts)
    broll: list[Broll] = []
    last_at = -1e9
    ci = 0
    for s in sorted(subs, key=lambda x: x.start):
        if s.start - last_at < gap_seconds:
            continue
        # Only over lines long enough to cover a cutaway.
        if s.end - s.start < clip_seconds * 0.6:
            continue
        clip = clips[ci % len(clips)]
        broll.append(Broll(str(clip.path), s.start, clip_seconds,
                           reason="B-roll cutaway over narration"))
        last_at = s.start
        ci += 1
        if len(broll) >= max_inserts:
            break
    notes = ([f"{len(broll)} B-roll cutaway(s) over narration"]
             if broll else [])
    return broll, notes

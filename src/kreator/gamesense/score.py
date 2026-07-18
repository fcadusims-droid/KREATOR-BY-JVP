"""Turn what the screen said into a ranking adjustment. Pure, deterministic.

This is the Planner side of GameSense: OCR and the announcer *described*;
here fixed weights *decide*. A multikill medal outweighs everything, a death
on screen sinks the clip (a viewer wants the play, not the killcam), plain
kills stack up to a cap, and unknown-but-loud center-screen announcements add
a little (the game flagged the moment even if we can't name it).
"""

from __future__ import annotations

from .events import GameEvent
from .keywords import classify_text

_WEIGHTS = {
    "multikill": 0.50,
    "victory": 0.30,
    "objective": 0.20,
    "kill": 0.15,          # per kill, capped below
    "announcement": 0.06,  # per novel banner, capped below
    "death": -0.45,
    "ui": -0.30,           # menus/scoreboards: text-dense but not gameplay
}
# The announcer narrating objective state ("...captured the hardpoint") runs
# all match in objective modes — ambient commentary, not a player feat. HUD
# objective banners keep full weight; the announcer's count a token amount.
_AMBIENT_ANNOUNCER = {"objective": 0.05, "victory": 0.10}
_KILL_CAP = 3          # kills counted at most this many times
_ANNOUNCE_CAP = 2
_DELTA_BOUNDS = (-0.6, 0.8)

_PHRASE = {
    "multikill": "a multikill medal on screen",
    "kill": "kill(s) confirmed on screen",
    "death": "the player dying on screen",
    "victory": "a victory/level-up banner",
    "objective": "an objective moment",
    "announcement": "the game announcing something",
    "ui": "menu/scoreboard on screen (not gameplay)",
}


def announcer_events(transcript_segments: list, span) -> list[GameEvent]:
    """Vocabulary hits in what the announcer/players *said* inside ``span`` —
    the transcript is already computed, so this costs nothing.

    A line belongs to the window where it *started*: Whisper can emit long
    segments, and attributing by overlap smeared one announcer sentence
    across several candidate windows on real footage.
    """
    out = []
    for seg in transcript_segments or []:
        if not (span.start <= seg.start <= span.end):
            continue
        for kind in classify_text(seg.text):
            out.append(GameEvent(seg.start, kind, "announcer", seg.text.strip()))
    return out


def viral_adjustment(events: list[GameEvent]) -> tuple[float, list[str]]:
    """(bounded score delta, human-readable reasons) for one clip window."""
    if not events:
        return 0.0, []
    # (kind, ambient?) → count. Ambient = the announcer narrating match
    # state, weighted down; personal callouts keep their kind's full weight.
    counts: dict[tuple[str, bool], int] = {}
    for ev in events:
        ambient = ev.source == "announcer" and ev.kind in _AMBIENT_ANNOUNCER
        counts[(ev.kind, ambient)] = counts.get((ev.kind, ambient), 0) + 1

    delta = 0.0
    reasons: list[str] = []
    for (kind, ambient), n in sorted(counts.items()):
        counted = min(n, _KILL_CAP) if kind == "kill" else \
            min(n, _ANNOUNCE_CAP) if kind == "announcement" else 1
        weight = _AMBIENT_ANNOUNCER[kind] if ambient else _WEIGHTS.get(kind, 0.0)
        contribution = weight * counted
        if contribution == 0.0:
            continue
        delta += contribution
        sign = "boost" if contribution > 0 else "demote"
        phrase = (f"the announcer mentioning {kind} play" if ambient
                  else _PHRASE.get(kind, kind))
        reasons.append(f"{sign}: {phrase}"
                       + (f" ×{counted}" if counted > 1 else ""))

    lo, hi = _DELTA_BOUNDS
    return min(max(delta, lo), hi), reasons

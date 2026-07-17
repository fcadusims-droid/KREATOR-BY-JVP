"""Pause removal for talking content — vlogs, podcasts, classes.

Gameplay is edited by *action*; talking content is edited by *speech*: keep
what was said, cut the dead air between sentences. The plan comes straight
from the transcript's segment boundaries, so a cut can never land mid-sentence
— the failure mode that makes automatic pause removal unusable. Deterministic
given the transcript.
"""

from __future__ import annotations

from ..types import Timespan
from .condenser import EditPlan, KeepSegment


def pause_cut_plan(
    speech_segments: list,
    duration: float,
    *,
    pad: float = 0.25,
    min_pause: float = 0.8,
    min_keep: float = 0.6,
) -> EditPlan:
    """Keep every spoken stretch (padded), cut every pause over ``min_pause``.

    Consecutive spoken spans whose gap is at most ``min_pause`` are merged —
    a natural breath does not become a cut. Keeps shorter than ``min_keep``
    are dropped as unwatchable fragments.
    """
    spans: list[list[float]] = []
    for seg in sorted(speech_segments, key=lambda s: s.start):
        start = max(0.0, seg.start - pad)
        end = min(duration, seg.end + pad)
        if end <= start:
            continue
        if spans and start - spans[-1][1] <= min_pause:
            spans[-1][1] = max(spans[-1][1], end)
        else:
            spans.append([start, end])

    segments = [
        KeepSegment(Timespan(s, e), mean_interest=1.0)
        for s, e in spans
        if e - s >= min_keep
    ]
    return EditPlan(segments, duration, 0.0)

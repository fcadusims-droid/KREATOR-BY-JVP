"""Group scored segments into ranked clip-length moments.

Seeds are the highest-scoring segments; each grows outward on sentence
(segment) boundaries until it reaches the minimum Short length, capped at the
maximum, then overlapping seeds are suppressed. The output quacks like the
Clipper's Candidate (``span``, ``score``, ``rank``, ``rationale``,
``breakdown.features``) so the Shorts pipeline consumes it unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..types import Timespan, format_tc
from .score import score_segment


@dataclass
class _Breakdown:
    features: dict = field(default_factory=dict)


@dataclass
class StoryMoment:
    span: Timespan
    score: float
    rank: int
    rationale: str
    breakdown: _Breakdown = field(default_factory=_Breakdown)
    evidence = None   # parity with Candidate; unused by the Shorts builder

    def to_dict(self) -> dict:
        return {"rank": self.rank, "start": round(self.span.start, 2),
                "end": round(self.span.end, 2), "score": round(self.score, 3),
                "rationale": self.rationale}


def _audio_emphasis(bundle, start: float, end: float) -> float:
    if not (bundle and bundle.times and bundle.audio):
        return 0.0
    vals = [a for t, a in zip(bundle.times, bundle.audio) if start <= t < end]
    return max(vals) if vals else 0.0


def story_moments(
    transcript: list,
    *,
    bundle=None,
    top_n: int = 5,
    min_len: float = 15.0,
    max_len: float = 60.0,
    suppress_overlap: float = 0.3,
) -> list[StoryMoment]:
    """Rank the transcript's clippable moments as StoryMoments.

    ``transcript`` is a list of SpeechSegments (``.start/.end/.text``);
    ``bundle`` (optional) supplies audio emphasis. Deterministic.
    """
    segs = sorted((s for s in transcript if (s.text or "").strip()),
                  key=lambda s: s.start)
    if not segs:
        return []

    scored = []
    for s in segs:
        emph = _audio_emphasis(bundle, s.start, s.end)
        sc, reasons = score_segment(s.text, audio_emphasis=emph)
        scored.append((sc, reasons, s))

    # Seeds: strongest segments first (then earliest for stability).
    order = sorted(range(len(segs)),
                   key=lambda i: (-scored[i][0], segs[i].start))

    moments: list[StoryMoment] = []
    used: list[Timespan] = []
    for idx in order:
        seed = segs[idx]
        if scored[idx][0] <= 0 and moments:
            break   # nothing quotable left
        # Grow symmetrically over neighbouring segments to reach min_len.
        lo = hi = idx
        start, end = seed.start, seed.end
        while end - start < min_len and (lo > 0 or hi < len(segs) - 1):
            grow_lo = lo > 0 and (idx - lo) <= (hi - idx)
            if grow_lo and (start - segs[lo - 1].start) <= max_len:
                lo -= 1
                start = segs[lo].start
            elif hi < len(segs) - 1 and (segs[hi + 1].end - start) <= max_len:
                hi += 1
                end = segs[hi].end
            else:
                break
        span = Timespan(start, min(end, start + max_len))
        if any(span.intersection(u) / max(span.duration, 1e-6) > suppress_overlap
               for u in used):
            continue
        used.append(span)

        # Aggregate reasons across the window; rank by the seed's strength.
        window_reasons: list[str] = []
        for j in range(lo, hi + 1):
            for r in scored[j][1]:
                if r not in window_reasons:
                    window_reasons.append(r)
        text = " ".join(segs[j].text.strip() for j in range(lo, hi + 1))
        rationale = (f"Quotable moment at {format_tc(seed.start)}: "
                     + (", ".join(window_reasons) if window_reasons
                        else "a self-contained line")
                     + f'. "{text[:70].strip()}…"')
        feats = {
            "story_score": round(min(scored[idx][0], 1.0), 3),
            "is_question": 1.0 if "question" in " ".join(scored[idx][1]) else 0.0,
            "audio_emphasis": round(_audio_emphasis(bundle, seed.start, seed.end), 3),
        }
        moments.append(StoryMoment(span, scored[idx][0], len(moments) + 1,
                                   rationale, _Breakdown(feats)))
        if len(moments) >= top_n:
            break
    return moments

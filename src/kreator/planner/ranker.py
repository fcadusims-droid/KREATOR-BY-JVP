"""K Clipper — generates, scores, orders, and explains clip candidates.

Design humility, per spec: K Clipper *ranks, it does not decide.* It returns
the top-N candidates each with the rationale for why it was chosen, and leaves
the final pick to the human until per-channel memory calibrates taste. The
ranking is fully deterministic given (evidence, profile), which is what E1
measures against a human editor's choices.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..evidence.types import Evidence
from ..types import Timespan, format_tc
from .scoring import ScoreBreakdown, ScoringProfile, score_evidence


# Human-readable labels for the rationale sentence.
_SIGNAL_PHRASES = {
    "visual_energy": "high visual energy",
    "audio_intensity": "a sharp audio peak",
    "hook_strength": "a fast-rising hook",
    "scene_activity": "dense scene activity",
    "speech_density": "spoken/quotable content",
    "event_confidence": "a model-confirmed event",
    "trigger_strength": "a strong raw signal",
}


@dataclass
class Candidate:
    """A ranked clip suggestion: where it is, how it scored, and why."""

    span: Timespan
    score: float
    rank: int
    breakdown: ScoreBreakdown
    evidence: Evidence
    rationale: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "rank": self.rank,
            "start": round(self.span.start, 2),
            "end": round(self.span.end, 2),
            "start_tc": format_tc(self.span.start),
            "end_tc": format_tc(self.span.end),
            "duration": round(self.span.duration, 2),
            "score": self.score,
            "rationale": self.rationale,
            "signals": {k: round(v, 3) for k, v in self.breakdown.features.items()},
            "evidence_id": self.evidence.evidence_id,
            "source": self.evidence.source,
            "labels": self.evidence.labels,
        }


class KClipper:
    def __init__(self, profile: ScoringProfile | None = None) -> None:
        self.profile = profile or ScoringProfile()

    def rank(self, evidences: list[Evidence], top_n: int = 5) -> list[Candidate]:
        scored: list[tuple[ScoreBreakdown, Evidence]] = [
            (score_evidence(ev, self.profile), ev) for ev in evidences
        ]

        # Deterministic ordering: score desc, then earliest moment, then a
        # stable content hash — so ties never resolve on dict/float accident.
        scored.sort(
            key=lambda pair: (
                -pair[0].total,
                pair[1].span.start,
                pair[1].evidence_id,
            )
        )

        candidates: list[Candidate] = []
        for i, (breakdown, ev) in enumerate(scored[:top_n], start=1):
            candidates.append(
                Candidate(
                    span=ev.span,
                    score=breakdown.total,
                    rank=i,
                    breakdown=breakdown,
                    evidence=ev,
                    rationale=self._explain(breakdown, ev),
                )
            )
        return candidates

    def _explain(self, breakdown: ScoreBreakdown, ev: Evidence) -> str:
        """Build a per-signal rationale from the top contributing signals."""
        ranked = sorted(
            breakdown.contributions.items(), key=lambda kv: kv[1], reverse=True
        )
        top = [
            (sig, breakdown.features.get(sig, 0.0))
            for sig, contrib in ranked
            if contrib > 0 and breakdown.features.get(sig, 0.0) > 0
        ][:3]

        if not top:
            return f"Weak candidate at {format_tc(ev.span.center)}; no strong signal."

        phrases = [
            f"{_SIGNAL_PHRASES.get(sig, sig)} ({val:.2f})" for sig, val in top
        ]
        joined = phrases[0] if len(phrases) == 1 else (
            ", ".join(phrases[:-1]) + f" and {phrases[-1]}"
        )
        event = ev.labels.get("event")
        tail = f" Labelled '{event}'." if event else ""
        return (
            f"Moment at {format_tc(ev.span.center)} shows {joined}."
            f"{tail}"
        )

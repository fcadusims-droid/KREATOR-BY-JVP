"""Planner / K Clipper — deterministic ranking of clip candidates.

The strict separation the runtime spec insists on: **the AI classifies; the
Planner decides.** Models (when present) only attach probabilistic labels to
evidence. This module turns an evidence set into an ordered ranking of
candidates with per-signal rationale — and it does so deterministically, so the
same evidence and the same weights always yield the same ranking. That is what
makes E1 testable: feed fixed evidence, assert the ranking.
"""

from .scoring import ScoringProfile, score_evidence
from .ranker import Candidate, KClipper

__all__ = ["Candidate", "KClipper", "ScoringProfile", "score_evidence"]

"""E4-RT: given a fixed evidence set, the Planner's ranking is correct and
deterministic — provable with no video and no models."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.evidence.types import Evidence
from kreator.planner import KClipper, ScoringProfile, score_evidence
from kreator.types import Timespan


def _ev(start, signals, labels=None):
    return Evidence(
        span=Timespan(start, start + 10.0),
        signals=signals,
        labels=labels or {},
    )


def test_higher_energy_ranks_first():
    strong = _ev(60.0, {"visual_energy": 0.95, "audio_intensity": 0.9, "hook_strength": 0.8})
    weak = _ev(20.0, {"visual_energy": 0.2, "audio_intensity": 0.1, "hook_strength": 0.1})
    ranking = KClipper().rank([weak, strong], top_n=2)
    assert ranking[0].span.start == 60.0
    assert ranking[1].span.start == 20.0
    assert ranking[0].score >= ranking[1].score


def test_ranking_is_deterministic():
    evs = [
        _ev(10.0, {"visual_energy": 0.5, "audio_intensity": 0.5}),
        _ev(30.0, {"visual_energy": 0.7, "audio_intensity": 0.6}),
        _ev(50.0, {"visual_energy": 0.7, "audio_intensity": 0.6}),  # tie w/ prev
    ]
    a = [c.to_dict() for c in KClipper().rank(evs, top_n=3)]
    b = [c.to_dict() for c in KClipper().rank(list(reversed(evs)), top_n=3)]
    # Same inputs (any order) → identical ranking, including tie resolution.
    assert [c["evidence_id"] for c in a] == [c["evidence_id"] for c in b]


def test_ties_break_by_earliest_moment():
    early = _ev(10.0, {"visual_energy": 0.6, "audio_intensity": 0.6})
    late = _ev(90.0, {"visual_energy": 0.6, "audio_intensity": 0.6})
    ranking = KClipper().rank([late, early], top_n=2)
    assert ranking[0].span.start == 10.0  # tie → earlier moment wins


def test_vlm_event_confidence_lifts_score():
    base = _ev(40.0, {"visual_energy": 0.5})
    labelled = _ev(40.0, {"visual_energy": 0.5}, labels={"event": "explosion", "conf": 0.9})
    profile = ScoringProfile()
    assert score_evidence(labelled, profile).total > score_evidence(base, profile).total


def test_rationale_names_the_top_signals():
    ev = _ev(60.0, {"visual_energy": 0.95, "audio_intensity": 0.9, "hook_strength": 0.85})
    [cand] = KClipper().rank([ev], top_n=1)
    assert "visual energy" in cand.rationale
    assert cand.rationale.startswith("Moment at")


def test_scores_are_bucketed_for_stability():
    # Two nearly-identical evidences must land on the same bucketed score, so
    # float noise cannot reorder the ranking.
    a = _ev(10.0, {"visual_energy": 0.8000, "audio_intensity": 0.7000})
    b = _ev(10.0, {"visual_energy": 0.8004, "audio_intensity": 0.7003})
    assert score_evidence(a, ScoringProfile()).total == score_evidence(b, ScoringProfile()).total


if __name__ == "__main__":
    import traceback

    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except Exception:
                failures += 1
                print(f"FAIL {name}")
                traceback.print_exc()
    raise SystemExit(1 if failures else 0)

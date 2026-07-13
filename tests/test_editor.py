"""Deterministic tests for the K Editor condenser — no video, no ffmpeg."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.editor import Condenser, interest_curve
from kreator.editor.interest import percentile
from kreator.signal_layer import synthetic_bundle


def _bundle_with_action_islands():
    """A 120s 'session' with two clear action islands (~30s and ~90s) in an
    otherwise calm timeline."""
    return synthetic_bundle(
        duration=120.0,
        peaks=[
            {"time": 30.0, "motion": 0.9, "audio": 0.8, "width": 5.0},
            {"time": 90.0, "motion": 0.95, "audio": 0.9, "width": 5.0},
        ],
    )


def test_interest_curve_peaks_at_action():
    bundle = _bundle_with_action_islands()
    times, interest = interest_curve(bundle)
    assert len(times) == len(interest)
    # Interest near an action island beats interest in the calm middle.
    def at(t):
        return interest[min(range(len(times)), key=lambda i: abs(times[i] - t))]
    assert at(30.0) > at(60.0)
    assert at(90.0) > at(60.0)


def test_condenser_keeps_action_cuts_boredom():
    plan = Condenser(target_keep=0.35).plan(_bundle_with_action_islands())
    assert plan.segments, "expected kept segments around the action"
    assert plan.kept_duration < plan.original_duration  # something was cut
    # Every kept segment should sit near one of the two action islands.
    for seg in plan.segments:
        c = seg.span.center
        assert min(abs(c - 30.0), abs(c - 90.0)) < 20.0


def test_condenser_respects_min_keep():
    plan = Condenser(target_keep=0.35, min_keep_seconds=2.0).plan(
        _bundle_with_action_islands()
    )
    for seg in plan.segments:
        assert seg.span.duration >= 2.0


def test_condenser_merges_short_cuts():
    # With a large min-cut, the two nearby islands should not be split by a
    # short boring gap — they merge into one kept region.
    close = synthetic_bundle(
        duration=60.0,
        peaks=[
            {"time": 25.0, "motion": 0.9, "audio": 0.8, "width": 4.0},
            {"time": 33.0, "motion": 0.9, "audio": 0.8, "width": 4.0},
        ],
    )
    plan = Condenser(target_keep=0.5, min_cut_seconds=10.0).plan(close)
    # The 8s gap between islands is below min_cut → single merged segment.
    spanning = [s for s in plan.segments if s.span.start <= 25 and s.span.end >= 33]
    assert spanning, "expected the short gap to be bridged into one segment"


def test_percentile_bounds():
    xs = [0.1, 0.2, 0.3, 0.4, 0.5]
    assert percentile(xs, 0.0) == 0.1
    assert percentile(xs, 1.0) == 0.5


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

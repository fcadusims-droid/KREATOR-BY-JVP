"""Deterministic tests for signal-driven keyframe selection (no video/VLM)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.signal_layer import synthetic_bundle
from kreator.vlm import select_keyframes


def _bundle():
    return synthetic_bundle(
        duration=120.0,
        peaks=[
            {"time": 20.0, "motion": 0.95, "audio": 0.9, "width": 4.0},
            {"time": 80.0, "motion": 0.9, "audio": 0.85, "width": 4.0},
        ],
        scene_cuts=[19.0, 79.0],
    )


def test_keyframes_respect_min_gap_and_cap():
    kfs = select_keyframes(_bundle(), max_frames=10, min_gap=6.0)
    assert len(kfs) <= 10
    for a, b in zip(kfs, kfs[1:]):
        assert b.time - a.time >= 6.0          # spacing enforced
    assert kfs == sorted(kfs, key=lambda k: k.time)  # time-ordered


def test_keyframes_flag_action_moments():
    kfs = select_keyframes(_bundle(), max_frames=30, min_gap=4.0)
    peak_times = [k.time for k in kfs if k.reason == "interest_peak"]
    # An interest peak should be selected near each planted action island.
    assert any(abs(t - 20.0) < 6 for t in peak_times)
    assert any(abs(t - 80.0) < 6 for t in peak_times)


def test_keyframes_empty_bundle():
    from kreator.types import SignalBundle
    assert select_keyframes(SignalBundle(duration=0.0, fps=1.0)) == []


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

"""Unit tests for the Evidence Layer's normalization primitives —
``bucket`` (per-run stability) and ``hysteretic`` (cross-run stability)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.evidence.types import bucket, hysteretic


def test_bucket_collapses_float_noise():
    # Two scores a hair apart must land on the same grid step.
    assert bucket(0.8149) == bucket(0.8151)


def test_bucket_clamps_out_of_range():
    assert bucket(-0.5) == 0.0
    assert bucket(1.5) == 1.0


def test_bucket_rejects_bad_levels():
    try:
        bucket(0.5, levels=0)
    except ValueError:
        return
    raise AssertionError("expected ValueError for levels < 1")


def test_hysteretic_passes_through_without_previous():
    assert hysteretic(0.7, None, rise=0.1, fall=0.1) == 0.7


def test_hysteretic_holds_small_change():
    # A change inside the band is ignored — the previous value is held.
    assert hysteretic(0.74, 0.70, rise=0.1, fall=0.1) == 0.70


def test_hysteretic_accepts_change_clearing_band():
    assert hysteretic(0.82, 0.70, rise=0.1, fall=0.1) == 0.82   # rose enough
    assert hysteretic(0.55, 0.70, rise=0.1, fall=0.1) == 0.55   # fell enough


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

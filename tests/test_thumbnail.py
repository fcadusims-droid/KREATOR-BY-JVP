"""Tests for K Thumbnail — moment picking and the deterministic treatment.
Uses synthetic bundles and ndarrays; no video file, no models."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.signal_layer import synthetic_bundle
from kreator.thumbnail import ThumbStyle, pick_thumbnail_times
from kreator.thumbnail.compose import enhance_frame


def _bundle():
    return synthetic_bundle(
        duration=120.0,
        peaks=[{"time": 30.0, "motion": 0.9, "audio": 0.8, "width": 4.0},
               {"time": 90.0, "motion": 0.95, "audio": 0.9, "width": 4.0}])


def test_picks_the_strongest_distinct_moments():
    times = pick_thumbnail_times(_bundle(), n=2)
    assert len(times) == 2
    # One pick near each action island — not two frames of the same burst.
    assert any(abs(t - 30.0) < 8.0 for t in times)
    assert any(abs(t - 90.0) < 8.0 for t in times)


def test_picks_respect_minimum_separation():
    times = pick_thumbnail_times(_bundle(), n=3, min_separation_ratio=0.08)
    gaps = [abs(a - b) for i, a in enumerate(times) for b in times[i + 1:]]
    assert all(g >= 120.0 * 0.08 for g in gaps)


def test_empty_bundle_picks_nothing():
    from kreator.types import SignalBundle
    assert pick_thumbnail_times(SignalBundle(duration=0.0, fps=30.0), 3) == []


def test_enhance_lifts_contrast_and_saturation_deterministically():
    import numpy as np

    rng = np.random.default_rng(7)
    frame = rng.integers(40, 180, size=(72, 128, 3), dtype=np.uint8)
    out1 = enhance_frame(frame.copy(), ThumbStyle())
    out2 = enhance_frame(frame.copy(), ThumbStyle())
    assert (out1 == out2).all()                    # deterministic
    assert out1.shape == frame.shape
    assert float(out1.mean()) > float(frame.mean())  # brighter/contrastier

    import cv2
    s_in = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)[:, :, 1].mean()
    s_out = cv2.cvtColor(out1, cv2.COLOR_BGR2HSV)[:, :, 1].mean()
    assert s_out > s_in                            # saturation pushed


def test_enhance_neutral_style_is_identity():
    import numpy as np

    frame = np.full((36, 64, 3), 120, np.uint8)
    style = ThumbStyle(contrast=1.0, brightness=0, saturation=1.0, sharpen=0.0)
    assert (enhance_frame(frame, style) == frame).all()


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

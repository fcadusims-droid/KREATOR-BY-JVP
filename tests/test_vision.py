"""Tests for K Vision — face-track smoothing and focus. No model, no video
(the pure track logic drives on synthetic Face lists)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.vision import smooth_track
from kreator.vision.faces import Face


def _f(cx_norm, w=1000, area=8000):
    # A face whose center-x is cx_norm of a `w`-wide frame.
    fw = (area) ** 0.5
    return Face(cx_norm * w - fw / 2, 100, fw, area / fw, 0.9)


def test_track_follows_a_moving_speaker():
    W = 1000
    samples = [[_f(0.3)], [_f(0.5)], [_f(0.7)], [_f(0.7)]]
    track = smooth_track(samples, W, alpha=1.0)   # alpha=1 → follow exactly
    assert abs(track[0] - 0.3) < 1e-6
    assert abs(track[-1] - 0.7) < 1e-6
    assert track == sorted(track)                 # monotonic rightward move


def test_track_low_pass_smooths_jitter():
    W = 1000
    samples = [[_f(0.5)], [_f(0.9)], [_f(0.5)], [_f(0.9)]]   # jitter
    track = smooth_track(samples, W, alpha=0.4)
    # Smoothed track lags the raw jitter: first sample locks on, the rest
    # never reach the raw 0.9 extreme.
    assert max(track[1:]) < 0.9 and min(track[1:]) > 0.5


def test_miss_holds_last_then_drifts_to_center():
    W = 1000
    samples = [[_f(0.8)]] + [[]] * 6        # face, then a long dropout
    track = smooth_track(samples, W, alpha=0.5, max_hold=3)
    assert abs(track[0] - 0.8) < 1e-6
    assert track[1] == track[2] == track[3] == track[0]   # held during hold window
    assert track[-1] < track[0]                            # then eases to center


def test_subject_is_the_persistent_face_not_a_passerby():
    W = 1000
    # A steady subject at 0.4; a bigger transient face flashes at 0.85.
    samples = [[_f(0.4)], [_f(0.4), _f(0.85, area=20000)], [_f(0.4)]]
    track = smooth_track(samples, W, alpha=1.0)
    assert all(abs(c - 0.4) < 1e-6 for c in track)   # never jumps to the passer-by


def test_no_faces_ever_is_center():
    assert smooth_track([[], [], []], 1000) == [0.5, 0.5, 0.5]


def test_face_profile_registered():
    from kreator.reframe.focus import FOCUS_PROFILES
    assert FOCUS_PROFILES.get("face") == "face"


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

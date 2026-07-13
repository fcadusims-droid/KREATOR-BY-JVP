"""Signal Layer + Analyst tests that need no video: peak picking, the
synthetic bundle, and the signals→evidence reduction."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.evidence import KAnalyst
from kreator.signal_layer import detect_peaks, synthetic_bundle


def test_detect_peaks_finds_prominent_maxima():
    times = [i * 0.5 for i in range(20)]
    series = [0.1] * 20
    series[6] = 0.9   # a clear peak at t=3.0
    series[14] = 0.8  # another at t=7.0
    peaks = detect_peaks(times, series, "motion_peak")
    peak_times = sorted(round(p.time, 1) for p in peaks)
    assert 3.0 in peak_times
    assert 7.0 in peak_times


def test_detect_peaks_respects_min_separation():
    times = [i * 0.5 for i in range(20)]
    series = [0.1] * 20
    series[6] = 0.9
    series[7] = 0.85  # 0.5s after the first — should be suppressed
    peaks = detect_peaks(times, series, "motion_peak", min_separation=4.0)
    assert len(peaks) == 1


def test_synthetic_bundle_generates_events():
    bundle = synthetic_bundle(
        duration=120.0,
        peaks=[
            {"time": 30.0, "motion": 0.9, "audio": 0.8, "speech": 1.0},
            {"time": 90.0, "motion": 0.7, "audio": 0.95, "speech": 1.0},
        ],
        scene_cuts=[29.0, 89.0],
    )
    assert bundle.duration == 120.0
    assert any(e.kind == "motion_peak" for e in bundle.events)
    assert any(e.kind == "audio_peak" for e in bundle.events)
    assert any(e.kind == "scene_cut" for e in bundle.events)


def test_analyst_builds_evidence_within_signal_bounds():
    bundle = synthetic_bundle(
        duration=120.0,
        peaks=[{"time": 60.0, "motion": 0.9, "audio": 0.85, "speech": 1.0}],
    )
    evidences = KAnalyst().analyze(bundle)
    assert evidences, "expected at least one evidence"
    for ev in evidences:
        # Evidence span never exceeds the video's physical bounds.
        assert ev.span.start >= 0.0
        assert ev.span.end <= bundle.duration
        # Signals are normalized into [0, 1].
        for name, value in ev.signals.items():
            assert 0.0 <= value <= 1.0, f"{name}={value} out of range"


def test_analyst_deduplicates_overlapping_triggers():
    # Two triggers 1s apart should collapse into a single evidence window.
    bundle = synthetic_bundle(
        duration=60.0,
        peaks=[
            {"time": 30.0, "motion": 0.9, "audio": 0.5},
            {"time": 31.0, "motion": 0.5, "audio": 0.9},
        ],
    )
    evidences = KAnalyst().analyze(bundle)
    assert len(evidences) == 1


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

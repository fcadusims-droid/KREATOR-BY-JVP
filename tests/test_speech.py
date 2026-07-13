"""Tests for the speech presence mapping — no model, pure function."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.speech import SpeechSegment, presence_series


def test_presence_series_marks_speech_windows():
    times = [i * 0.5 for i in range(20)]  # 0..9.5s
    segs = [SpeechSegment(2.0, 4.0, "hello"), SpeechSegment(7.0, 8.0, "there")]
    presence = presence_series(segs, times)
    assert presence[times.index(3.0)] == 1.0   # inside first segment
    assert presence[times.index(7.5)] == 1.0   # inside second
    assert presence[times.index(5.0)] == 0.0   # in the gap
    assert presence[times.index(0.0)] == 0.0   # before any speech


def test_presence_series_empty_inputs():
    assert presence_series([], [0.0, 1.0]) == [0.0, 0.0]
    assert presence_series([SpeechSegment(0.0, 1.0, "x")], []) == []


def test_speech_segment_to_dict():
    d = SpeechSegment(1.234, 5.678, "  hi  ").to_dict()
    assert d == {"start": 1.23, "end": 5.68, "text": "hi"}


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

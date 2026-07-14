"""Tests for K Validator — render-integrity checks. No ffmpeg needed for the
parser and the missing-file path."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.validator.check import _parse_probe, validate_render
from kreator.dsl import Cut, EditProgram, Transition


SAMPLE = """
  Duration: 00:00:29.20, start: 0.000000, bitrate: 1500 kb/s
  Stream #0:0[0x1](und): Video: h264 (High), yuv420p, 1282x720, 25 fps
  Stream #0:1[0x2](und): Audio: aac (LC), 44100 Hz, stereo, fltp, 129 kb/s
"""


def test_parse_probe_reads_duration_and_streams():
    info = _parse_probe(SAMPLE)
    assert abs(info["duration"] - 29.2) < 1e-6
    assert info["has_video"] and info["has_audio"]


def test_parse_probe_no_audio():
    info = _parse_probe("  Duration: 00:00:10.00\n  Stream #0:0: Video: h264\n")
    assert info["has_video"] and not info["has_audio"]


def test_validate_flags_missing_file():
    prog = EditProgram(cuts=[Cut(0.0, 10.0)])
    r = validate_render("/no/such/file.mp4", prog, has_audio=True)
    assert not r.ok and any("missing" in i or "empty" in i for i in r.issues)


def test_expected_duration_accounts_for_transitions():
    # 3 cuts of 10s = 30s, minus two 0.4s crossfades = 29.2s expected.
    prog = EditProgram(
        cuts=[Cut(0, 10), Cut(20, 30), Cut(40, 50)],
        transitions=[Transition(10, "crossfade", 0.4), Transition(20, "crossfade", 0.4)],
    )
    r = validate_render("/no/such/file.mp4", prog, has_audio=True)
    assert abs(r.expected - 29.2) < 1e-6


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

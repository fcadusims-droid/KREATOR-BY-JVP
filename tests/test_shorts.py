"""Tests for the Shorts builder — span fitting and program building.
Pure logic, no video, no ffmpeg."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.shorts import ShortSpec, build_short_program, fit_span
from kreator.types import Timespan

SPEC = ShortSpec(min_len=15.0, max_len=60.0)


def test_fit_span_grows_short_moments_symmetrically():
    fitted = fit_span(Timespan(100.0, 105.0), 600.0, SPEC)   # 5s → 15s
    assert abs(fitted.duration - 15.0) < 1e-6
    assert abs(fitted.center - 102.5) < 1e-6                  # same center


def test_fit_span_trims_long_moments_around_center():
    fitted = fit_span(Timespan(100.0, 200.0), 600.0, SPEC)   # 100s → 60s
    assert abs(fitted.duration - 60.0) < 1e-6
    assert abs(fitted.center - 150.0) < 1e-6


def test_fit_span_clamps_to_video_preserving_length():
    fitted = fit_span(Timespan(0.0, 5.0), 600.0, SPEC)       # near the start
    assert fitted.start == 0.0 and abs(fitted.duration - 15.0) < 1e-6
    fitted = fit_span(Timespan(596.0, 600.0), 600.0, SPEC)   # near the end
    assert fitted.end == 600.0 and abs(fitted.duration - 15.0) < 1e-6


def test_fit_span_whole_video_when_video_is_tiny():
    fitted = fit_span(Timespan(2.0, 4.0), 10.0, SPEC)        # 10s video < min 15s
    assert fitted.start == 0.0 and fitted.end == 10.0


def test_build_short_program_single_cut_reframed():
    prog = build_short_program(Timespan(30.0, 55.0), SPEC, focus_x=0.7,
                               rationale=["Rank #1: big explosion"])
    assert len(prog.cuts) == 1
    assert prog.cuts[0].source_start == 30.0 and prog.cuts[0].source_end == 55.0
    assert prog.reframe is not None and prog.reframe.focus_x == (0.7,)
    assert prog.reframe.aspect == "9:16"
    assert prog.rationale == ["Rank #1: big explosion"]


def test_build_short_program_subtitles_remapped_to_clip():
    from kreator.speech import SpeechSegment

    transcript = [SpeechSegment(32.0, 34.0, "inside the clip"),
                  SpeechSegment(90.0, 92.0, "outside — dropped")]
    prog = build_short_program(Timespan(30.0, 55.0), SPEC, transcript=transcript)
    assert len(prog.subtitles) == 1
    assert abs(prog.subtitles[0].start - 2.0) < 1e-6      # 32 - 30 in edited time
    assert prog.subtitles[0].text == "inside the clip"


def test_build_short_program_source_aspect_keeps_no_reframe():
    spec = ShortSpec(aspect=None)
    prog = build_short_program(Timespan(0.0, 20.0), spec)
    assert prog.reframe is None


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

"""Tests for pause removal (talking content) and its content detection."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.director import detect_content
from kreator.editor import pause_cut_plan
from kreator.speech import SpeechSegment


def test_pauses_are_cut_speech_is_kept():
    segs = [SpeechSegment(2.0, 6.0, "first thought"),
            SpeechSegment(12.0, 16.0, "after a long pause")]
    plan = pause_cut_plan(segs, 20.0, pad=0.25, min_pause=0.8)
    assert len(plan.segments) == 2
    a, b = plan.segments
    assert a.span.start <= 2.0 and a.span.end >= 6.0     # speech + padding kept
    assert b.span.start >= 6.5                            # the pause is gone
    assert plan.kept_duration < 20.0


def test_a_breath_does_not_become_a_cut():
    segs = [SpeechSegment(2.0, 6.0, "one sentence,"),
            SpeechSegment(6.5, 10.0, "then the next")]   # 0.5s gap = a breath
    plan = pause_cut_plan(segs, 15.0, min_pause=0.8)
    assert len(plan.segments) == 1                        # merged, no cut
    assert plan.segments[0].span.intersection(plan.segments[0].span) > 0


def test_never_cuts_mid_sentence():
    segs = [SpeechSegment(3.0, 9.0, "a long uninterrupted sentence")]
    plan = pause_cut_plan(segs, 30.0)
    seg = plan.segments[0]
    assert seg.span.start <= 3.0 and seg.span.end >= 9.0  # sentence intact


def test_empty_transcript_empty_plan():
    assert pause_cut_plan([], 60.0).segments == []


def test_detects_talking_content_from_speech_ratio():
    descs = ["a man talking to the camera in a room"]
    prof = detect_content(descs, speech_ratio=0.8)
    assert prof.preset == "talking"
    # Same descriptions but almost no speech → not talking content.
    prof = detect_content(descs, speech_ratio=0.1)
    assert prof.preset != "talking"


def test_gameplay_not_mistaken_for_talking():
    descs = ["a man is shooting a gun", "a police chase on the highway",
             "an explosion near a building"]
    prof = detect_content(descs, speech_ratio=0.5)
    assert prof.preset != "talking"          # game signal wins at 0.5 speech


def test_detect_content_without_ratio_unchanged():
    prof = detect_content(["a bank vault door", "driving through the city",
                           "heist briefing at the map"])
    assert prof.preset == "mission"          # the existing gameplay behavior


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

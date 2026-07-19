"""Tests for K Story — spoken-moment scoring and windowing. Pure, no video."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.speech import SpeechSegment
from kreator.story import score_segment, story_moments


def test_hook_and_question_beat_filler():
    hook, hr = score_segment("Here's why nobody tells you the secret.")
    filler, _ = score_segment("and then we walked over to the thing over there")
    question, qr = score_segment("What would you do in that situation?")
    assert hook > filler and question > filler
    assert any("hook" in r for r in hr)
    assert any("question" in r for r in qr)


def test_portuguese_cues():
    sc, reasons = score_segment("Deixa eu te contar o segredo disso, é incrível!")
    assert sc > 0.4
    assert any("hook" in r for r in reasons)


def test_audio_emphasis_lifts_score():
    calm, _ = score_segment("this was a good play", audio_emphasis=0.2)
    loud, lr = score_segment("this was a good play", audio_emphasis=0.9)
    assert loud > calm and any("energy" in r for r in lr)


def test_laughter_counts():
    sc, reasons = score_segment("and then hahaha I couldn't stop laughing")
    assert any("laughter" in r for r in reasons)


def test_story_moments_rank_the_quotable_windows():
    segs = [
        SpeechSegment(0.0, 4.0, "so today we're just getting started here"),
        SpeechSegment(4.0, 9.0, "Here's the secret nobody tells you about this."),
        SpeechSegment(9.0, 14.0, "It's actually incredible when you see it work."),
        SpeechSegment(14.0, 19.0, "anyway moving on to the next thing"),
        SpeechSegment(19.0, 24.0, "um and then we kept going for a while"),
    ]
    moments = story_moments(segs, top_n=2, min_len=8.0, max_len=20.0)
    assert moments
    top = moments[0]
    # The hook segment (4-9s) must be inside the top moment's window.
    assert top.span.start <= 4.0 and top.span.end >= 9.0
    assert "Quotable moment" in top.rationale
    # Quacks like a Candidate for the Shorts pipeline.
    assert hasattr(top, "span") and hasattr(top.breakdown, "features")
    assert "story_score" in top.breakdown.features


def test_moments_reach_minimum_length():
    segs = [SpeechSegment(float(i * 2), float(i * 2 + 2), f"line number {i} here")
            for i in range(20)]
    segs[5] = SpeechSegment(10.0, 12.0, "Here's why this is the best trick ever!")
    m = story_moments(segs, top_n=1, min_len=15.0, max_len=45.0)[0]
    assert m.span.duration >= 15.0 - 1e-6


def test_empty_transcript_no_moments():
    assert story_moments([], top_n=3) == []


def test_speech_led_routing_map():
    from kreator.director.job import _moment_source, _SPEECH_LED
    from kreator.director import ContentProfile
    assert "vlog" in _SPEECH_LED and "documentary" in _SPEECH_LED
    assert _moment_source(ContentProfile("vlog", "Vlog", preset="vlog")) == "speech"
    assert _moment_source(ContentProfile("shooter", "FPS", preset="punchy")) == "signal"


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

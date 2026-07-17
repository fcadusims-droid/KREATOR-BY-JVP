"""Tests for karaoke captions — word remap, ASS generation, compose fallback.
Pure logic, no ffmpeg."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.dsl import Caption, CaptionStyle, Cut, captions_from_transcript, write_ass
from kreator.speech import SpeechSegment, Word

CUTS = [Cut(10.0, 20.0), Cut(40.0, 50.0)]


def _seg(start, end, text, word_times):
    words = tuple(Word(s, e, t) for s, e, t in word_times)
    return SpeechSegment(start, end, text, words)


def test_words_remap_to_edited_timeline():
    seg = _seg(12.0, 14.0, "hello brave world",
               [(12.0, 12.5, "hello"), (12.6, 13.1, "brave"), (13.2, 14.0, "world")])
    caps = captions_from_transcript([seg], CUTS)
    assert len(caps) == 1
    words = caps[0].words
    assert [w[2] for w in words] == ["hello", "brave", "world"]
    assert abs(words[0][0] - 2.0) < 1e-6      # 12.0 → edited 2.0
    assert abs(words[2][0] - 3.2) < 1e-6
    assert caps[0].text == "hello brave world"


def test_caption_dropped_when_segment_was_cut():
    seg = _seg(25.0, 28.0, "gone", [(25.0, 26.0, "gone")])
    assert captions_from_transcript([seg], CUTS) == []


def test_segment_without_words_is_skipped():
    plain = SpeechSegment(12.0, 14.0, "no word data")
    assert captions_from_transcript([plain], CUTS) == []


def test_words_clamped_to_their_cut():
    # Word runs past the end of its cut → end clamped, later words dropped.
    seg = _seg(18.0, 44.0, "spills over",
               [(18.0, 19.0, "spills"), (19.5, 21.0, "over"), (43.0, 44.0, "far")])
    caps = captions_from_transcript([seg], CUTS)
    assert len(caps) == 1
    words = caps[0].words
    texts = [w[2] for w in words]
    assert "spills" in texts and "over" in texts
    assert "far" not in texts                 # starts inside the removed gap
    assert all(we <= 10.0 + 1e-2 for _, we, _ in words)


def test_ass_karaoke_tags_and_timing(tmp_path=None):
    import tempfile
    cap = Caption(2.0, 4.0, ((2.0, 2.5, "hello"), (2.8, 3.4, "world")))
    dest = str(Path(tempfile.mkdtemp()) / "k.ass")
    write_ass([cap], dest)
    text = Path(dest).read_text()
    # Gap folds into the previous word: hello covers 2.0→2.8 = 80cs.
    assert "{\\k80}hello" in text
    assert "{\\k60}world" in text             # last word: its own 0.6s
    assert "Dialogue: 0,0:00:02.00,0:00:04.00,K," in text
    assert "PlayResX: 1280" in text


def test_ass_style_is_parameterizable():
    import tempfile
    style = CaptionStyle(font="Impact", size=40, alignment=5, bold=False)
    cap = Caption(0.0, 1.0, ((0.0, 1.0, "hi"),))
    dest = str(Path(tempfile.mkdtemp()) / "s.ass")
    write_ass([cap], dest, style=style)
    text = Path(dest).read_text()
    assert "Style: K,Impact,40," in text
    assert ",5,30,30," in text                # alignment 5 (middle center)


def test_compose_prefers_karaoke_falls_back_to_plain():
    from kreator.dsl import compose_program
    from kreator.editor.condenser import EditPlan, KeepSegment
    from kreator.types import Timespan

    plan = EditPlan([KeepSegment(Timespan(10.0, 20.0), 0.6)], 30.0, 0.5)
    worded = [_seg(12.0, 13.0, "hi there", [(12.0, 12.4, "hi"), (12.5, 13.0, "there")])]
    plain = [SpeechSegment(12.0, 13.0, "hi there")]

    prog = compose_program(plan, transcript=worded, captions=True)
    assert prog.captions and not prog.subtitles
    # No word data anywhere → same request degrades to plain subtitles.
    prog = compose_program(plan, transcript=plain, captions=True)
    assert prog.subtitles and not prog.captions


def test_program_dict_includes_caption_words():
    from kreator.dsl import EditProgram
    prog = EditProgram(cuts=[Cut(0.0, 5.0)],
                       captions=[Caption(1.0, 2.0, ((1.0, 1.5, "yo"),))])
    ops = prog.to_dict()["operations"]
    cap = next(op for op in ops if op["type"] == "caption")
    assert cap["words"][0]["text"] == "yo"


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

"""Tests for the conversational parser — plain language → JobRequest.
Deterministic keyword grammar, no model."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.director import parse_instruction


def test_portuguese_full_request():
    req = parse_instruction(
        "faz 5 shorts de ~30 segundos com legenda animada, sem música")
    assert req.shorts == 5
    assert req.max_short_len == 30.0
    assert req.captions == "karaoke"
    assert req.music is False
    assert req.long_edit is False           # only Shorts were asked for
    assert req.notes                        # the reading is explained


def test_english_spec_example():
    req = parse_instruction(
        "Turn this gameplay into a ~30-second Short with animated captions")
    assert req.shorts == 1
    assert req.max_short_len == 30.0
    assert req.captions == "karaoke"
    assert req.long_edit is False


def test_number_words_pt_en():
    assert parse_instruction("três shorts por favor").shorts == 3
    assert parse_instruction("make five shorts").shorts == 5


def test_long_edit_plus_shorts():
    req = parse_instruction("corte completo leve + dois shorts")
    assert req.long_edit is True
    assert req.shorts == 2
    assert req.intensity == "light"


def test_vertical_long_edit():
    req = parse_instruction("edita o vídeo completo em vertical com legendas")
    assert req.long_edit is True and req.shorts == 0
    assert req.aspect == "9:16"
    assert req.captions == "plain"


def test_no_captions_wins_over_captions_keyword():
    assert parse_instruction("um short sem legendas").captions == "none"


def test_language_choice_pt_en():
    assert parse_instruction("um short com legendas em espanhol").language == "es"
    assert parse_instruction("a short with captions in english").language == "en"
    assert parse_instruction("legendas em português").language == "pt"
    assert parse_instruction("make a short").language is None   # auto-detect


def test_empty_or_unrelated_text_keeps_defaults():
    req = parse_instruction("obrigado!")
    assert req.long_edit is True and req.shorts == 0
    assert req.captions == "auto" and req.intensity == "auto"


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

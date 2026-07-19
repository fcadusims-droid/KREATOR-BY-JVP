"""Tests for the editing-template system (simple → cinematic)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.director import JobRequest, parse_instruction
from kreator.director.templates import TEMPLATES, apply_template


def test_template_fills_defaults():
    req = JobRequest()
    notes = apply_template(req, "montage")
    assert req.style == "montage" and req.intensity == "heavy"
    assert req.captions == "karaoke" and req.music is True
    assert notes and "template 'montage'" in notes[0]


def test_explicit_fields_beat_the_template():
    # The creator set captions=none and music off; the template must not undo it.
    req = JobRequest(captions="none", music=False)
    apply_template(req, "cinematic")
    assert req.captions == "none"      # kept
    assert req.music is False          # kept
    assert req.style == "cinematic"    # filled (was auto)


def test_simple_is_the_lightest_touch():
    req = JobRequest()
    apply_template(req, "simple")
    assert req.style == "clean" and req.intensity == "light"
    assert req.music is False


def test_auto_template_changes_nothing():
    req = JobRequest()
    assert apply_template(req, "auto") == []
    assert req.style == "auto" and req.intensity == "auto"


def test_all_templates_reference_valid_values():
    for name, tpl in TEMPLATES.items():
        assert tpl.get("style", "clean") in ("clean", "montage", "cinematic",
                                             "none", "auto")
        assert tpl.get("intensity", "light") in ("light", "medium", "heavy",
                                                 "auto")


def test_instruction_parser_picks_templates():
    assert parse_instruction("edita cinematográfico").template == "cinematic"
    assert parse_instruction("faz uma montagem pesada").template == "montage"
    assert parse_instruction("algo bem simples").template == "simple"


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

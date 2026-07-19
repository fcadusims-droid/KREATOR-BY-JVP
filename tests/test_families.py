"""Tests for the universal content-family classifier (vlog/doc/tutorial/…)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.director import EDITING_PRESETS, detect_content


def test_vlog_is_speech_plus_a_face():
    p = detect_content(["a woman talking to the camera in a room"],
                       speech_ratio=0.8, has_faces=True)
    assert p.genre == "vlog" and p.preset == "vlog"
    assert EDITING_PRESETS[p.preset]["keep_dialogue"] is True


def test_documentary_is_narration_without_a_steady_face():
    p = detect_content(
        ["an aerial shot of a mountain landscape",
         "a river through the forest", "the ocean at sunset"],
        speech_ratio=0.6, has_faces=False)
    assert p.genre == "documentary" and p.preset == "documentary"


def test_tutorial_from_screen_and_hands_cues():
    p = detect_content(
        ["close-up of hands on a keyboard", "a screen with a diagram",
         "a desk with tools"],
        speech_ratio=0.7, has_faces=True)
    assert p.genre == "tutorial"


def test_travel_is_visual_led_scenic():
    p = detect_content(
        ["a busy street market", "an old town plaza", "a temple on a hill",
         "a drone shot over the ocean"],
        speech_ratio=0.05, music_ratio=0.6)
    assert p.genre == "travel"
    assert EDITING_PRESETS[p.preset]["keep_dialogue"] is False


def test_gameplay_still_wins_over_families():
    # Strong game cues must not be mistaken for a real-world family, even with
    # speech present (a streamer talking over gameplay).
    p = detect_content(
        ["a soldier shooting a gun", "an explosion near a building",
         "a police chase through the city"],
        speech_ratio=0.6, has_faces=True)
    assert p.genre in ("shooter", "action_gameplay", "driving")


def test_backward_compatible_signature():
    # The old two-arg call still works (no faces/music info).
    assert detect_content([]).genre == "generic_gameplay"
    p = detect_content(["a man speaking into a microphone"], speech_ratio=0.8)
    assert p.preset in EDITING_PRESETS


def test_all_family_presets_are_complete():
    for fam in ("vlog", "documentary", "tutorial", "travel"):
        p = EDITING_PRESETS[fam]
        assert {"target_keep", "keep_dialogue", "min_cut", "zoom", "music",
                "note"} <= set(p)


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

"""Tests for the Director's content/genre detection — deterministic, no model.
The descriptions below are real SmolVLM outputs from GTA keyframes."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.director import detect_content, EDITING_PRESETS


GTA_HEIST_DESCS = [
    "Two police officers are standing in front of a white board.",
    "A player is driving a vehicle on a road in a video game.",
    "A truck is parked in a parking lot.",
    "Three characters are standing in front of a large bank vault door.",
    "Fingerprint screen.",
    "A man is being chased by two police officers.",
    "A man is delivering a loot box to a buyer.",
    "A man is walking through a casino.",
]


def test_detects_gta_heist_and_picks_mission_preset():
    prof = detect_content(GTA_HEIST_DESCS)
    assert prof.genre == "gta_heist"
    assert prof.preset == "mission"
    # Mission preset keeps more (don't over-cut, per real viewer feedback).
    assert EDITING_PRESETS[prof.preset]["target_keep"] >= 0.5
    assert EDITING_PRESETS[prof.preset]["keep_dialogue"] is True


def test_detects_shooter_as_punchy():
    descs = ["A soldier is shooting a gun.", "An explosion in a building.",
             "A man fires a weapon at an enemy.", "Two soldiers in a firefight."]
    prof = detect_content(descs)
    assert prof.genre == "shooter"
    assert EDITING_PRESETS[prof.preset]["target_keep"] <= 0.35


def test_every_preset_key_resolves():
    for descs in ([], ["a car driving on a road"], GTA_HEIST_DESCS):
        prof = detect_content(descs)
        assert prof.preset in EDITING_PRESETS


def test_empty_is_generic():
    assert detect_content([]).genre == "generic_gameplay"


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

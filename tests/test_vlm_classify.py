"""Tests for VLM description → scene type, and the visual keep signal.
Pure functions — no model, no torch."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.vlm import scene_type, is_keep, visual_keep_series, SceneLabel


def test_scene_type_from_real_descriptions():
    # Actual SmolVLM outputs observed on GTA keyframes.
    assert scene_type("A man is shooting a gun in a building.") == "action"
    assert scene_type("A white truck is parked in a parking lot.") == "idle"
    assert scene_type(
        "Three characters are standing in front of a white board with a map.") == "dialogue"
    assert scene_type("A man is walking down a street in a video game.") in {"travel", "dialogue"}


def test_scene_type_scenic_and_other():
    assert scene_type("A beautiful sunset over the mountains.") == "scenic"
    assert scene_type("") == "other"
    assert scene_type("blorptastic gibberish") == "other"


def test_is_keep_matches_keep_types():
    assert is_keep("A man is shooting a gun.")            # action
    assert is_keep("A sunset over the ocean.")            # scenic
    assert is_keep("Characters standing at a map board.") # dialogue
    assert not is_keep("A car parked in an empty lot.")   # idle


def test_visual_keep_series_marks_keep_scenes_only():
    times = [i * 1.0 for i in range(30)]  # 0..29s
    labels = [
        SceneLabel(10.0, "scenic", "a sunset"),
        SceneLabel(20.0, "idle", "a parked car"),
    ]
    series = visual_keep_series(labels, times, window=3.0)
    assert series[times.index(10.0)] == 1.0   # scenic → rescued
    assert series[times.index(20.0)] == 0.0   # idle → not rescued
    assert series[times.index(5.0)] == 0.0    # far from any label


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

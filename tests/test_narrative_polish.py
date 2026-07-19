"""Tests for K Narrative (chapters/hook) and K Polish (color correction)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.narrative import chapter_transcript, detect_hook
from kreator.polish import gray_world_fix
from kreator.speech import SpeechSegment


def _talk(pairs):
    t = 0.0
    segs = []
    for text in pairs:
        segs.append(SpeechSegment(t, t + 5.0, text))
        t += 5.0
    return segs


def test_chapters_split_on_topic_turn():
    # Two clearly different topics: cooking, then car maintenance.
    segs = _talk([
        "today we're cooking pasta with fresh tomato sauce and basil",
        "the pasta needs salt in the boiling water before the noodles",
        "add garlic and olive oil to the tomato sauce for flavor",
        "now let's switch to changing the oil in your car engine",
        "drain the old engine oil and replace the oil filter",
        "torque the filter and refill with fresh motor oil",
    ])
    chapters = chapter_transcript(segs, min_chapter=10.0, threshold=0.15)
    assert len(chapters) >= 2
    # The break lands around the topic switch (~15s).
    assert any(12.0 <= c.start <= 20.0 for c in chapters[1:])
    # Chapters carry topical titles.
    assert all(c.title for c in chapters)


def test_single_topic_is_one_chapter():
    segs = _talk(["we talk about pasta", "more about pasta sauce"])
    chapters = chapter_transcript(segs)
    assert len(chapters) == 1


def test_boundary_snaps_to_a_scene_cut():
    segs = _talk([
        "cooking pasta tomato sauce basil garlic kitchen",
        "cooking pasta boiling water salt noodles kitchen",
        "cooking pasta olive oil flavor sauce simmer",
        "car engine oil filter drain replace motor torque",
        "car engine oil filter refill fresh motor vehicle",
        "car engine oil filter check level dipstick vehicle",
    ])
    # The topic turn is at 15s (cooking → car); a scene cut sits at 16s.
    chapters = chapter_transcript(segs, scene_cuts=[16.0], min_chapter=14.0,
                                  snap_window=4.0)
    assert len(chapters) >= 2
    assert any(abs(c.start - 16.0) < 1e-6 for c in chapters[1:])


def test_detect_hook_finds_the_strong_opener():
    segs = _talk([
        "so um hi everyone",
        "Here's the secret nobody tells you about this!",
        "and then we kept going",
    ])
    hook = detect_hook(segs, within=30.0)
    assert hook is not None
    assert 5.0 <= hook.start <= 10.0     # the middle line is the hook


def test_gray_world_corrects_a_color_cast():
    # A blue-cast frame (blue mean well above red/green): expect the red gain
    # up and the blue gain down toward neutral.
    fix = gray_world_fix(0.30, 0.35, 0.60)
    assert fix is not None
    assert fix.r_gain > 1.0 and fix.b_gain < 1.0


def test_gray_world_noop_when_neutral():
    # An already-neutral, well-exposed frame → no correction.
    assert gray_world_fix(0.5, 0.5, 0.5) is None


def test_gains_are_clamped():
    # An extreme cast must not produce a wild gain.
    fix = gray_world_fix(0.02, 0.5, 0.5)
    assert fix is not None and fix.r_gain <= 1.6


def test_color_fix_in_filtergraph():
    from kreator.dsl import ColorFix, Cut, EditProgram
    from kreator.dsl.execute import _build_filtergraph

    prog = EditProgram(cuts=[Cut(0.0, 5.0)],
                       color_fix=ColorFix(1.2, 1.0, 0.85, 0.05))
    graph, vlabel, _a = _build_filtergraph(prog, has_audio=False, subs_path=None)
    assert "colorchannelmixer=rr=1.200:gg=1.000:bb=0.850" in graph
    assert "eq=brightness=0.050" in graph
    assert vlabel == "cfx"


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

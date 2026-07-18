"""Tests for K Motion — speed-aware timeline, planner, executor chains.
Pure logic, no ffmpeg run."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.dsl import Cut, EditProgram, Grade, PunchZoom, Shake, source_to_edited
from kreator.gamesense import GameEvent
from kreator.motion import STYLES, plan_motion, snap_to_beats
from kreator.types import Timespan


def test_slow_mo_stretches_the_edited_timeline():
    cuts = [Cut(10.0, 14.0), Cut(20.0, 24.0, speed=0.5), Cut(30.0, 34.0)]
    prog = EditProgram(cuts=cuts)
    assert prog.edited_duration == 4.0 + 8.0 + 4.0        # slow-mo doubles
    # A word spoken 2s into the slow-mo lands 4s into that cut's edited time.
    assert source_to_edited(22.0, cuts) == 4.0 + 4.0
    # After the slow-mo, positions shift by the stretch.
    assert source_to_edited(31.0, cuts) == 4.0 + 8.0 + 1.0


def test_atempo_chain_handles_extreme_slow_mo():
    from kreator.dsl.execute import _atempo_chain
    assert _atempo_chain(1.0) == ""
    assert _atempo_chain(0.5) == ",atempo=0.5"
    assert _atempo_chain(0.25) == ",atempo=0.5,atempo=0.5"
    assert _atempo_chain(2.0) == ",atempo=2"


def test_planner_splits_the_spine_around_the_kill():
    span = Timespan(100.0, 115.0)
    events = [GameEvent(108.0, "multikill", "hud", "DOUBLE KILL")]
    plan = plan_motion(span, events, style="montage")
    assert len(plan.cuts) == 3
    pre, slow, post = plan.cuts
    assert slow.speed == 0.5 and pre.speed == 1.0 and post.speed == 1.0
    assert slow.source_start <= 108.0 <= slow.source_end   # event inside slow-mo
    assert pre.source_start == 100.0 and post.source_end == 115.0
    assert plan.shakes and plan.punch_zooms and plan.grade.preset == "punchy"
    assert any("slow-mo" in r for r in plan.rationale)


def test_planner_none_style_is_the_raw_clip():
    span = Timespan(100.0, 115.0)
    events = [GameEvent(108.0, "multikill", "hud", "DOUBLE KILL")]
    plan = plan_motion(span, events, style="none")
    assert len(plan.cuts) == 1 and plan.cuts[0].speed == 1.0
    assert not plan.punch_zooms and not plan.shakes and plan.grade is None


def test_planner_without_events_keeps_single_cut_plus_grade():
    plan = plan_motion(Timespan(0.0, 15.0), [], style="montage")
    assert len(plan.cuts) == 1
    assert not plan.punch_zooms and not plan.shakes
    assert plan.grade and plan.grade.preset == "punchy"


def test_pulse_lands_in_edited_time_through_the_slow_mo():
    span = Timespan(100.0, 115.0)
    events = [GameEvent(108.0, "multikill", "hud", "DOUBLE KILL")]
    plan = plan_motion(span, events, style="montage")
    at = plan.punch_zooms[0].at
    # Edited time of 108.0 through the split cuts must match the DSL mapping.
    assert abs(at - source_to_edited(108.0, plan.cuts)) < 1e-6
    st = STYLES["montage"]
    assert at > 108.0 - 100.0 - st["slowmo_pre"]           # stretched, not raw


def test_executor_emits_speed_zoompan_shake_grade():
    from kreator.dsl.execute import _build_filtergraph
    prog = EditProgram(
        cuts=[Cut(0.0, 4.0), Cut(4.0, 6.0, speed=0.5)],
        punch_zooms=[PunchZoom(4.5, amount=0.22)],
        shakes=[Shake(4.5, 5.0, amplitude=10.0)],
        grade=Grade("punchy"))
    graph, vlabel, _a = _build_filtergraph(prog, has_audio=True,
                                           subs_path=None, main_dims=(1280, 720))
    assert "(PTS-STARTPTS)/0.5" in graph and "atempo=0.5" in graph
    assert "zoompan=z='1+0.22*exp(-abs(in-135)" in graph   # 4.5s * 30fps
    assert "fps=30" in graph                                # zoompan needs CFR
    assert "between(t,4.500,5.000)*10*sin(53*t)" in graph
    assert "eq=contrast=1.15" in graph
    assert vlabel == "grd"


def test_punch_zoom_without_dims_is_an_error():
    from kreator.dsl.execute import _build_filtergraph
    prog = EditProgram(cuts=[Cut(0.0, 4.0)], punch_zooms=[PunchZoom(1.0)])
    try:
        _build_filtergraph(prog, has_audio=False, subs_path=None)
        assert False, "should require main dimensions"
    except ValueError:
        pass


def test_snap_to_beats():
    beats = [1.0, 2.0, 3.0]
    assert snap_to_beats([1.2, 2.7, 9.0], beats) == [1.0, 3.0, 9.0]
    assert snap_to_beats([2.6], beats) == [2.6]    # 0.4s away > tol: stays
    assert snap_to_beats([1.2], []) == [1.2]


def test_program_dict_lists_motion_ops():
    prog = EditProgram(cuts=[Cut(0.0, 5.0, speed=0.5)],
                       punch_zooms=[PunchZoom(1.0)], shakes=[Shake(1.0, 1.5)],
                       grade=Grade("cinematic"))
    ops = prog.to_dict()["operations"]
    types = [op["type"] for op in ops]
    assert "punch_zoom" in types and "shake" in types and "grade" in types
    cut = next(op for op in ops if op["type"] == "cut")
    assert cut["speed"] == 0.5


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

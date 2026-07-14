"""Tests for the editing DSL — timeline remap, subtitle placement, program.
Pure logic, no ffmpeg."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.dsl import (Cut, EditProgram, Subtitle, source_to_edited,
                         subtitles_from_transcript)
from kreator.speech import SpeechSegment


CUTS = [Cut(10.0, 20.0), Cut(40.0, 50.0)]  # keep 10-20s and 40-50s of source


def test_source_to_edited_maps_kept_times():
    assert source_to_edited(10.0, CUTS) == 0.0     # start of first kept span
    assert source_to_edited(15.0, CUTS) == 5.0     # 5s into first span
    assert source_to_edited(40.0, CUTS) == 10.0    # start of second span (after 10s kept)
    assert source_to_edited(45.0, CUTS) == 15.0    # 5s into second span


def test_source_to_edited_returns_none_for_cut_time():
    assert source_to_edited(25.0, CUTS) is None    # in the removed gap
    assert source_to_edited(5.0, CUTS) is None      # before any kept span


def test_subtitles_land_on_edited_timeline():
    speech = [
        SpeechSegment(12.0, 16.0, "kept line"),     # inside first cut → edited 2..6
        SpeechSegment(25.0, 28.0, "cut line"),      # in the gap → dropped
        SpeechSegment(42.0, 46.0, "second line"),   # inside second cut → edited 12..16
    ]
    subs = subtitles_from_transcript(speech, CUTS)
    assert len(subs) == 2
    assert subs[0].text == "kept line"
    assert abs(subs[0].start - 2.0) < 1e-3 and abs(subs[0].end - 6.0) < 1e-2
    assert abs(subs[1].start - 12.0) < 1e-3


def test_subtitle_end_clamped_to_its_cut():
    # A line that starts inside a cut but runs past its end is clamped, not
    # allowed to spill onto the next (unrelated) segment.
    speech = [SpeechSegment(18.0, 44.0, "spills over")]
    subs = subtitles_from_transcript(speech, CUTS)
    assert len(subs) == 1
    # starts at edited 8 (18-10), ends at edited ~10 (cut1 ends at source 20)
    assert abs(subs[0].start - 8.0) < 1e-3
    assert subs[0].end <= 10.0 + 1e-2


def test_program_to_dict_lists_operations():
    prog = EditProgram(cuts=CUTS, subtitles=[Subtitle(1.0, 3.0, "hi")], height=720)
    d = prog.to_dict()
    assert d["height"] == 720
    types = [op["type"] for op in d["operations"]]
    assert types.count("cut") == 2 and "subtitle" in types
    assert d["edited_duration"] == 20.0


def test_compose_justifies_cuts_and_adds_zoom():
    from kreator.editor.condenser import EditPlan, KeepSegment
    from kreator.types import Timespan
    from kreator.dsl import compose_program

    segs = [KeepSegment(Timespan(0.0, 10.0), 0.6),   # intense → zoomed
            KeepSegment(Timespan(20.0, 30.0), 0.2)]  # calm → no zoom
    plan = EditPlan(segs, 40.0, 0.3)
    prog = compose_program(plan, zoom=True, rationale=["recognized X"])

    assert all(c.reason for c in prog.cuts)          # every cut is justified
    assert prog.rationale == ["recognized X"]
    assert len(prog.zooms) == 1                       # only the intense segment
    assert prog.zooms[0].start == 0.0 and prog.zooms[0].end == 10.0
    # justifications survive serialization
    ops = prog.to_dict()["operations"]
    assert all("reason" in op for op in ops if op["type"] == "cut")


def test_zoom_scale_for_overlap():
    from kreator.dsl.execute import _zoom_scale_for
    from kreator.dsl.program import EditProgram, Zoom

    prog = EditProgram(zooms=[Zoom(0.0, 10.0, 1.12)])
    assert _zoom_scale_for(prog, 5.0, 8.0) == 1.12    # cut overlaps the zoom
    assert _zoom_scale_for(prog, 12.0, 15.0) is None  # cut after the zoom


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

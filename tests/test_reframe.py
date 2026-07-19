"""Tests for reframing — pure geometry, compose, filtergraph, validation.
No cv2, no ffmpeg, no video."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.reframe import center_of_mass, crop_window, parse_aspect


def test_parse_aspect():
    assert abs(parse_aspect("9:16") - 0.5625) < 1e-9
    assert parse_aspect("1:1") == 1.0
    assert abs(parse_aspect("16:9") - 16 / 9) < 1e-9


def test_parse_aspect_rejects_malformed():
    for bad in ("vertical", "9x16", "9:", "0:16", "-9:16"):
        try:
            parse_aspect(bad)
            assert False, f"{bad!r} should have raised"
        except ValueError:
            pass


def test_crop_window_vertical_from_1080p():
    # 1920x1080 → 9:16 keeps full height; width 1080*9/16=607.5 → even 606.
    x, y, w, h = crop_window(1920, 1080, "9:16", focus_x=0.5)
    assert (w, h) == (606, 1080)
    assert y == 0
    assert x == (1920 - 606) // 2          # centered on the middle


def test_crop_window_clamps_focus_to_frame():
    x0, _, w, _ = crop_window(1920, 1080, "9:16", focus_x=0.0)
    x1, _, _, _ = crop_window(1920, 1080, "9:16", focus_x=1.0)
    assert x0 == 0                          # far-left action → window at 0
    assert x1 == 1920 - w                   # far-right action → flush right


def test_crop_window_shortens_when_source_is_taller():
    # A vertical source cropped to 16:9 keeps full width, crops height.
    x, y, w, h = crop_window(1080, 1920, "16:9", focus_x=0.5)
    assert w == 1080
    assert h == 606                          # 1080*9/16 → even floor
    assert y == (1920 - 606) // 2


def test_center_of_mass_follows_energy():
    assert center_of_mass([0.0, 0.0, 10.0, 0.0]) == (2 + 0.5) / 4
    assert center_of_mass([10.0, 0.0, 0.0, 0.0]) == (0 + 0.5) / 4


def test_center_of_mass_degrades_to_center():
    assert center_of_mass([]) == 0.5                  # nothing to read
    assert center_of_mass([0.0, 0.0, 0.0]) == 0.5     # nothing moved
    assert abs(center_of_mass([5.0, 5.0, 5.0, 5.0]) - 0.5) < 1e-9  # uniform pan


def test_center_weighting_tames_edge_flicker():
    from kreator.reframe import center_weighted

    # A kill-feed-like flicker at the right edge over mild central action.
    energies = [1.0] * 50 + [1.0] * 49 + [40.0]
    raw = center_of_mass(energies)
    weighted = center_of_mass(center_weighted(energies, 0.7))
    assert raw > 0.6                       # raw energy chases the edge
    assert abs(weighted - 0.5) < abs(raw - 0.5)   # the prior pulls it back
    # Zero strength is a no-op.
    assert center_weighted(energies, 0.0) == energies


def test_clamp_focus_bounds_the_crop():
    from kreator.reframe import clamp_focus

    assert clamp_focus(0.9, 0.12) == 0.62
    assert clamp_focus(0.1, 0.12) == 0.38
    assert clamp_focus(0.52, 0.12) == 0.52         # inside → untouched


def test_focus_profiles_exist_and_center_is_free():
    from kreator.reframe import FOCUS_PROFILES, cut_focus_centers

    assert {"fps", "follow", "center"} <= set(FOCUS_PROFILES)
    fps, follow = FOCUS_PROFILES["fps"], FOCUS_PROFILES["follow"]
    assert fps["center_weight"] > follow["center_weight"]
    assert fps["max_offset"] < follow["max_offset"]
    # "center" never opens the video — a bogus path proves it.
    assert cut_focus_centers("/nonexistent.mp4", [(0.0, 5.0)],
                             profile="center") == [0.5]


def test_compose_attaches_reframe_with_focus_and_reason():
    from kreator.dsl import compose_program
    from kreator.editor.condenser import EditPlan, KeepSegment
    from kreator.types import Timespan

    segs = [KeepSegment(Timespan(0.0, 10.0), 0.6),
            KeepSegment(Timespan(20.0, 30.0), 0.4)]
    prog = compose_program(EditPlan(segs, 40.0, 0.5), aspect="9:16",
                           focus_x=[0.3, 0.7])
    assert prog.reframe is not None
    assert prog.reframe.aspect == "9:16" and prog.reframe.strategy == "crop"
    assert prog.reframe.focus_x == (0.3, 0.7)
    assert prog.reframe.reason                      # the op is justified
    # no aspect requested → no reframe
    assert compose_program(EditPlan(segs, 40.0, 0.5)).reframe is None


def test_reframe_serialized_in_program_dict():
    from kreator.dsl import Cut, EditProgram, Reframe

    prog = EditProgram(cuts=[Cut(0.0, 10.0)],
                       reframe=Reframe("9:16", "crop", (0.4,)))
    ops = prog.to_dict()["operations"]
    rf = next(op for op in ops if op["type"] == "reframe")
    assert rf["aspect"] == "9:16" and rf["focus_x"] == [0.4]


def test_filtergraph_crops_per_cut_focus():
    from kreator.dsl import Cut, EditProgram, Reframe
    from kreator.dsl.execute import _build_filtergraph

    prog = EditProgram(cuts=[Cut(0.0, 10.0), Cut(20.0, 30.0)],
                       reframe=Reframe("9:16", "crop", (0.3, 0.7)))
    graph, _v, _a = _build_filtergraph(prog, has_audio=True, subs_path=None)
    assert "crop=w='trunc(min(iw,ih*9/16)/2)*2'" in graph
    assert "clip(iw*0.3000-ow/2,0,iw-ow)" in graph   # cut 1 follows its focus
    assert "clip(iw*0.7000-ow/2,0,iw-ow)" in graph   # cut 2 follows its own


def test_filtergraph_pad_strategy_adds_bars():
    from kreator.dsl import Cut, EditProgram, Reframe
    from kreator.dsl.execute import _build_filtergraph

    prog = EditProgram(cuts=[Cut(0.0, 10.0)], reframe=Reframe("9:16", "pad"))
    graph, _v, _a = _build_filtergraph(prog, has_audio=False, subs_path=None)
    assert "pad=w='trunc((max(iw,ih*9/16)+1)/2)*2'" in graph
    assert "crop=w=" not in graph


def test_filtergraph_without_reframe_unchanged():
    from kreator.dsl import Cut, EditProgram
    from kreator.dsl.execute import _build_filtergraph

    prog = EditProgram(cuts=[Cut(0.0, 10.0)])
    graph, _v, _a = _build_filtergraph(prog, has_audio=True, subs_path=None)
    assert "crop=" not in graph and "pad=" not in graph


def test_probe_parses_dimensions_not_stream_ids():
    from kreator.validator.check import _parse_probe

    stderr = (
        "Input #0, mov,mp4, from 'out.mp4':\n"
        "  Duration: 00:00:42.50, start: 0.000000, bitrate: 1000 kb/s\n"
        "  Stream #0:0[0x1](und): Video: h264 (High), yuv420p(progressive), "
        "606x1080 [SAR 1:1 DAR 101:180], 30 fps\n"
        "  Stream #0:1[0x2](und): Audio: aac (LC), 44100 Hz, stereo\n"
    )
    info = _parse_probe(stderr)
    assert (info["width"], info["height"]) == (606, 1080)
    assert info["duration"] == 42.5 and info["has_audio"]


def test_validator_aspect_check():
    from kreator.validator.check import _aspect_ok

    assert _aspect_ok(606, 1080, "9:16")        # even-floored crop width
    assert _aspect_ok(406, 720, "9:16")         # scale=-2:720 rounding
    assert not _aspect_ok(1920, 1080, "9:16")   # not reframed at all
    assert not _aspect_ok(0, 0, "9:16")         # unparsed dims never pass


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

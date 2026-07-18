"""Tests for the sfx and b-roll executors — filtergraph and library lookup.
Pure logic, no ffmpeg run."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.dsl import Broll, Cut, EditProgram, Music, Sfx
from kreator.dsl.execute import _build_filtergraph, _input_map, _reframed_dims


def test_input_map_fixed_order_music_sfx_broll():
    prog = EditProgram(cuts=[Cut(0.0, 10.0)],
                       music=[Music("bed.mp3", 0.0, 10.0)],
                       sfx=[Sfx(2.0, "hit.wav"), Sfx(5.0, "boom.wav")],
                       broll=[Broll("clip.mp4", 3.0, 2.0)])
    music_idx, sfx_idxs, broll_idxs = _input_map(prog, has_audio=True)
    assert music_idx == 1 and sfx_idxs == [2, 3] and broll_idxs == [4]
    # A silent main video takes no audio inputs; broll still gets one.
    music_idx, sfx_idxs, broll_idxs = _input_map(prog, has_audio=False)
    assert music_idx is None and sfx_idxs == [] and broll_idxs == [1]


def test_sfx_delayed_and_mixed_without_lowering_main_audio():
    prog = EditProgram(cuts=[Cut(0.0, 10.0)],
                       sfx=[Sfx(2.5, "hit.wav", volume=0.7)])
    graph, _v, alabel = _build_filtergraph(prog, has_audio=True, subs_path=None)
    assert "adelay=2500|2500" in graph and "volume=0.7" in graph
    assert "normalize=0" in graph            # the creator's audio stays full
    assert alabel == "amx"


def test_music_and_sfx_share_one_mix():
    prog = EditProgram(cuts=[Cut(0.0, 10.0)],
                       music=[Music("bed.mp3", 0.0, 10.0, 0.2)],
                       sfx=[Sfx(1.0, "hit.wav")])
    graph, _v, alabel = _build_filtergraph(prog, has_audio=True, subs_path=None)
    assert "amix=inputs=3" in graph and alabel == "amx"


def test_broll_scaled_shifted_and_gated_to_its_window():
    prog = EditProgram(cuts=[Cut(0.0, 10.0)],
                       broll=[Broll("clip.mp4", 3.0, 2.0)])
    graph, vlabel, _a = _build_filtergraph(prog, has_audio=False,
                                           subs_path=None, main_dims=(640, 360))
    assert "scale=640:360,setpts=PTS+3.000/TB" in graph
    assert "overlay=eof_action=repeat:enable='between(t,3.000,5.000)'" in graph
    assert vlabel == "bo0"


def test_broll_without_dims_is_an_error():
    prog = EditProgram(cuts=[Cut(0.0, 10.0)], broll=[Broll("c.mp4", 1.0, 1.0)])
    try:
        _build_filtergraph(prog, has_audio=False, subs_path=None)
        assert False, "should require main dimensions"
    except ValueError:
        pass


def test_broll_dims_follow_the_reframe():
    from kreator.dsl import Reframe
    prog = EditProgram(cuts=[Cut(0.0, 10.0)],
                       reframe=Reframe("9:16", "crop", (0.5,)))
    assert _reframed_dims(1920, 1080, prog) == (606, 1080)
    assert _reframed_dims(1920, 1080, EditProgram(cuts=[Cut(0.0, 1.0)])) == (1920, 1080)


def test_library_finds_sfx_and_broll_by_name():
    from kreator.library import KLibrary

    root = Path(tempfile.mkdtemp())
    (root / "sfx").mkdir()
    (root / "broll").mkdir()
    (root / "sfx" / "impact-hit.wav").write_bytes(b"x")
    (root / "broll" / "city-drone.mp4").write_bytes(b"x")
    lib = KLibrary(root)
    assert lib.find_sfx("impact").path.name == "impact-hit.wav"
    assert lib.find_broll("city").path.name == "city-drone.mp4"
    assert lib.find_sfx("nonexistent").path.name == "impact-hit.wav"  # fallback
    assert KLibrary(tempfile.mkdtemp()).find_sfx() is None


def test_program_dict_lists_sfx_and_broll():
    prog = EditProgram(cuts=[Cut(0.0, 5.0)],
                       sfx=[Sfx(1.0, "hit.wav", reason="impact on the peak")],
                       broll=[Broll("b.mp4", 2.0, 1.0, reason="cutaway")])
    types = [op["type"] for op in prog.to_dict()["operations"]]
    assert "sfx" in types and "broll" in types


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

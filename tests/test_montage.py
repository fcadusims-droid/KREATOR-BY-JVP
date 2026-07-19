"""Tests for K Montage — Ken Burns / B-roll planning and the executor chains."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.dsl import Cut, EditProgram, KenBurns, Music
from kreator.dsl.execute import _build_filtergraph, _zoom_chain
from kreator.montage import plan_broll, plan_ken_burns


def test_ken_burns_targets_the_long_held_shots():
    cuts = [Cut(0.0, 2.0), Cut(2.0, 10.0), Cut(10.0, 12.0), Cut(12.0, 20.0)]
    moves = plan_ken_burns(cuts, min_seconds=3.0)
    assert len(moves) == 2                      # only the 8s shots
    # Edited-time windows over the long cuts (2-10 and 12-20).
    windows = {(round(m.start), round(m.end)) for m in moves}
    assert windows == {(2, 10), (12, 20)}
    # Alternating direction keeps a sequence from feeling mechanical.
    assert moves[0].z_from != moves[1].z_from


def test_ken_burns_expr_compiles_into_zoompan():
    prog = EditProgram(cuts=[Cut(0.0, 8.0)],
                       ken_burns=[KenBurns(0.0, 8.0, 1.0, 1.12, pan=0.1)])
    chain = _zoom_chain(prog, (1280, 720))
    assert "zoompan=z='1+" in chain
    assert "between(in,0,240)" in chain          # 8s * 30fps window
    assert "clip((in-0)/240.0,0,1)" in chain
    assert "+0.10*(iw-iw/zoom)" in chain          # the pan drift


def test_music_ducking_uses_sidechaincompress():
    prog = EditProgram(cuts=[Cut(0.0, 10.0)],
                       music=[Music("bed.mp3", 0.0, 10.0, 0.3, duck=True)])
    graph, _v, alabel = _build_filtergraph(prog, has_audio=True, subs_path=None)
    assert "asplit=2[voice][duckkey]" in graph
    assert "sidechaincompress" in graph
    assert alabel == "amx"
    # Without duck, no sidechain — the plain mix.
    prog2 = EditProgram(cuts=[Cut(0.0, 10.0)],
                        music=[Music("bed.mp3", 0.0, 10.0, 0.3)])
    g2, _v2, _a2 = _build_filtergraph(prog2, has_audio=True, subs_path=None)
    assert "sidechaincompress" not in g2


def test_plan_broll_places_cutaways_over_narration():
    from kreator.speech import SpeechSegment

    root = Path(tempfile.mkdtemp())
    (root / "broll").mkdir()
    (root / "broll" / "city.mp4").write_bytes(b"x")
    (root / "broll" / "nature.mp4").write_bytes(b"x")
    cuts = [Cut(0.0, 60.0)]
    transcript = [SpeechSegment(float(i * 10), float(i * 10 + 4),
                                f"narration line number {i} goes here")
                  for i in range(6)]
    broll, notes = plan_broll(cuts, transcript, str(root),
                              gap_seconds=8.0, max_inserts=3)
    assert 1 <= len(broll) <= 3 and notes
    # Cutaways are spaced (we keep returning to the speaker).
    starts = [b.start for b in broll]
    assert all(b - a >= 8.0 for a, b in zip(starts, starts[1:]))


def test_plan_broll_empty_without_library():
    from kreator.speech import SpeechSegment
    cuts = [Cut(0.0, 30.0)]
    tr = [SpeechSegment(1.0, 5.0, "a line of narration here now")]
    assert plan_broll(cuts, tr, None) == ([], [])


def test_program_dict_lists_ken_burns():
    prog = EditProgram(cuts=[Cut(0.0, 8.0)],
                       ken_burns=[KenBurns(0.0, 8.0, 1.0, 1.1)])
    types = [op["type"] for op in prog.to_dict()["operations"]]
    assert "ken_burns" in types


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

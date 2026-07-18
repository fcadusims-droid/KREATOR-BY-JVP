"""Tests for K GameSense — vocabulary, event collapse, viral scoring.
Pure logic; no OCR, no video."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.gamesense import (GameEvent, announcer_events, classify_text,
                               collapse_events, viral_adjustment)
from kreator.speech import SpeechSegment
from kreator.types import Timespan


def test_vocabulary_spans_games_and_languages():
    assert classify_text("DOUBLE KILL") == ["multikill"]
    assert classify_text("~ WASTED ~") == ["death"]                 # GTA
    assert classify_text("you died") == ["death"]                   # souls
    assert classify_text("VICTORY!") == ["victory"]                 # generic
    assert classify_text("GOAL") == ["objective"]                   # sports
    assert classify_text("MISSÃO CONCLUÍDA") == ["victory"]         # pt
    assert classify_text("inimigo Eliminado por você") == ["death"]  # pt death
    assert classify_text("just walking around") == []


def test_killed_by_never_reads_as_a_kill():
    kinds = classify_text("Killed by xXSniperXx")
    assert kinds == ["death"]
    assert "kill" not in kinds


def test_collapse_merges_persistent_banners():
    evs = [GameEvent(10.0, "multikill", "hud", "DOUBLE KILL"),
           GameEvent(11.0, "multikill", "hud", "DOUBLE KILL"),   # same banner
           GameEvent(12.0, "multikill", "hud", "DOUBLE KILL"),   # still up
           GameEvent(20.0, "multikill", "hud", "TRIPLE KILL")]   # new one
    out = collapse_events(evs)
    assert len(out) == 2
    assert out[0].time == 10.0 and out[1].time == 20.0


def test_multikill_beats_a_death_sinks():
    up, up_reasons = viral_adjustment(
        [GameEvent(5.0, "multikill", "hud", "DOUBLE KILL"),
         GameEvent(4.0, "kill", "hud", "enemy down")])
    down, down_reasons = viral_adjustment(
        [GameEvent(5.0, "death", "hud", "Killed by foo")])
    assert up >= 0.6 and any("multikill" in r for r in up_reasons)
    assert down <= -0.4 and any("demote" in r for r in down_reasons)
    assert viral_adjustment([]) == (0.0, [])


def test_kill_stacking_is_capped():
    kills = [GameEvent(float(i), "kill", "hud", "enemy down") for i in range(8)]
    delta, reasons = viral_adjustment(kills)
    assert abs(delta - 0.15 * 3) < 1e-9          # capped at 3
    assert any("×3" in r for r in reasons)


def test_adjustment_is_bounded():
    pile = ([GameEvent(float(i), "multikill", "hud", "x") for i in range(5)]
            + [GameEvent(float(i), "victory", "hud", "x") for i in range(5)])
    delta, _ = viral_adjustment(pile)
    assert delta <= 0.8


def test_announcer_events_from_transcript_window():
    segs = [SpeechSegment(100.0, 102.0, "Double kill!"),
            SpeechSegment(300.0, 302.0, "enemy down")]
    evs = announcer_events(segs, Timespan(95.0, 110.0))
    assert len(evs) == 1
    assert evs[0].kind == "multikill" and evs[0].source == "announcer"


def test_reader_degrades_without_video():
    from kreator.gamesense import read_screen_events
    assert read_screen_events("x.mp4", []) == []   # no spans → no reads


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

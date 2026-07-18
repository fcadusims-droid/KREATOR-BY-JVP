"""Tests for K Learn — features, dataset store, deterministic taste model."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.gamesense import GameEvent
from kreator.learn import (FEATURES, feature_vector, learned_adjustment,
                           load_dataset, load_model, record_verdict,
                           save_model, train)


def _row(energy, kills, deaths):
    return feature_vector(
        {"visual_energy": energy, "audio_intensity": energy},
        [GameEvent(1.0, "kill", "hud", "x")] * kills
        + [GameEvent(2.0, "death", "hud", "x")] * deaths)


def test_feature_vector_order_and_counts():
    row = feature_vector({"visual_energy": 0.8, "hook_strength": 0.5},
                         [GameEvent(1.0, "multikill", "hud", "x"),
                          GameEvent(2.0, "kill", "hud", "x"),
                          {"kind": "kill"}])
    assert len(row) == len(FEATURES)
    assert row[FEATURES.index("visual_energy")] == 0.8
    assert row[FEATURES.index("n_multikill")] == 1.0
    assert row[FEATURES.index("n_kill")] == 2.0        # dataclass + dict both
    assert row[FEATURES.index("n_death")] == 0.0


def test_dataset_roundtrip_and_contract_guard():
    store = Path(tempfile.mkdtemp()) / "labels.jsonl"
    record_verdict(store, _row(0.9, 2, 0), 1)
    record_verdict(store, _row(0.2, 0, 1), 0)
    X, y = load_dataset(store)
    assert len(X) == 2 and y == [1, 0]
    # A row from an older feature contract is skipped, not misread.
    store.write_text(store.read_text().replace('"visual_energy"', '"old_feat"'),
                     encoding="utf-8")
    X, y = load_dataset(store)
    assert X == [] and y == []


def test_model_refuses_the_cold_start():
    X = [_row(0.9, 2, 0)] * 3 + [_row(0.2, 0, 1)] * 3   # 3 < MIN_PER_CLASS
    assert train(X, [1, 1, 1, 0, 0, 0]) is None


def test_model_learns_a_separable_taste_deterministically():
    # The creator approves kill-heavy clips, rejects death clips.
    X = [_row(0.8 + i * 0.01, 2, 0) for i in range(6)] + \
        [_row(0.3 + i * 0.01, 0, 1) for i in range(6)]
    y = [1] * 6 + [0] * 6
    m1, m2 = train(X, y), train(X, y)
    assert m1 == m2                                     # deterministic
    assert m1["train_accuracy"] == 1.0
    kills_w = m1["weights"][FEATURES.index("n_kill")]
    death_w = m1["weights"][FEATURES.index("n_death")]
    assert kills_w > 0 > death_w                        # inspectable + sane


def test_learned_adjustment_is_bounded_and_explained():
    X = [_row(0.8, 2, 0)] * 6 + [_row(0.3, 0, 1)] * 6
    model = train(X, [1] * 6 + [0] * 6)
    up, up_r = learned_adjustment(model, {"visual_energy": 0.85},
                                  [GameEvent(1.0, "kill", "hud", "x")] * 2)
    down, down_r = learned_adjustment(model, {"visual_energy": 0.3},
                                      [GameEvent(1.0, "death", "hud", "x")])
    assert 0 < up <= 0.25 and "taste" in up_r
    assert -0.25 <= down < 0 and "demote" in down_r
    assert learned_adjustment(None, {}, []) == (0.0, "")


def test_model_save_load_roundtrip():
    X = [_row(0.8, 2, 0)] * 5 + [_row(0.3, 0, 1)] * 5
    model = train(X, [1] * 5 + [0] * 5)
    path = Path(tempfile.mkdtemp()) / "model.json"
    save_model(model, path)
    assert load_model(path) == model
    assert load_model("/nonexistent/model.json") is None


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

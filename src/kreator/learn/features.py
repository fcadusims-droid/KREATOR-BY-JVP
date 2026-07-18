"""The taste model's feature vector — everything Kreator already knows about
a clip, in a fixed order. Pure.

Order is a contract: a trained model is only valid for the FEATURES list it
was trained on, so the list is versioned data, not an implementation detail.
"""

from __future__ import annotations

# Signal-layer features (from the Clipper's ScoreBreakdown) followed by
# GameSense event counts. Extend only by appending; never reorder.
FEATURES: tuple[str, ...] = (
    "visual_energy", "audio_intensity", "hook_strength",
    "speech_density", "scene_activity", "trigger_strength",
    "n_multikill", "n_kill", "n_death", "n_victory",
    "n_objective", "n_announcement", "n_ui",
)


def feature_vector(signals: dict, events: list) -> list[float]:
    """(clip signals, GameSense events) → the ordered feature values.

    ``signals`` is the Clipper's per-signal dict; ``events`` are the clip's
    GameEvents (or dicts with a "kind"). Missing signals read as 0 — a model
    trained on this vector tolerates clips analyzed without some stage.
    """
    counts: dict[str, int] = {}
    for e in events or []:
        kind = e.get("kind") if isinstance(e, dict) else e.kind
        counts[kind] = counts.get(kind, 0) + 1

    row: list[float] = []
    for name in FEATURES:
        if name.startswith("n_"):
            row.append(float(counts.get(name[2:], 0)))
        else:
            row.append(float((signals or {}).get(name, 0.0)))
    return row

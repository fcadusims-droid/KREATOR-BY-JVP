"""Per-signal scoring of a clip candidate.

The signals mirror the spec's K Clipper vocabulary — hook, emotional peak,
conflict/energy, reveal, quotable line, visual energy — mapped onto the
deterministic features the Evidence Layer produces, plus optional model labels
when a VLM/ASR backend fed them in.

Weights live in a ``ScoringProfile``. Today it holds sensible niche-agnostic
defaults; in Phase 2 this is exactly where ``channel_profile.json`` plugs in,
so the ranking calibrates per channel. Keeping weights explicit and versioned
(not baked into a prompt) is what makes the decision auditable and testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..evidence.types import Evidence, bucket


@dataclass(frozen=True)
class ScoringProfile:
    """Named, versioned set of signal weights. Sums are not required to be 1;
    the total is normalized by the weight sum so profiles stay comparable."""

    name: str = "default-gameplay"
    version: str = "1"
    weights: dict[str, float] = field(
        default_factory=lambda: {
            "visual_energy": 1.0,   # action peaks — core of gameplay highlights
            "audio_intensity": 0.9, # reactions, hits, explosions
            "hook_strength": 1.1,   # a sharp opener retains on Shorts
            "scene_activity": 0.5,  # editing density around the moment
            "speech_density": 0.4,  # narrated / quotable moments
            "event_confidence": 1.2,  # VLM-labelled event (0 when signal-only)
            "trigger_strength": 0.6,  # how strongly the raw signal fired
        }
    )


def _feature_vector(ev: Evidence) -> dict[str, float]:
    """Assemble the scored features from evidence signals + optional labels."""
    features = dict(ev.signals)
    # Fold a VLM event confidence (if any) into a scored feature. Absent in the
    # signal-only path, so it contributes nothing there.
    conf = ev.labels.get("conf")
    if isinstance(conf, (int, float)):
        features["event_confidence"] = bucket(float(conf))
    return features


@dataclass(frozen=True)
class ScoreBreakdown:
    total: float                     # bucketed 0..1
    contributions: dict[str, float]  # signal -> weighted contribution
    features: dict[str, float]       # signal -> raw normalized value


def score_evidence(ev: Evidence, profile: ScoringProfile) -> ScoreBreakdown:
    """Deterministically score one evidence into a stable total + breakdown."""
    features = _feature_vector(ev)
    weight_sum = sum(abs(w) for w in profile.weights.values()) or 1.0

    contributions: dict[str, float] = {}
    acc = 0.0
    for signal, weight in profile.weights.items():
        value = float(features.get(signal, 0.0))
        contribution = weight * value
        contributions[signal] = contribution
        acc += contribution

    total = bucket(acc / weight_sum)
    return ScoreBreakdown(total=total, contributions=contributions, features=features)

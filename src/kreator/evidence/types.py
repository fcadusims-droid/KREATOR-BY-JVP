"""Evidence dataclass + the two normalization primitives that keep the
Planner's decisions stable across probabilistic re-runs.

`bucket` and `hysteretic` are the mechanism the runtime spec (§4-RT) calls
"buckets + hysteresis": continuous scores are reduced to stable ranges so an
irrelevant wobble in a model's confidence between two runs does not flip the
plan. They are pure functions — trivially testable, no dependencies.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from ..types import Timespan


def bucket(x: float, levels: int = 20) -> float:
    """Quantize a score in [0, 1] to a fixed grid of ``levels`` steps.

    Two nearly-identical scores (0.8149 vs 0.8151) collapse to the same
    bucket, so downstream ordering does not depend on float noise. This is the
    stability half of "buckets + hysteresis".
    """
    if levels < 1:
        raise ValueError("levels must be >= 1")
    x = min(1.0, max(0.0, x))
    return round(x * levels) / levels


def hysteretic(
    value: float, previous: float | None, *, rise: float, fall: float
) -> float:
    """Apply hysteresis: only accept a change large enough to clear a band.

    A new ``value`` replaces ``previous`` only if it rises by at least ``rise``
    or falls by at least ``fall``; otherwise the previous value is held. This
    stops a signal that hovers around a threshold from oscillating the decision
    on every re-run. With no previous value, the new value passes through.
    """
    if previous is None:
        return value
    if value >= previous + rise or value <= previous - fall:
        return value
    return previous


@dataclass
class Evidence:
    """A normalized, versioned observation over a signal-bounded span.

    Invariant enforced by the Evidence Layer: ``span`` comes from the
    deterministic Signal Layer and is *never* redefined by a model. Labels are
    appended on top of that fixed span; they describe it, they cannot move it.
    """

    span: Timespan
    signals: dict[str, float] = field(default_factory=dict)  # normalized 0..1
    labels: dict[str, object] = field(default_factory=dict)  # from VLM/ASR, optional
    source: str = "signal-only"  # provenance of the labels

    @property
    def evidence_id(self) -> str:
        """Content hash — stable for identical spans, signals, labels, source."""
        payload = {
            "span": [round(self.span.start, 3), round(self.span.end, 3)],
            "signals": {k: round(v, 6) for k, v in sorted(self.signals.items())},
            "labels": self.labels,
            "source": self.source,
        }
        blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()[:16]

    def signal(self, name: str, default: float = 0.0) -> float:
        return float(self.signals.get(name, default))

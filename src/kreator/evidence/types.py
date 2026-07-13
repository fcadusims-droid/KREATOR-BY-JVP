"""Evidence dataclass + the two normalization primitives from the runtime
spec's "buckets + hysteresis" (§4-RT), which keep the Planner's decisions
stable under probabilistic inference.

Both are pure functions with no dependencies. Their roles differ by scope:

- ``bucket`` acts *within a single run*: it quantizes each score so float
  noise (0.8149 vs 0.8151) cannot reorder the ranking. This is applied on
  every feature the Analyst produces today.
- ``hysteretic`` acts *across runs*: it holds a value unless a new one clears
  a band, so a signal hovering at a threshold doesn't flip between two
  analyses. It needs a *previous* value to compare against, so it activates
  only once there is re-run/persisted state to feed it — which the single-pass
  MVP does not yet have. It is provided and tested here as the primitive that
  layer will use, not wired into the one-shot path.
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

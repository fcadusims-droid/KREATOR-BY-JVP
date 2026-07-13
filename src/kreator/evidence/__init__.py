"""Evidence Layer — turns raw signals into structured, normalized evidence.

This is the boundary where probabilistic inference *may* enter (VLM/ASR), but
in a contained way: models only ever label a slice the signals already
flagged, and they can never move, stretch, or invent the physical limits of a
signal. When no model backend is configured, evidence is built from the
deterministic signals alone — which is enough to exercise the Planner and run
E1's ranking end-to-end without a GPU.
"""

from .types import Evidence, bucket, hysteretic
from .analyst import KAnalyst

__all__ = ["Evidence", "KAnalyst", "bucket", "hysteretic"]

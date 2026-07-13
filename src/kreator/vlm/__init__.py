"""VLM enablement — the CPU-only groundwork that makes visual understanding
reachable without a GPU.

The expensive part of a VLM is running it on every frame. Kreator never does
that: the keyframe sampler here selects the ~10–40 frames actually worth a
label (one per episode, scene boundaries, interest peaks, and — crucially — the
low-action stretches the signal proxy *cannot* classify, e.g. a scenic pause).
A VLM backend then labels only those. See ``docs/vlm-without-gpu.md``.
"""

from .keyframes import Keyframe, select_keyframes

__all__ = ["Keyframe", "select_keyframes"]

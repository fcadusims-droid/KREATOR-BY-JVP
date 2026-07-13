"""VLM enablement — local, offline visual understanding without a GPU.

The expensive part of a VLM is running it on every frame. Kreator never does
that: the keyframe sampler selects the ~10–40 frames worth a label (one per
episode, scene boundaries, interest peaks, and — crucially — the low-action
stretches the signal proxy *cannot* classify, e.g. a scenic pause). A local
CPU VLM (SmolVLM) then *describes* only those frames, and a deterministic
keyword classifier maps each description to a scene type. Scenic / dialogue /
action scenes are rescued into the edit. See ``docs/vlm-without-gpu.md``.
"""

from .keyframes import Keyframe, select_keyframes
from .classify import KEEP_TYPES, is_keep, scene_type
from .backends import LocalVLMBackend
from .label import SceneLabel, label_keyframes, visual_keep_series

__all__ = [
    "Keyframe", "select_keyframes",
    "KEEP_TYPES", "is_keep", "scene_type",
    "LocalVLMBackend",
    "SceneLabel", "label_keyframes", "visual_keep_series",
]

"""Signal Layer — the deterministic foundation of the whole pipeline.

Nothing here depends on a probabilistic model: the same input bits always
produce the same signals. It extracts cheap, CPU-only time series (motion via
optical flow, audio energy, scene cuts) and flags discrete trigger events from
them. Everything downstream consumes this bundle instead of the raw video, so
the expensive layers only ever look at signal-flagged slices.

Heavy dependencies (OpenCV, PySceneDetect, audio decoders) are imported lazily
inside the functions that need them, so importing this package — and unit-
testing the Planner — never requires them.
"""

from .pipeline import analyze_video, detect_peaks, synthetic_bundle

__all__ = ["analyze_video", "detect_peaks", "synthetic_bundle"]

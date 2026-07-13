"""Scene-cut detection via PySceneDetect (BSD-3), lazily imported."""

from __future__ import annotations


def detect_scene_cuts(video_path: str, threshold: float = 27.0) -> list[float]:
    """Return the timecodes (seconds) of detected scene boundaries.

    Uses PySceneDetect's content detector. A cut at a moment often means the
    action changed — a useful, cheap, fully deterministic signal.
    """
    from scenedetect import detect, ContentDetector  # type: ignore

    scene_list = detect(video_path, ContentDetector(threshold=threshold))
    # detect() returns (start, end) FrameTimecode pairs; a "cut" is each
    # boundary between consecutive scenes.
    cuts: list[float] = []
    for _start, end in scene_list[:-1] if scene_list else []:
        cuts.append(float(end.get_seconds()))
    return cuts

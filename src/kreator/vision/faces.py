"""Face detection via OpenCV's YuNet — resolved flexibly, degrades gracefully.

The model (``face_detection_yunet``, Apache-2.0, ~230 KB) is resolved from, in
order: the ``KREATOR_FACE_MODEL`` env var, a copy vendored next to this file,
or a well-known OpenCV data path. If none is found, ``FaceDetector`` reports
unavailable and the caller keeps using motion focus — face reframing is an
enhancement, never a hard dependency (the CPU-offline contract holds either
way).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

_MODEL_NAME = "face_detection_yunet_2023mar.onnx"


def _resolve_model() -> str | None:
    env = os.environ.get("KREATOR_FACE_MODEL")
    if env and Path(env).exists():
        return env
    here = Path(__file__).resolve().parent / "data" / _MODEL_NAME
    if here.exists():
        return str(here)
    # Some OpenCV builds ship the model under their data dir.
    try:
        import cv2  # type: ignore

        cand = Path(cv2.data.haarcascades).parent / _MODEL_NAME
        if cand.exists():
            return str(cand)
    except Exception:
        pass
    return None


def detect_faces_available() -> bool:
    """Can we detect faces here? (cv2 + the YuNet model both present.)"""
    if _resolve_model() is None:
        return False
    try:
        import cv2  # type: ignore

        return hasattr(cv2, "FaceDetectorYN_create")
    except Exception:
        return False


@dataclass(frozen=True)
class Face:
    x: float          # box left, in frame pixels
    y: float
    w: float
    h: float
    score: float

    @property
    def cx(self) -> float:
        return self.x + self.w / 2.0

    @property
    def area(self) -> float:
        return self.w * self.h


class FaceDetector:
    """Thin wrapper over cv2.FaceDetectorYN. ``.available`` is False when the
    model or the API is missing — callers check it and degrade."""

    def __init__(self, *, score_threshold: float = 0.6,
                 input_width: int = 320) -> None:
        self._model = _resolve_model()
        self._det = None
        self._input_width = input_width
        self._score = score_threshold

    @property
    def available(self) -> bool:
        return self._model is not None

    def _detector(self, w: int, h: int):
        import cv2  # type: ignore

        if self._det is None:
            self._det = cv2.FaceDetectorYN_create(
                self._model, "", (w, h), score_threshold=self._score)
        self._det.setInputSize((w, h))
        return self._det

    def detect(self, frame) -> list[Face]:
        """Faces in one BGR frame. YuNet reads a downscaled copy (its input
        width) and the boxes are mapped back to full-frame pixels."""
        import cv2  # type: ignore

        h, w = frame.shape[:2]
        scale = self._input_width / float(w)
        small = cv2.resize(frame, (self._input_width, max(1, int(h * scale))))
        sh, sw = small.shape[:2]
        _n, faces = self._detector(sw, sh).detect(small)
        out: list[Face] = []
        if faces is not None:
            for f in faces:
                out.append(Face(float(f[0]) / scale, float(f[1]) / scale,
                                float(f[2]) / scale, float(f[3]) / scale,
                                float(f[-1])))
        return out

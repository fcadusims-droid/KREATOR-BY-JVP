"""Model backends for the Evidence Layer, behind narrow interfaces.

The product spec's governing rule — "models are commodity; infrastructure is
not" — is enforced structurally here: the VLM and ASR are pluggable adapters,
and the rest of the system depends only on these Protocols, never on a
specific model. On a GPU box you plug in Qwen2.5-VL and WhisperX; with no
backend configured the Evidence Layer runs signal-only, which is enough to
produce a ranking and validate the Planner.

Nothing in this module imports a heavy dependency at import time. The real
adapters import lazily inside their methods, so the deterministic pipeline
stays runnable on a plain CPU with none of them installed.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..types import Timespan


@runtime_checkable
class VLMBackend(Protocol):
    """Vision-language labeller. Sees only a signal-flagged slice, never the
    whole video, and returns semantic labels with a confidence score."""

    name: str

    def label(self, video_path: str, span: Timespan) -> dict[str, object]:
        """Return labels for ``span``, e.g. ``{"event": "explosion",
        "conf": 0.82}``. Must not depend on anything outside ``span``."""
        ...


@runtime_checkable
class ASRBackend(Protocol):
    """Speech-to-text over a slice. Used to surface quotable lines; it never
    redefines segment boundaries — those come from VAD in the Signal Layer."""

    name: str

    def transcribe(self, video_path: str, span: Timespan) -> str:
        """Return the transcript text spoken within ``span`` (may be empty)."""
        ...


class QwenVLBackend:
    """Adapter for Qwen2.5-VL (Apache-2.0), the spec's default VLM.

    Imports transformers/torch lazily so this module stays importable without
    them. Instantiate only where a GPU is available.
    """

    name = "qwen2.5-vl"

    def __init__(self, model_id: str = "Qwen/Qwen2.5-VL-7B-Instruct") -> None:
        self.model_id = model_id
        self._model = None
        self._processor = None

    def _ensure_loaded(self) -> None:  # pragma: no cover - requires GPU + weights
        if self._model is not None:
            return
        from transformers import (  # type: ignore
            AutoProcessor,
            Qwen2_5_VLForConditionalGeneration,
        )

        self._processor = AutoProcessor.from_pretrained(self.model_id)
        self._model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            self.model_id, torch_dtype="auto", device_map="auto"
        )

    def label(self, video_path: str, span: Timespan) -> dict[str, object]:  # pragma: no cover
        self._ensure_loaded()
        raise NotImplementedError(
            "Wire frame sampling of `span` + a JSON-constrained prompt here on "
            "the GPU box. Kept unimplemented so the CPU pipeline stays runnable."
        )


class WhisperXBackend:
    """Adapter for WhisperX (BSD-2), the spec's default ASR.

    Word-level timestamps land here in Phase 1's K Subtitle; for E1 we only
    need the text of a slice to detect quotable lines.
    """

    name = "whisperx"

    def __init__(self, model_id: str = "large-v2") -> None:
        self.model_id = model_id
        self._model = None

    def transcribe(self, video_path: str, span: Timespan) -> str:  # pragma: no cover
        raise NotImplementedError(
            "Wire faster-whisper over the audio of `span` here on the GPU box."
        )

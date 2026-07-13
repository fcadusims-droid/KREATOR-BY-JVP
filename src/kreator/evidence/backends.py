"""Model-backend interfaces for the Evidence Layer (K Analyst / K Clipper).

The product spec's governing rule — "models are commodity; infrastructure is
not" — is enforced structurally: K Clipper's evidence layer depends only on
these narrow Protocols, never on a specific model. With no backend configured
it runs signal-only, which is enough to produce a ranking (E1).

These Protocols are the *optional* enrichment hook for K Clipper. The concrete,
working model backends the rest of Kreator uses live elsewhere and run locally
on CPU:

- ``kreator.speech`` — faster-whisper transcription (dialogue).
- ``kreator.vlm`` — SmolVLM scene description (visual understanding).

A K Clipper VLM/ASR adapter would implement the Protocols below by reusing
those; kept as interfaces only so nothing here pins a heavy dependency.
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

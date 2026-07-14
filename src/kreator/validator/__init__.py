"""K Validator — the "validation" step before the video is handed over.

Kreator can't produce inauthentic content (it only ever cuts the creator's own
footage — see docs/not-generative.md), so this validator checks *render
integrity*: does the output actually match the plan? Right length, real video
and audio streams, not an empty/black file. If the render is broken, the caller
finds out here instead of shipping a bad video.
"""

from .check import ValidationReport, validate_render

__all__ = ["ValidationReport", "validate_render"]

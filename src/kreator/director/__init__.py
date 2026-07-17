"""Director — Kreator's autonomous "how should this be edited?" decision.

Given what the other layers *understood* about a video (VLM scene descriptions,
signals, speech), the Director decides — with no user input — what kind of
content it is and which editing preset fits. This is what lets the app run
fully autonomously: upload a video, and Kreator figures out the rest.

Deterministic and rule-based (the AI describes; the Director decides), so it's
testable without any model.
"""

from .content import ContentProfile, EDITING_PRESETS, detect_content
from .auto import Understanding, autonomous_edit, understand_video
from .job import JobRequest, run_job
from .instructions import parse_instruction

__all__ = ["ContentProfile", "EDITING_PRESETS", "detect_content",
           "autonomous_edit", "understand_video", "Understanding",
           "JobRequest", "run_job", "parse_instruction"]

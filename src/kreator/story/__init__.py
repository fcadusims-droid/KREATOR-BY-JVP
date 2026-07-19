"""K Story — find the clippable moments in *what was said*.

Gameplay moments are found by action and the game's HUD; talking moments —
vlog, podcast, interview, documentary — are found in the transcript. A line
that lands (a hook, a question, a strong claim, a personal story beat, a
laugh) is what a human clips, and signal energy is blind to it. K Story scores
the creator's own words (never writes any), groups them into clip-length
windows on sentence boundaries, and ranks them — the same shape of ranked
candidate the Clipper produces, so the Shorts pipeline consumes either.

A deterministic keyword+prosody scorer always runs offline; an optional local
LLM (Ollama) can re-rank with reasons and degrades away when absent.
"""

from .score import score_segment
from .moments import StoryMoment, story_moments

__all__ = ["score_segment", "StoryMoment", "story_moments"]

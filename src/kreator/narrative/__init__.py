"""K Narrative — the structure of a long piece: chapters and the hook.

A documentary or a long vlog isn't just a tighter cut; it has a shape. K
Narrative reads the creator's own transcript (never writes any) and finds
where the topic turns, so the edit carries chapter markers, and finds the
strongest opening beat, so the piece can lead with a hook. Deterministic:
topic turns are lexical shifts snapped to scene cuts; the hook is the
best-scoring line in the opening stretch.
"""

from .chapters import Chapter, chapter_transcript, detect_hook

__all__ = ["Chapter", "chapter_transcript", "detect_hook"]

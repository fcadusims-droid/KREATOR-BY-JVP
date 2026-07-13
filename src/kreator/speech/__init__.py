"""Speech understanding — when someone is talking, and what they say.

For no-commentary gameplay this is *in-game* dialogue (mission talk, NPC lines,
story beats). It matters to the editor because a dialogue moment can be quiet —
low motion, no gunfire — yet be exactly what a viewer stays for. The pure
action proxy would cut it; speech presence rescues it.

Runs on CPU via faster-whisper (small model, int8), lazily imported so the rest
of the package doesn't require it. It yields both *presence* (timestamps, the
signal the editor uses) and *content* (the transcript, a stored artifact that
later serves K Subtitle and K SEO).
"""

from .transcribe import SpeechSegment, presence_series, transcribe

__all__ = ["SpeechSegment", "presence_series", "transcribe"]

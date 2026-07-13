"""Map a VLM's free-text frame description to a scene type — deterministically.

The lesson from CPU-model testing: a small local VLM is unreliable when asked to
*judge* ("is this intense?") but accurate when asked to *describe* ("a man is
shooting a gun"). So the VLM produces a description (its strength) and this
module applies explicit keyword rules to reach a scene type (the Planner's job).
Pure and testable — no model needed to exercise it.

Scene types and how the editor treats them:
- ``action``   — keep (already caught by signals, VLM confirms)
- ``dialogue`` — keep: a briefing/conversation, often quiet (signals miss it)
- ``scenic``   — keep: a view worth lingering on (signals read as idle)
- ``travel``   — neutral: driving/walking with nothing notable
- ``idle``     — cut candidate: parked, empty, menu, nothing happening
"""

from __future__ import annotations

# Checked in priority order — the first category with a keyword hit wins.
_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("action", ("shoot", "gun", "fire", "firing", "explos", "fight", "combat",
                "crash", "chase", "weapon", "battl", "attack", "blood", "police chase")),
    ("scenic", ("sunset", "sunrise", "landscape", "mountain", "ocean", "beach",
                "scenery", "scenic", "forest", "nature", "horizon", "skyline",
                "waterfall", "field", "valley", "view of")),
    ("dialogue", ("board", "map", "briefing", "meeting", "conversation", "talking",
                  "standing in front", "desk", "whiteboard", "presentation",
                  "group of people", "characters are standing")),
    ("idle", ("parked", "empty", "menu", "loading", "nothing", "still",
              "no one", "deserted")),
    ("travel", ("driving", "road", "highway", "street", "walking", "car is",
                "truck is", "riding", "vehicle")),
]

# Which scene types the editor should rescue (lift interest to keep them).
KEEP_TYPES = frozenset({"action", "scenic", "dialogue"})


def scene_type(description: str) -> str:
    """Classify a description into a scene type, or ``"other"`` if nothing hits."""
    text = (description or "").lower()
    for label, keywords in _RULES:
        if any(kw in text for kw in keywords):
            return label
    return "other"


def is_keep(description: str) -> bool:
    """True if the description names a scene worth keeping (action/scenic/dialogue)."""
    return scene_type(description) in KEEP_TYPES

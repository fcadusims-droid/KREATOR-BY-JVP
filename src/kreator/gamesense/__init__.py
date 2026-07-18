"""K GameSense — read the game's own screen to understand what happened.

Games *narrate themselves on the HUD*: kill feeds, medals, "DOUBLE KILL",
"WASTED", "VICTORY", "GOAL!", "MISSION PASSED", timers, killcam banners. That
text is the most reliable ground truth available about the gameplay — far more
reliable than motion energy, which cannot tell a multikill from the player
dying. GameSense OCRs the whole frame (not game-specific regions — users
upload *different games*), classifies what it reads against a multi-game,
multi-language vocabulary, and also flags *novel center-screen announcements*
generically, so a game whose words we don't know still registers as "the game
announced something big".

The events carry precise timestamps and screen regions so they serve both
selection (rank the multikill, demote the death — this phase) and editing
(slow-mo exactly on the medal, shake on the hit — the K Motion layer).

Deterministic pipeline, honest split: OCR *describes* the screen; the
keyword classifier *labels*; the Planner's scorer *decides*. Degrades
gracefully to no events when tesseract/pytesseract are unavailable.
"""

from .events import GameEvent, collapse_events
from .keywords import classify_text
from .hud import read_screen_events
from .score import announcer_events, viral_adjustment

__all__ = ["GameEvent", "collapse_events", "classify_text",
           "read_screen_events", "announcer_events", "viral_adjustment"]

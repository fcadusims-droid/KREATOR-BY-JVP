"""Infer the *kind* of gameplay from VLM scene descriptions, and pick a preset.

The VLM tells us what's on screen ("a bank vault door", "chased by police",
"driving a vehicle"). Aggregating those descriptions is enough to recognize the
genre — GTA-style heist/open-world crime, a shooter, racing, sports — without
any label from the user. From the genre, the Director picks editing defaults.

One preset choice is grounded in real audience feedback, not a guess: the only
genuine *editing* comment found while mining YouTube comments on no-commentary
GTA gameplay was **"You cut the video a lot, I don't know how the missions go"**
— so mission/heist content keeps *more* and preserves dialogue, rather than
being cut into a punchy montage.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# Genre signals — counted across all scene descriptions.
_GENRE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "heist_mission": ("vault", "keycard", "keypad", "loot", "buyer", "heist",
                      "hostage", "briefing", "map", "fingerprint", "objective",
                      "team", "mission", "safe", "security"),
    "combat": ("shoot", "gun", "fire", "weapon", "police", "chase", "fight",
               "explos", "soldier", "military", "battle", "enemy"),
    "driving": ("driving", "vehicle", "car", "truck", "bus", "road", "highway",
                "street", "motorcycle", "traffic", "garage"),
    "sports": ("ball", "goal", "field", "match", "stadium", "pitch", "race track",
               "lap", "referee", "player kicks"),
    "urban": ("city", "casino", "store", "building", "downtown", "mall",
              "parking", "hallway", "room"),
    "talking": ("person talking", "man speaking", "woman speaking",
                "person sitting", "microphone", "webcam", "podcast",
                "person in front of", "talking to the camera",
                "close-up of a face", "interview"),
}


@dataclass(frozen=True)
class ContentProfile:
    genre: str                     # e.g. "gta_heist", "shooter", "racing", "generic_gameplay"
    label: str                     # human-readable
    tags: list[str] = field(default_factory=list)   # detected signal buckets
    preset: str = "balanced"       # key into EDITING_PRESETS

    def to_dict(self) -> dict[str, object]:
        return {"genre": self.genre, "label": self.label,
                "tags": self.tags, "preset": self.preset}


# Editing presets the Director can choose. Params map onto Condenser + DSL.
# ``music`` is the mood the Director asks the K Library for (None = no bed).
# Mission keeps no music so briefings stay clear (the "I can't follow the
# mission" feedback); action/punchy montages get a bed if the library has one.
EDITING_PRESETS: dict[str, dict] = {
    # Keep more, preserve dialogue — grounded in the "you cut too much, can't
    # follow the mission" feedback. Don't montage a heist; no flashy zooms.
    "mission": {"target_keep": 0.55, "keep_dialogue": True, "min_cut": 5.0,
                "zoom": False, "music": None,
                "note": "keeps more and preserves briefings so the mission still reads"},
    # Open-world action: balanced condense, keep action coherent, punch in on peaks.
    "action": {"target_keep": 0.40, "keep_dialogue": True, "min_cut": 4.0,
               "zoom": True, "music": "action",
               "note": "balanced — keeps the action, trims the travel, punches in on peaks"},
    # Punchy: mostly combat, tighten hard, zoom on the action.
    "punchy": {"target_keep": 0.30, "keep_dialogue": False, "min_cut": 3.0,
               "zoom": True, "music": "intense",
               "note": "tight, action-forward cut with punch-ins"},
    "balanced": {"target_keep": 0.40, "keep_dialogue": True, "min_cut": 4.0,
                 "zoom": True, "music": "upbeat",
                 "note": "sensible default"},
    # Talking content (vlog/podcast/class): the edit is speech-driven — keep
    # what was said, cut the dead air. target_keep is nominal; the plan comes
    # from pause_cut_plan over the transcript, never cutting mid-sentence.
    "talking": {"target_keep": 0.85, "keep_dialogue": True, "min_cut": 0.8,
                "zoom": False, "music": None,
                "note": "keeps the speech, cuts pauses and dead air"},
}


def detect_content(
    descriptions: list[str], speech_ratio: float | None = None
) -> ContentProfile:
    """Infer genre + preset from VLM scene descriptions.

    ``speech_ratio`` (spoken time / duration, when a transcript exists) lets
    the Director recognize *talking* content — a vlog or podcast is defined by
    someone talking most of the time, which descriptions alone can miss.
    """
    text = " ".join(descriptions).lower()
    scores = {
        genre: sum(text.count(kw) for kw in kws)
        for genre, kws in _GENRE_KEYWORDS.items()
    }
    tags = [g for g, s in scores.items() if s > 0]

    heist = scores["heist_mission"]
    combat = scores["combat"]
    driving = scores["driving"]
    sports = scores["sports"]

    # Talking content: mostly speech, or clear talking-head visuals with
    # meaningful speech coverage and no stronger game signal.
    game_signal = heist + combat + driving + sports
    if speech_ratio is not None and (
        speech_ratio >= 0.7
        or (speech_ratio >= 0.45 and scores["talking"] >= 1 and game_signal == 0)
    ):
        return ContentProfile("talking", "Talking / vlog content",
                              tags, preset="talking")

    # GTA-style heist/mission: heist cues present, alongside city + driving.
    if heist >= 2 and (scores["urban"] or driving):
        return ContentProfile("gta_heist", "GTA-style heist / mission",
                              tags, preset="mission")
    if sports >= 2 and sports >= combat:
        return ContentProfile("sports", "Sports gameplay", tags, preset="balanced")
    if combat >= 3 and combat >= driving:
        return ContentProfile("shooter", "Combat / shooter gameplay",
                              tags, preset="punchy")
    if driving >= 3 and driving >= combat:
        return ContentProfile("driving", "Driving / open-world gameplay",
                              tags, preset="action")
    if combat or driving or heist:
        return ContentProfile("action_gameplay", "Action gameplay",
                              tags, preset="action")
    return ContentProfile("generic_gameplay", "Gameplay", tags, preset="balanced")

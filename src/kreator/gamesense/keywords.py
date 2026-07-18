"""Multi-game, multi-language HUD vocabulary → event kinds. Pure.

Organized by *what it means for the edit*, not by game: a "DOUBLE KILL"
medal (CoD), a "GOAL!" banner (FIFA), and "MISSION PASSED" (GTA) are all
peak moments; "WASTED", "YOU DIED", and "Killed by" are all the player
failing. Games ship localized, so common pt/es strings sit next to the
English ones. Matching is case-insensitive substring over OCR output —
which is noisy, so phrases are chosen to be distinctive.
"""

from __future__ import annotations

# Peak feats — the moment worth clipping.
MULTIKILL = (
    "double kill", "triple kill", "quad kill", "multikill", "multi kill",
    "mega kill", "ultra kill", "monster kill", "rampage", "killing spree",
    "kill chain", "killstreak", "kill streak", "collateral", "unstoppable",
    "merciless", "relentless", "brutal", "nuclear", "godlike", "dominating",
    "ace", "team wipe", "squad wipe", "penta kill", "quadra kill",
    "bizarro", "imparavel",  # pt localizations commonly seen
)

KILL = (
    "enemy down", "kill confirmed", "target down", "hostile down",
    "you killed", "eliminated", "eliminou", "knocked", "knockdown",
    "headshot", "finished", "abatido", "derrubado", "baixa confirmada",
)

# The player failing — the opposite of a highlight.
DEATH = (
    "killed by", "you were eliminated", "you died", "eliminated by",
    "wasted", "mission failed", "game over", "respawn", "spectating",
    "killcam", "death cam", "voce morreu", "você morreu", "eliminado por",
    "morto por", "missao falhou", "missão falhou", "has fallen",
)

# Round/match outcomes and objectives — context peaks.
VICTORY = (
    "victory", "match won", "round won", "you win", "winner",
    "play of the game", "mvp", "champion", "vitoria", "vitória",
    "mission passed", "missao concluida", "missão concluída", "rank up",
    "level up", "new record", "personal best", "first place",
)

OBJECTIVE = (
    "objective captured", "flag captured", "point captured", "captured",
    "bomb planted", "bomb defused", "defusing", "hardpoint", "goal",
    "touchdown", "checkpoint", "final lap", "last lap", "overtime",
    "gol", "objetivo", "capturado", "plantada", "ultima volta", "última volta",
)

_VOCAB: dict[str, tuple[str, ...]] = {
    "multikill": MULTIKILL,
    "death": DEATH,          # before "kill": "killed by" must not read as a kill
    "kill": KILL,
    "victory": VICTORY,
    "objective": OBJECTIVE,
}


def classify_text(text: str) -> list[str]:
    """Event kinds present in a piece of screen/announcer text, in priority
    order. Death phrases are checked before kill phrases so "killed by"
    never registers as the player getting a kill."""
    t = " ".join(text.lower().split())
    if not t:
        return []
    found: list[str] = []
    for kind, phrases in _VOCAB.items():
        if any(p in t for p in phrases):
            found.append(kind)
    # "killed by" style hits match both DEATH and KILL vocab; death wins.
    if "death" in found and "kill" in found:
        found.remove("kill")
    return found

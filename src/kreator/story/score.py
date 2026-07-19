"""Score one spoken segment for clippability. Pure, deterministic, en+pt.

The cues are what make a line worth clipping, weighted by how strongly they
predict a human would pull it. Prosody (was it said *loudly/excitedly*) is
passed in from the audio, since delivery matters as much as words.
"""

from __future__ import annotations

import re

# A promise of payoff — the opener that makes someone keep watching.
HOOK = (
    "the secret", "here's why", "here is why", "the truth", "nobody tells you",
    "what nobody", "the reason", "this is how", "here's how", "here is how",
    "the best", "the worst", "the biggest", "you won't believe", "watch this",
    "let me tell you", "the trick", "the problem with", "never do", "always do",
    "o segredo", "a verdade", "ninguém te conta", "por isso que", "o motivo",
    "é assim que", "o melhor", "o pior", "o maior", "presta atenção",
    "deixa eu te contar", "o truque", "nunca faça", "sempre faça",
)

# Emotional / superlative emphasis — the peaks people remember.
EMPHASIS = (
    "amazing", "incredible", "insane", "crazy", "unbelievable", "shocking",
    "hilarious", "terrifying", "perfect", "love", "hate", "wow", "oh my",
    "the most", "literally", "actually", "honestly", "i can't believe",
    "incrível", "inacreditável", "absurdo", "surreal", "perfeito", "impossível",
    "chocante", "hilário", "nossa", "meu deus", "sério", "de verdade",
)

# First-person story markers — vlog/story gold (a personal beat, not filler).
STORY = (
    " i ", " i'm", " i've", " my ", " we ", " me ", " you ",
    " eu ", " meu ", " minha ", " a gente ", " você ", " voce ",
)

# Laughter, as it lands in a transcript.
LAUGH = ("haha", "hahaha", "lol", "lmao", "[laugh", "(laugh", "kkk", "rs ")

_QUESTION_WORDS = ("what", "why", "how", "who", "when", "where", "which",
                   "o que", "por que", "porque", "como", "quem", "quando",
                   "onde", "qual", "será que")


def _count(text: str, phrases) -> int:
    return sum(text.count(p) for p in phrases)


def is_question(text: str) -> bool:
    t = text.strip().lower()
    return t.endswith("?") or any(t.startswith(w + " ") for w in _QUESTION_WORDS)


def score_segment(text: str, *, audio_emphasis: float = 0.0) -> tuple[float, list[str]]:
    """(clippability score, reasons) for one transcript segment.

    ``audio_emphasis`` is 0..1, how loud/energetic the delivery was (peak
    audio over the segment) — a line shouted lands harder than one mumbled.
    """
    padded = " " + " ".join(text.lower().split()) + " "
    reasons: list[str] = []
    score = 0.0

    hook = _count(padded, HOOK)
    if hook:
        score += min(hook, 2) * 0.35
        reasons.append("a hook line")
    if is_question(text):
        score += 0.25
        reasons.append("a question to the viewer")
    emph = _count(padded, EMPHASIS)
    if emph:
        score += min(emph, 3) * 0.15
        reasons.append("emotional emphasis")
    if _count(padded, LAUGH):
        score += 0.30
        reasons.append("laughter")
    story = _count(padded, STORY)
    if story:
        score += min(story, 4) * 0.05
        reasons.append("a personal/story beat")
    if audio_emphasis >= 0.6:
        score += (audio_emphasis - 0.6) * 0.75
        reasons.append("delivered with energy")

    # A self-contained sentence (has some length and ends cleanly) clips better
    # than a dangling fragment.
    words = len(re.findall(r"\w+", text))
    if words >= 6 and text.strip().endswith((".", "!", "?")):
        score += 0.1

    return score, reasons

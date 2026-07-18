"""Conversational mode: a natural-language request → a JobRequest.

The model never edits — and here, no model even *parses*: a deterministic
keyword grammar (Portuguese + English) reads the creator's sentence and fills
in the same form the guided UI exposes. Anything it doesn't recognize simply
keeps its default, and everything it *did* understand is recorded in
``notes`` so the creator can see how the sentence was read. Offline, CPU,
testable. (An optional local LLM can layer on later; this is the floor that
always works.)
"""

from __future__ import annotations

import re

from .job import JobRequest

_NUMBER_WORDS = {
    "um": 1, "uma": 1, "one": 1, "a": 1,
    "dois": 2, "duas": 2, "two": 2,
    "tres": 3, "três": 3, "three": 3,
    "quatro": 4, "four": 4,
    "cinco": 5, "five": 5,
    "seis": 6, "six": 6,
    "sete": 7, "seven": 7,
    "oito": 8, "eight": 8,
    "nove": 9, "nine": 9,
    "dez": 10, "ten": 10,
}

# Spoken/caption language the user can name, mapped to Whisper ISO codes.
_LANGUAGES = {
    "pt": ("portugues", "português", "portuguese"),
    "en": ("ingles", "inglês", "english"),
    "es": ("espanhol", "español", "spanish"),
    "fr": ("frances", "francês", "french"),
    "de": ("alemao", "alemão", "german"),
    "it": ("italiano", "italian"),
    "ja": ("japones", "japonês", "japanese"),
    "ko": ("coreano", "korean"),
}

_LONG_EDIT_CUES = (
    "highlight", "melhores momentos", "resumo", "corte completo", "full edit",
    "video completo", "vídeo completo", "long edit", "edita o video",
    "edita o vídeo", "edit the video", "condensa", "condense",
)


def _find_count(text: str, after: str = "") -> int | None:
    """A number (digit or word) appearing right before ``short(s)``."""
    m = re.search(r"(\d+|" + "|".join(_NUMBER_WORDS) + r")\s+shorts?\b", text)
    if not m:
        return None
    token = m.group(1)
    return int(token) if token.isdigit() else _NUMBER_WORDS[token]


def parse_instruction(text: str) -> JobRequest:
    """Read a creator's sentence into a JobRequest (defaults where silent).

    Examples it understands (en/pt):
      "make 5 shorts of ~30 seconds with animated captions, no music"
      "turn this into a vertical Short with karaoke captions"
      "faz 3 shorts de ~30 segundos com legenda animada, sem música"
    """
    t = " " + text.lower().strip() + " "
    req = JobRequest()
    notes: list[str] = []

    # How many Shorts?
    count = _find_count(t)
    if count is not None:
        req.shorts = count
        notes.append(f"{count} Short(s) requested")
    elif re.search(r"\bshorts?\b", t):
        req.shorts = 1
        notes.append("a Short requested (no count given → 1)")

    # Short length: "~30 segundos", "30s", "30-second".
    m = re.search(r"~?\s*(\d+)\s*(?:-?\s*(?:s\b|seg\b|segundos?|seconds?|sec\b))",
                  t)
    if m:
        secs = float(m.group(1))
        req.max_short_len = secs
        req.min_short_len = min(req.min_short_len, max(5.0, secs * 0.5))
        notes.append(f"Short length target ≈{int(secs)}s")

    # The long edit: produced only when asked for alongside Shorts.
    wants_long = any(cue in t for cue in _LONG_EDIT_CUES)
    if req.shorts and not wants_long:
        req.long_edit = False
        notes.append("only Shorts (no full edit mentioned)")
    elif wants_long:
        req.long_edit = True
        notes.append("full condensed edit requested")

    # Aspect for the long edit ("vertical", "9:16").
    if req.long_edit and ("vertical" in t or "9:16" in t):
        req.aspect = "9:16"
        notes.append("long edit vertical (9:16)")

    # Captions.
    if re.search(r"sem legendas?|no captions?|no subtitles?", t):
        req.captions = "none"
        notes.append("no captions")
    elif re.search(r"legendas? animadas?|animated (?:captions?|subtitles?)|"
                   r"karaoke|word.?by.?word|palavra por palavra", t):
        req.captions = "karaoke"
        notes.append("animated karaoke captions")
    elif re.search(r"legendas?|captions?|subtitles?", t):
        req.captions = "plain"
        notes.append("plain captions")

    # Spoken/caption language ("legendas em espanhol", "captions in english").
    for code, names in _LANGUAGES.items():
        if any(f" {n} " in t or f" {n}," in t or f" {n}." in t for n in names):
            req.language = code
            notes.append(f"language: {code}")
            break

    # Thumbnails ("3 thumbnails", "sem thumbnail", "with a thumbnail").
    if re.search(r"sem (?:thumb|thumbnail|capa)|no thumbnails?", t):
        req.thumbnails = 0
        notes.append("no thumbnails")
    else:
        m = re.search(r"(\d+)\s*(?:thumbs?|thumbnails?|capas?)", t)
        if m:
            req.thumbnails = int(m.group(1))
            notes.append(f"{req.thumbnails} thumbnail candidate(s)")

    # Music.
    if re.search(r"sem m[úu]sica|no music", t):
        req.music = False
        notes.append("no music bed")

    # Editing style (K Motion preset).
    if re.search(r"cinematogr[aá]fic|cinematic", t):
        req.style = "cinematic"
        notes.append("cinematic style")
    elif re.search(r"montage|montagem|ediç[aã]o pesada|heavy edit", t):
        req.style = "montage"
        notes.append("aggressive montage style")
    elif re.search(r"sem efeitos|no effects|\braw\b|\bclean\b", t):
        req.style = "clean"
        notes.append("clean style (color only)")

    # Cut intensity.
    if re.search(r"\bleve\b|\bsuave\b|\blight\b|keep more", t):
        req.intensity = "light"
        notes.append("light cut")
    elif re.search(r"agressiv|bem curto|\bheavy\b|\btight\b|\bpunchy\b", t):
        req.intensity = "heavy"
        notes.append("heavy cut")

    req.notes = notes
    return req

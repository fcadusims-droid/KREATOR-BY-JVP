"""The editing operations and the EditProgram that holds them.

Coordinate convention, stated once because it's the thing that goes wrong:
- ``Cut`` uses **source** timeline coordinates (spans of the original upload).
- every overlay operation (``Subtitle``, ``Zoom``, …) uses **edited** timeline
  coordinates (position in the final, cut-together video).

``timeline.py`` is what converts between the two.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Cut:
    """A source span to keep — the spine of the edit."""
    source_start: float
    source_end: float
    reason: str = ""   # why this span was kept (the justification)

    @property
    def duration(self) -> float:
        return self.source_end - self.source_start

    def to_dict(self) -> dict:
        return {"type": "cut", "source_start": round(self.source_start, 3),
                "source_end": round(self.source_end, 3), "reason": self.reason}


@dataclass(frozen=True)
class Subtitle:
    """A caption on the edited timeline (from the creator's own spoken words)."""
    start: float
    end: float
    text: str
    reason: str = ""

    def to_dict(self) -> dict:
        return {"type": "subtitle", "start": round(self.start, 3),
                "end": round(self.end, 3), "text": self.text, "reason": self.reason}


@dataclass(frozen=True)
class Caption:
    """A karaoke caption on the edited timeline: the creator's own words, each
    timed, so the burned subtitle highlights word by word as it is spoken.
    ``words`` is ``((start, end, text), …)`` in edited time."""
    start: float
    end: float
    words: tuple[tuple[float, float, str], ...]
    reason: str = ""

    @property
    def text(self) -> str:
        return " ".join(w[2] for w in self.words)

    def to_dict(self) -> dict:
        return {"type": "caption", "start": round(self.start, 3),
                "end": round(self.end, 3),
                "words": [{"start": round(s, 3), "end": round(e, 3), "text": t}
                          for s, e, t in self.words],
                "reason": self.reason}


@dataclass(frozen=True)
class CaptionStyle:
    """How burned karaoke captions look — the seed of the Editing Profile's
    caption style. Colors are ASS ``&HAABBGGRR`` strings."""
    font: str = "Arial"
    size: int = 28                  # at 720-line PlayRes; libass scales with output
    primary: str = "&H0000E5FF"     # already-sung words (yellow-ish)
    upcoming: str = "&H00FFFFFF"    # not-yet-sung words (white)
    outline: str = "&H00000000"
    alignment: int = 2              # ASS numpad: 2 = bottom center, 5 = middle center
    margin_v: int = 44
    bold: bool = True

    def to_dict(self) -> dict:
        return {"font": self.font, "size": self.size, "primary": self.primary,
                "upcoming": self.upcoming, "outline": self.outline,
                "alignment": self.alignment, "margin_v": self.margin_v,
                "bold": self.bold}


@dataclass(frozen=True)
class Zoom:
    """A punch-in over an edited-timeline range."""
    start: float
    end: float
    scale: float = 1.15

    def to_dict(self) -> dict:
        return {"type": "zoom", "start": round(self.start, 3),
                "end": round(self.end, 3), "scale": self.scale}


@dataclass(frozen=True)
class Transition:
    """A transition at an edited-timeline instant."""
    at: float
    kind: str = "crossfade"
    duration: float = 0.4

    def to_dict(self) -> dict:
        return {"type": "transition", "at": round(self.at, 3),
                "kind": self.kind, "duration": self.duration}


@dataclass(frozen=True)
class Music:
    """A background track — a real, free-to-use file from the K Library."""
    track: str
    start: float
    end: float
    volume: float = 0.25

    def to_dict(self) -> dict:
        return {"type": "music", "track": self.track, "start": round(self.start, 3),
                "end": round(self.end, 3), "volume": self.volume}


@dataclass(frozen=True)
class Reframe:
    """Reframe the whole edit to another aspect ratio (e.g. 9:16 Shorts).

    ``strategy`` is ``"crop"`` (select the window of real pixels that holds the
    action) or ``"pad"`` (fit the full frame, neutral bars around it). With
    ``crop``, ``focus_x`` gives one normalized horizontal center (0..1) per cut
    — aligned by index with ``EditProgram.cuts``; empty means center every cut.
    """
    aspect: str = "9:16"
    strategy: str = "crop"
    focus_x: tuple[float, ...] = ()
    reason: str = ""

    def to_dict(self) -> dict:
        return {"type": "reframe", "aspect": self.aspect,
                "strategy": self.strategy,
                "focus_x": [round(f, 3) for f in self.focus_x],
                "reason": self.reason}


@dataclass(frozen=True)
class Broll:
    """A licensed B-roll clip from the K Library (executor: future)."""
    query: str
    start: float
    duration: float

    def to_dict(self) -> dict:
        return {"type": "broll", "query": self.query,
                "start": round(self.start, 3), "duration": self.duration}


@dataclass
class EditProgram:
    """A full edit as data: the cut spine plus overlay operations.

    This is the *intermediate representation* the Director produces and the
    executor consumes — timeline + operations + justifications. The AI never
    edits; it plans this, and the deterministic executor runs it.
    """
    cuts: list[Cut] = field(default_factory=list)
    subtitles: list[Subtitle] = field(default_factory=list)
    captions: list[Caption] = field(default_factory=list)   # karaoke (word-level)
    caption_style: CaptionStyle | None = None
    zooms: list[Zoom] = field(default_factory=list)
    transitions: list[Transition] = field(default_factory=list)
    music: list[Music] = field(default_factory=list)
    broll: list[Broll] = field(default_factory=list)
    reframe: Reframe | None = None
    height: int | None = None
    # High-level editorial decisions, in plain language — the "why" behind the
    # plan (e.g. "recognized GTA heist → mission preset → kept more").
    rationale: list[str] = field(default_factory=list)

    @property
    def edited_duration(self) -> float:
        return sum(c.duration for c in self.cuts)

    def to_dict(self) -> dict:
        return {
            "height": self.height,
            "edited_duration": round(self.edited_duration, 2),
            "rationale": self.rationale,
            "operations": (
                [c.to_dict() for c in self.cuts]
                + [s.to_dict() for s in self.subtitles]
                + [c.to_dict() for c in self.captions]
                + [z.to_dict() for z in self.zooms]
                + [t.to_dict() for t in self.transitions]
                + [m.to_dict() for m in self.music]
                + [b.to_dict() for b in self.broll]
                + ([self.reframe.to_dict()] if self.reframe else [])
            ),
        }

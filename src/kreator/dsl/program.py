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

    @property
    def duration(self) -> float:
        return self.source_end - self.source_start

    def to_dict(self) -> dict:
        return {"type": "cut", "source_start": round(self.source_start, 3),
                "source_end": round(self.source_end, 3)}


@dataclass(frozen=True)
class Subtitle:
    """A caption on the edited timeline (from the creator's own spoken words)."""
    start: float
    end: float
    text: str

    def to_dict(self) -> dict:
        return {"type": "subtitle", "start": round(self.start, 3),
                "end": round(self.end, 3), "text": self.text}


@dataclass(frozen=True)
class Zoom:
    """A punch-in over an edited-timeline range (executor: future)."""
    start: float
    end: float
    scale: float = 1.15

    def to_dict(self) -> dict:
        return {"type": "zoom", "start": round(self.start, 3),
                "end": round(self.end, 3), "scale": self.scale}


@dataclass(frozen=True)
class Transition:
    """A transition at an edited-timeline instant (executor: future)."""
    at: float
    kind: str = "crossfade"
    duration: float = 0.4

    def to_dict(self) -> dict:
        return {"type": "transition", "at": round(self.at, 3),
                "kind": self.kind, "duration": self.duration}


@dataclass(frozen=True)
class Music:
    """Background track from the K Library (needs the asset library — future)."""
    track: str
    start: float
    end: float
    volume: float = 0.25

    def to_dict(self) -> dict:
        return {"type": "music", "track": self.track, "start": round(self.start, 3),
                "end": round(self.end, 3), "volume": self.volume}


@dataclass(frozen=True)
class Broll:
    """A licensed B-roll clip from the K Library (needs the library — future)."""
    query: str
    start: float
    duration: float

    def to_dict(self) -> dict:
        return {"type": "broll", "query": self.query,
                "start": round(self.start, 3), "duration": self.duration}


@dataclass
class EditProgram:
    """A full edit as data: the cut spine plus overlay operations."""
    cuts: list[Cut] = field(default_factory=list)
    subtitles: list[Subtitle] = field(default_factory=list)
    zooms: list[Zoom] = field(default_factory=list)
    transitions: list[Transition] = field(default_factory=list)
    music: list[Music] = field(default_factory=list)
    broll: list[Broll] = field(default_factory=list)
    height: int | None = None

    @property
    def edited_duration(self) -> float:
        return sum(c.duration for c in self.cuts)

    def to_dict(self) -> dict:
        return {
            "height": self.height,
            "edited_duration": round(self.edited_duration, 2),
            "operations": (
                [c.to_dict() for c in self.cuts]
                + [s.to_dict() for s in self.subtitles]
                + [z.to_dict() for z in self.zooms]
                + [t.to_dict() for t in self.transitions]
                + [m.to_dict() for m in self.music]
                + [b.to_dict() for b in self.broll]
            ),
        }

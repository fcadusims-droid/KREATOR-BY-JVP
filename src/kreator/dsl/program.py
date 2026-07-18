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
    """A source span to keep — the spine of the edit.

    ``speed`` is the playback rate: 1.0 plays as filmed, 0.5 is half-speed
    slow motion (the K Motion planner splits a cut so the slow-mo lands
    exactly on the event). Audio is tempo-matched by the executor.
    """
    source_start: float
    source_end: float
    reason: str = ""   # why this span was kept (the justification)
    speed: float = 1.0

    @property
    def duration(self) -> float:
        """Source-time length of the span."""
        return self.source_end - self.source_start

    @property
    def edited_duration(self) -> float:
        """How long this cut lasts in the edited video (speed applied)."""
        return self.duration / self.speed

    def to_dict(self) -> dict:
        d = {"type": "cut", "source_start": round(self.source_start, 3),
             "source_end": round(self.source_end, 3), "reason": self.reason}
        if self.speed != 1.0:
            d["speed"] = self.speed
        return d


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
class PunchZoom:
    """A zoom *pulse* centered at an edited-time instant — snaps in and eases
    out, the CapCut-style hit emphasis. ``amount`` is the peak extra zoom
    (0.22 = 22%); ``width`` is roughly how many seconds the pulse breathes."""
    at: float
    amount: float = 0.22
    width: float = 0.5
    reason: str = ""

    def to_dict(self) -> dict:
        return {"type": "punch_zoom", "at": round(self.at, 3),
                "amount": self.amount, "width": self.width,
                "reason": self.reason}


@dataclass(frozen=True)
class Shake:
    """A camera-shake window on the edited timeline — impact emphasis. The
    frame is slightly upscaled and the crop window jitters inside it, so
    every pixel shown is still real footage."""
    start: float
    end: float
    amplitude: float = 10.0    # max jitter in output pixels
    reason: str = ""

    def to_dict(self) -> dict:
        return {"type": "shake", "start": round(self.start, 3),
                "end": round(self.end, 3), "amplitude": self.amplitude,
                "reason": self.reason}


@dataclass(frozen=True)
class Grade:
    """A whole-video color treatment by named preset — deterministic
    eq/colorbalance chains, the programmatic equivalent of a LUT."""
    preset: str = "vivid"      # vivid | cinematic | punchy

    def to_dict(self) -> dict:
        return {"type": "grade", "preset": self.preset}


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
class Sfx:
    """A short sound effect — a real, free-to-use K Library file — mixed in
    at an edited-timeline instant, under the main audio."""
    at: float
    sound: str                      # path to the library audio file
    volume: float = 0.8
    reason: str = ""

    def to_dict(self) -> dict:
        return {"type": "sfx", "at": round(self.at, 3), "sound": self.sound,
                "volume": self.volume, "reason": self.reason}


@dataclass(frozen=True)
class Broll:
    """A licensed B-roll cutaway from the K Library: its video overlays the
    edit for ``[start, start+duration)`` (edited time) while the main audio
    keeps playing. ``path`` is the real library file."""
    path: str
    start: float
    duration: float
    reason: str = ""

    def to_dict(self) -> dict:
        return {"type": "broll", "path": self.path,
                "start": round(self.start, 3), "duration": self.duration,
                "reason": self.reason}


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
    punch_zooms: list[PunchZoom] = field(default_factory=list)
    shakes: list[Shake] = field(default_factory=list)
    grade: Grade | None = None
    transitions: list[Transition] = field(default_factory=list)
    music: list[Music] = field(default_factory=list)
    sfx: list[Sfx] = field(default_factory=list)
    broll: list[Broll] = field(default_factory=list)
    reframe: Reframe | None = None
    height: int | None = None
    # High-level editorial decisions, in plain language — the "why" behind the
    # plan (e.g. "recognized GTA heist → mission preset → kept more").
    rationale: list[str] = field(default_factory=list)

    @property
    def edited_duration(self) -> float:
        return sum(c.edited_duration for c in self.cuts)

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
                + [p.to_dict() for p in self.punch_zooms]
                + [s.to_dict() for s in self.shakes]
                + ([self.grade.to_dict()] if self.grade else [])
                + [t.to_dict() for t in self.transitions]
                + [m.to_dict() for m in self.music]
                + [s.to_dict() for s in self.sfx]
                + [b.to_dict() for b in self.broll]
                + ([self.reframe.to_dict()] if self.reframe else [])
            ),
        }

"""Shared, dependency-free domain types for the E1 slice.

These are deliberately plain dataclasses with no third-party imports, so the
Planner — the heart of E1 — can be constructed and unit-tested with fixed
inputs, no video and no models. That is the runtime spec's E4-RT: "given an
evidence set, does the produced plan match a human editor's decision?"
"""

from __future__ import annotations

from dataclasses import dataclass, field


def format_tc(seconds: float) -> str:
    """Render a timecode as HH:MM:SS for human-readable rationale."""
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


@dataclass(frozen=True)
class Timespan:
    """A half-open interval [start, end) on the video timeline, in seconds."""

    start: float
    end: float

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError(f"end ({self.end}) precedes start ({self.start})")

    @property
    def duration(self) -> float:
        return self.end - self.start

    @property
    def center(self) -> float:
        return (self.start + self.end) / 2.0

    def overlaps(self, other: "Timespan") -> bool:
        return self.start < other.end and other.start < self.end

    def intersection(self, other: "Timespan") -> float:
        """Seconds of overlap with another span (0 if disjoint)."""
        return max(0.0, min(self.end, other.end) - max(self.start, other.start))

    def clamp(self, lo: float, hi: float) -> "Timespan":
        start = min(max(self.start, lo), hi)
        end = min(max(self.end, lo), hi)
        return Timespan(start, end)

    def __str__(self) -> str:
        return f"[{format_tc(self.start)}–{format_tc(self.end)}]"


@dataclass(frozen=True)
class Event:
    """A deterministic point-in-time observation from the Signal Layer.

    Events are *triggers*: an instant the raw signals flagged as potentially
    interesting (a loud moment, a motion spike, a scene cut). They carry no
    semantic meaning yet — that is added later, as evidence.
    """

    time: float
    kind: str  # "audio_peak" | "motion_peak" | "scene_cut" | ...
    strength: float  # normalized 0..1; scene cuts use 1.0

    def __str__(self) -> str:
        return f"{self.kind}@{format_tc(self.time)}({self.strength:.2f})"


@dataclass
class SignalBundle:
    """The Signal Layer's output: time series + discrete trigger events.

    Deterministic by construction — the same input bits always produce the
    same bundle. Everything downstream consumes this instead of the raw video.
    """

    duration: float
    fps: float
    # Discrete triggers, each an ``Event``.
    events: list[Event] = field(default_factory=list)
    # Dense per-window series, aligned to ``times`` (seconds). Optional; the
    # Planner can score from events alone when a series is absent.
    times: list[float] = field(default_factory=list)
    motion: list[float] = field(default_factory=list)  # optical-flow magnitude 0..1
    audio: list[float] = field(default_factory=list)  # audio energy 0..1
    speech: list[float] = field(default_factory=list)  # voice activity 0/1 or 0..1
    scene_cuts: list[float] = field(default_factory=list)  # times of scene boundaries

    def events_of(self, kind: str) -> list[Event]:
        return [e for e in self.events if e.kind == kind]

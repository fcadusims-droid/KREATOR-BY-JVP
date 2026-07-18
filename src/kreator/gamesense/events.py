"""GameEvent — one thing the screen (or announcer) said, timed and placed."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GameEvent:
    time: float
    kind: str          # multikill | kill | death | victory | objective | announcement
    source: str        # "hud" | "announcer"
    text: str          # what was actually read
    region: str = ""   # coarse screen position, e.g. "center", "top-left"

    def to_dict(self) -> dict:
        return {"time": round(self.time, 2), "kind": self.kind,
                "source": self.source, "text": self.text, "region": self.region}


def collapse_events(events: list[GameEvent], *, window: float = 2.5) -> list[GameEvent]:
    """Merge repeats: the same kind read again within ``window`` seconds is the
    same on-screen banner persisting across samples, not a new event."""
    out: list[GameEvent] = []
    last_at: dict[str, float] = {}
    for ev in sorted(events, key=lambda e: (e.time, e.kind)):
        prev = last_at.get(ev.kind)
        if prev is not None and ev.time - prev < window:
            last_at[ev.kind] = ev.time
            continue
        last_at[ev.kind] = ev.time
        out.append(ev)
    return out

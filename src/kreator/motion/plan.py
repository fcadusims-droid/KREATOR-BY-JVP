"""Plan the effects for one clip: events in, operations out. Pure.

The planner takes the clip's source span, the GameSense events inside it, and
a style preset, and produces the K Motion operations: a cut spine whose speed
changes exactly around the peak event (slow-mo on the kill), zoom pulses on
every celebrated instant, a shake window on the hardest impact, and a grade.
Deterministic given (span, events, style) — the same clip always edits the
same way.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..dsl import Cut, Grade, PunchZoom, Shake

# Which events deserve which emphasis.
_SLOWMO_KINDS = ("multikill", "kill")          # the feat plays at half speed
_PULSE_KINDS = ("multikill", "kill", "victory", "objective", "announcement")
_SHAKE_KINDS = ("multikill",)                   # only the hardest hit shakes

# Style presets — the package of effects a clip gets. The Director picks one
# from the recognized content; the creator can override.
STYLES: dict[str, dict] = {
    # Aggressive FPS montage: slow-mo the feat, pulse every celebration,
    # shake the multikill, punchy color.
    "montage": {"slowmo": 0.5, "slowmo_pre": 0.7, "slowmo_post": 1.1,
                "pulse": 0.22, "shake": 10.0, "grade": "punchy"},
    # Cinematic: slow-mo and a filmic grade, no shake, subtle pulses.
    "cinematic": {"slowmo": 0.5, "slowmo_pre": 0.8, "slowmo_post": 1.2,
                  "pulse": 0.12, "shake": None, "grade": "cinematic"},
    # Clean: color only — the footage speaks for itself.
    "clean": {"slowmo": None, "slowmo_pre": 0, "slowmo_post": 0,
              "pulse": None, "shake": None, "grade": "vivid"},
    # Raw: no effects at all (the pre-Motion behavior).
    "none": {"slowmo": None, "slowmo_pre": 0, "slowmo_post": 0,
             "pulse": None, "shake": None, "grade": None},
}


@dataclass
class MotionPlan:
    """The planned operations for one clip, in edited-time coordinates."""
    cuts: list[Cut] = field(default_factory=list)
    punch_zooms: list[PunchZoom] = field(default_factory=list)
    shakes: list[Shake] = field(default_factory=list)
    grade: Grade | None = None
    rationale: list[str] = field(default_factory=list)


def _edited_time(source_t: float, cuts: list[Cut]) -> float | None:
    from ..dsl import source_to_edited

    return source_to_edited(source_t, cuts)


def plan_motion(
    span,
    events: list,
    *,
    style: str = "montage",
    beats: list[float] | None = None,
) -> MotionPlan:
    """Build the motion plan for a single-cut clip over source ``span``.

    ``events`` are GameSense events (source time) inside the span. The
    strongest slow-mo-worthy event splits the spine into pre/slow/post cuts
    with the slow half-speed section bracketing the event; every celebrated
    instant gets a zoom pulse (snapped to ``beats`` when given); a multikill
    also gets a shake. Unknown style falls back to "none".
    """
    st = STYLES.get(style, STYLES["none"])
    plan = MotionPlan(grade=Grade(st["grade"]) if st["grade"] else None)
    if st["grade"]:
        plan.rationale.append(f"'{st['grade']}' color grade ({style} style)")

    events = sorted((e for e in events if span.start <= e.time <= span.end),
                    key=lambda e: e.time)

    # --- the cut spine, split around the headline event for slow-mo ---
    headline = next((e for e in events if e.kind in _SLOWMO_KINDS), None)
    if st["slowmo"] and headline is not None:
        pre = max(span.start, headline.time - st["slowmo_pre"])
        post = min(span.end, headline.time + st["slowmo_post"])
        cuts = []
        if pre > span.start:
            cuts.append(Cut(span.start, pre, reason="build-up"))
        cuts.append(Cut(pre, post, reason=f"{headline.kind} in slow motion",
                        speed=st["slowmo"]))
        if post < span.end:
            cuts.append(Cut(post, span.end, reason="aftermath"))
        plan.cuts = cuts
        plan.rationale.append(
            f"slow-mo ({st['slowmo']}×) on the {headline.kind} at "
            f"{headline.time - span.start:.1f}s into the clip")
    else:
        plan.cuts = [Cut(span.start, span.end, reason="ranked moment")]

    # --- zoom pulses on every celebrated instant ---
    if st["pulse"]:
        for e in events:
            if e.kind not in _PULSE_KINDS:
                continue
            at = _edited_time(min(e.time, span.end - 1e-3), plan.cuts)
            if at is None:
                continue
            at = _snap(at, beats)
            plan.punch_zooms.append(PunchZoom(
                at, amount=st["pulse"],
                reason=f"pulse on {e.kind}: {e.text[:40]}"))
        if plan.punch_zooms:
            plan.rationale.append(
                f"{len(plan.punch_zooms)} zoom pulse(s) on the game's own "
                "celebrated moments")

    # --- shake on the hardest hit ---
    if st["shake"]:
        for e in events:
            if e.kind in _SHAKE_KINDS:
                at = _edited_time(min(e.time, span.end - 1e-3), plan.cuts)
                if at is not None:
                    plan.shakes.append(Shake(at, at + 0.5,
                                             amplitude=st["shake"],
                                             reason=f"impact shake on {e.kind}"))
        if plan.shakes:
            plan.rationale.append("impact shake on the multikill")

    return plan


def _snap(t: float, beats: list[float] | None, tol: float = 0.35) -> float:
    """Move ``t`` to the nearest beat when one is close enough — effects that
    land on the music's beat read as intentional."""
    if not beats:
        return t
    nearest = min(beats, key=lambda b: abs(b - t))
    return nearest if abs(nearest - t) <= tol else t

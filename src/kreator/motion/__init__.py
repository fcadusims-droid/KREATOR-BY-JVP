"""K Motion — the heavy-editing layer: effects planned on real moments.

This is the "editor B" of the two-agent flow: the Clipper/Editor decide *what*
footage survives; K Motion decides *how it hits* — slow motion landing exactly
on the kill, a zoom pulse on the medal, camera shake on the impact, a color
grade over the whole piece, effect times snapped to the music's beat. Every
effect is a deterministic FFmpeg transform of real pixels (spec §4: nothing
generated), planned from the GameSense events' precise timestamps and executed
frame-accurately by the DSL runner.
"""

from .plan import STYLES, plan_motion
from .beats import beat_times, snap_to_beats

__all__ = ["STYLES", "plan_motion", "beat_times", "snap_to_beats"]

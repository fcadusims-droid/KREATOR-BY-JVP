"""K Reframe — deterministic aspect-ratio reframing (16:9 → 9:16 Shorts).

Turning a horizontal gameplay into a vertical Short is a *crop decision*, not a
generation problem: pick the window of real pixels that holds the action and
keep it steady. The focus comes from the same cheap signal the editor already
trusts — frame-difference motion — reduced to a horizontal center of mass per
kept segment. A pure geometry layer computes the crop; the DSL executor turns
it into an FFmpeg expression. No pixel is invented (see docs/not-generative.md):
``crop`` selects real pixels, ``pad`` adds neutral bars around them.
"""

from .geometry import center_of_mass, crop_window, parse_aspect
from .focus import cut_focus_centers

__all__ = ["parse_aspect", "crop_window", "center_of_mass", "cut_focus_centers"]

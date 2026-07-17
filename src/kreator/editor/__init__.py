"""K Editor — condense a long, unedited gameplay into its interesting parts.

Where K Clipper picks the top-N *moments* (for Shorts), K Editor works on the
*whole timeline*: it decides, second by second, what is worth keeping and what
is a boring stretch to cut, then renders a tighter video from the kept parts.

The hard question the product raises — "how does the system know what's boring
vs. interesting?" — is answered here at the signal level and stated honestly:

- **Interesting** = sustained visual action and/or loud audio (combat, chases,
  crashes, explosions). The Signal Layer already measures both.
- **Boring** = long stretches where little moves and little is heard (cruising
  in a straight line, standing in a menu, idle).

This is a *proxy*, not semantic understanding. It captures "action density,"
which for no-commentary gameplay correlates well with what a viewer stays for.
What it does **not** know by itself is *why* a quiet moment matters (a mission
briefing, a scenic pause, story dialogue). That is what the rescue signals add:
speech presence (``kreator.speech``) and VLM scene labels (``kreator.vlm``,
local and CPU-only — see ``docs/vlm-without-gpu.md``) lift the interest floor
via ``Condenser.plan(speech=…, visual_keep=…)`` so those stretches survive.
"""

from .interest import interest_curve
from .condenser import Condenser, EditPlan, KeepSegment
from .render import render_segments

__all__ = [
    "interest_curve",
    "Condenser",
    "EditPlan",
    "KeepSegment",
    "render_segments",
]

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
What it does **not** yet know is *why* something is interesting (a funny fail
that isn't loud, a clever play). That is what the VLM refinement adds — see
``kreator.editor.interest.semantic_boost`` and the backend hooks. The
signal-only condenser runs today on CPU; the VLM layer plugs in on a GPU box.
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

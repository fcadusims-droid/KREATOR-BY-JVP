"""K Shorts — turn K Clipper's ranked moments into finished vertical Shorts.

The Clipper ranks, the human (or the Director) picks how many — and this module
does the *editing*: each candidate span is fitted to a watchable Short length,
reframed to 9:16 with the crop following the action, captioned with the
creator's own words, rendered, and validated. Every Short carries the
candidate's rationale, so the "why this moment" survives into the deliverable.
"""

from .builder import ShortSpec, build_short_program, fit_span, make_shorts

__all__ = ["ShortSpec", "fit_span", "build_short_program", "make_shorts"]

"""Editing templates — the simple → cinematic dial as named doctrines.

A template bundles the knobs a creator would otherwise set one by one (cut
intensity, motion style, caption style, music) into one choice that spans the
range from a barely-touched trim to a full cinematic treatment. ``auto`` lets
the Director pick from the recognized content; any explicit field the creator
set still wins over the template, and the template wins over the Director's
auto-defaults. Deterministic, content-agnostic — the same names work for
gameplay, vlog, or documentary.
"""

from __future__ import annotations

# Each template sets a subset of JobRequest fields. Omitted fields are left for
# the Director to choose from the content. Ordered simplest → most produced.
TEMPLATES: dict[str, dict] = {
    "auto": {},   # the Director decides everything from the content
    # Barely touched: trim the dead weight, keep it honest, plain captions.
    "simple": {"style": "clean", "intensity": "light", "captions": "plain",
               "music": False},
    # Clean vlog: light energy, animated captions, keep the story.
    "vlog": {"style": "clean", "intensity": "light", "captions": "karaoke"},
    # Tutorial: keep every step, no effects or music in the way.
    "tutorial": {"style": "clean", "intensity": "light", "captions": "plain",
                 "music": False},
    # Cinematic: measured pace, Ken Burns + film grade, a music bed.
    "cinematic": {"style": "cinematic", "intensity": "medium",
                  "captions": "plain", "music": True},
    # Aggressive montage: tight cut, slow-mo/pulses/shake, karaoke captions.
    "montage": {"style": "montage", "intensity": "heavy", "captions": "karaoke",
                "music": True},
}


def apply_template(req, name: str) -> list[str]:
    """Fill ``req`` from template ``name`` where the creator left the default.

    Returns human-readable notes on what the template set. An explicit field
    (already changed from its default) is never overwritten — the creator's
    own choice beats the template.
    """
    tpl = TEMPLATES.get(name)
    if not tpl:
        return []
    notes: list[str] = []
    # Defaults that mean "not set by the creator", per field.
    default = {"style": "auto", "intensity": "auto", "captions": "auto",
               "music": True}
    for field, value in tpl.items():
        cur = getattr(req, field, None)
        if cur == default.get(field, None) or (field == "music" and cur is True):
            setattr(req, field, value)
            notes.append(f"{field}={value}")
    return [f"template '{name}': " + ", ".join(notes)] if notes else []

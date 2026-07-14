"""Kreator — The Operating System for Human Creativity.

Kreator edits a creator's gameplay for them: it understands the footage, cuts
the boring parts, keeps the action (and dialogue and scenes worth keeping), and
delivers a tighter video — all locally, offline, on CPU.

    Signal Layer → understanding (speech + VLM) → Director → K Editor → render

**Inviolable rule — Kreator is NOT a generative AI.** Every pixel and sound in
the output comes from the video the user uploaded. Kreator only analyzes,
selects, cuts, reorders, and reassembles the creator's own material; it never
generates, fabricates, or pulls content from outside the footage. The
understanding models (Whisper, SmolVLM) only *describe* the real footage so the
deterministic Planner can decide how to cut it — the AI describes, the Planner
decides, the footage is the creator's. See ``docs/not-generative.md``.

Sub-packages: ``signal_layer`` (deterministic CPU signals), ``evidence`` +
``planner`` (K Clipper / E1 ranking), ``editor`` (K Editor condense + render),
``speech`` (dialogue), ``vlm`` (scene understanding), ``director`` (autonomous
"how to edit this" decision).
"""

__version__ = "0.1.0"

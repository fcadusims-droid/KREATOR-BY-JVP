"""Render an edit plan to an actual video file — via the DSL executor.

``render_segments`` is the plain "condense only" render: it expresses the
plan's kept segments as a cuts-only ``EditProgram`` and hands it to the one
FFmpeg executor (``kreator.dsl.execute_program``), so there is a single
filtergraph builder in the codebase. The executor's trim/concat is
frame-accurate (cuts at exact times, not just keyframes) at the cost of
re-encoding the kept parts — the right trade-off for a condensed export.
"""

from __future__ import annotations

from ..dsl import Cut, EditProgram, execute_program
from .condenser import EditPlan


def render_segments(
    video_path: str,
    plan: EditPlan,
    out_path: str,
    *,
    has_audio: bool = True,
    height: int | None = None,
    crf: int = 23,
    preset: str = "veryfast",
    verbose: bool = False,
) -> str:
    """Render ``plan``'s kept segments from ``video_path`` into ``out_path``.

    ``height`` scales the output (e.g. 480/720/1080); ``None`` keeps the source
    resolution. Returns the output path. Raises if the plan is empty or ffmpeg
    fails.
    """
    if not plan.segments:
        raise ValueError("edit plan has no segments to render")

    program = EditProgram(
        cuts=[Cut(s.span.start, s.span.end,
                  reason=f"kept (interest {s.mean_interest:.2f})")
              for s in plan.segments],
        height=height,
    )
    return execute_program(video_path, program, out_path, has_audio=has_audio,
                           crf=crf, preset=preset, verbose=verbose)

"""Render an edit plan to an actual video file with FFmpeg.

Uses a single ``trim``/``concat`` filtergraph, which is frame-accurate (cuts
at exact times, not just keyframes) at the cost of re-encoding the kept parts —
the right trade-off for a condensed export, where quality at the seams matters
and the kept portion is a fraction of the original.

The filtergraph is written to a script file (``-filter_complex_script``) so a
plan with dozens of segments doesn't blow the command-line length limit.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from .condenser import EditPlan


def _ffmpeg_bin() -> str:
    """Prefer a system ffmpeg; fall back to the imageio-ffmpeg binary."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # pragma: no cover
        return "ffmpeg"


def _build_filtergraph(plan: EditPlan, has_audio: bool) -> str:
    parts: list[str] = []
    labels: list[str] = []
    for i, seg in enumerate(plan.segments):
        s, e = seg.span.start, seg.span.end
        parts.append(
            f"[0:v]trim=start={s:.3f}:end={e:.3f},setpts=PTS-STARTPTS[v{i}];"
        )
        if has_audio:
            parts.append(
                f"[0:a]atrim=start={s:.3f}:end={e:.3f},asetpts=PTS-STARTPTS[a{i}];"
            )
        labels.append(f"[v{i}][a{i}]" if has_audio else f"[v{i}]")
    n = len(plan.segments)
    if has_audio:
        parts.append(f"{''.join(labels)}concat=n={n}:v=1:a=1[outv][outa]")
    else:
        parts.append(f"{''.join(labels)}concat=n={n}:v=1:a=0[outv]")
    return "".join(parts)


def render_segments(
    video_path: str,
    plan: EditPlan,
    out_path: str,
    *,
    has_audio: bool = True,
    crf: int = 23,
    preset: str = "veryfast",
    verbose: bool = False,
) -> str:
    """Render ``plan``'s kept segments from ``video_path`` into ``out_path``.

    Returns the output path. Raises if the plan is empty or FFmpeg fails.
    """
    if not plan.segments:
        raise ValueError("edit plan has no segments to render")

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    graph = _build_filtergraph(plan, has_audio)

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
        fh.write(graph)
        script = fh.name

    cmd = [
        _ffmpeg_bin(), "-y", "-i", video_path,
        "-filter_complex_script", script,
        "-map", "[outv]",
        *(["-map", "[outa]"] if has_audio else []),
        "-c:v", "libx264", "-crf", str(crf), "-preset", preset,
        *(["-c:a", "aac", "-b:a", "128k"] if has_audio else []),
        out_path,
    ]
    if verbose:
        print("[render] segments:", len(plan.segments), "->", out_path)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    Path(script).unlink(missing_ok=True)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-8:])
        raise RuntimeError(f"ffmpeg failed:\n{tail}")
    return out_path

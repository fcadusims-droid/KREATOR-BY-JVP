"""Execute an EditProgram with FFmpeg — the deterministic operations runner.

Today it runs the `cut` spine (trim/concat, frame-accurate), burns `subtitle`
overlays (libass), and scales to the target height. Other operation types are
carried in the program but not yet executed; they raise nothing — they're just
skipped until their executor lands.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from .program import EditProgram


def _ffmpeg_bin() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # pragma: no cover
        return "ffmpeg"


def _srt_time(t: float) -> str:
    t = max(0.0, t)
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(subtitles, path: str) -> None:
    """Write edited-timeline subtitles to an SRT file."""
    lines = []
    for i, sub in enumerate(sorted(subtitles, key=lambda s: s.start), start=1):
        lines.append(str(i))
        lines.append(f"{_srt_time(sub.start)} --> {_srt_time(sub.end)}")
        lines.append(sub.text)
        lines.append("")
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def _build_filtergraph(program: EditProgram, has_audio: bool, srt_path: str | None):
    parts: list[str] = []
    labels: list[str] = []
    for i, cut in enumerate(program.cuts):
        s, e = cut.source_start, cut.source_end
        parts.append(f"[0:v]trim=start={s:.3f}:end={e:.3f},setpts=PTS-STARTPTS[v{i}];")
        if has_audio:
            parts.append(f"[0:a]atrim=start={s:.3f}:end={e:.3f},asetpts=PTS-STARTPTS[a{i}];")
        labels.append(f"[v{i}][a{i}]" if has_audio else f"[v{i}]")

    n = len(program.cuts)
    if has_audio:
        parts.append(f"{''.join(labels)}concat=n={n}:v=1:a=1[cv][outa];")
    else:
        parts.append(f"{''.join(labels)}concat=n={n}:v=1:a=0[cv];")

    vlabel = "cv"
    if srt_path:
        style = ("FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
                 "BorderStyle=1,Outline=2,Shadow=0,Bold=1,Alignment=2,MarginV=28")
        parts.append(f"[{vlabel}]subtitles='{srt_path}':force_style='{style}'[sv];")
        vlabel = "sv"
    if program.height:
        parts.append(f"[{vlabel}]scale=-2:{int(program.height)}[outs];")
        vlabel = "outs"

    return "".join(parts).rstrip(";"), vlabel


def execute_program(
    video_path: str,
    program: EditProgram,
    out_path: str,
    *,
    has_audio: bool = True,
    crf: int = 23,
    preset: str = "veryfast",
    verbose: bool = False,
) -> str:
    """Render ``program`` from ``video_path`` into ``out_path``."""
    if not program.cuts:
        raise ValueError("edit program has no cuts to render")

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.mkdtemp()
    srt_path = None
    if program.subtitles:
        srt_path = str(Path(tmp) / "subs.srt")
        write_srt(program.subtitles, srt_path)

    graph, vlabel = _build_filtergraph(program, has_audio, srt_path)
    script = str(Path(tmp) / "graph.txt")
    Path(script).write_text(graph, encoding="utf-8")

    cmd = [
        _ffmpeg_bin(), "-y", "-i", video_path,
        "-filter_complex_script", script,
        "-map", f"[{vlabel}]",
        *(["-map", "[outa]"] if has_audio else []),
        "-c:v", "libx264", "-crf", str(crf), "-preset", preset,
        "-movflags", "+faststart",
        *(["-c:a", "aac", "-b:a", "128k"] if has_audio else []),
        out_path,
    ]
    if verbose:
        print(f"[dsl] {len(program.cuts)} cuts, {len(program.subtitles)} subtitles "
              f"-> {out_path}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    shutil.rmtree(tmp, ignore_errors=True)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-8:])
        raise RuntimeError(f"ffmpeg failed:\n{tail}")
    return out_path

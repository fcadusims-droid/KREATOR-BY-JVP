"""Execute an EditProgram with FFmpeg — the deterministic operations runner.

Today it runs the `cut` spine (trim/concat, frame-accurate), burns `subtitle`
overlays (libass), applies `zoom` punch-ins and `transition` crossfades, mixes a
`music` bed under the audio, reframes to a target aspect (`reframe`: 9:16
Shorts via focus-aware crop or pad), and scales to the target height.
`broll` is carried in the program but not yet executed — it raises nothing,
just skipped until its executor lands.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from ..ffmpeg import ffmpeg_bin
from .program import EditProgram


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


def _zoom_scale_for(program: EditProgram, edited_start: float, edited_end: float):
    """Return the zoom scale to apply to a cut occupying this edited-time range,
    or None. A cut is zoomed if a Zoom op overlaps its edited range."""
    for z in program.zooms:
        if z.start < edited_end and edited_start < z.end:
            return z.scale
    return None


def _reframe_chain(program: EditProgram, cut_index: int) -> str:
    """The per-segment crop/pad filter step for the program's Reframe, or "".

    Written with iw/ih expressions so it works at any source resolution, and
    with output dimensions forced even (x264 requires it). ``crop`` centers the
    window on the cut's focus, clamped inside the frame; ``pad`` fits the whole
    frame and adds neutral bars. Applied per segment (same aspect for all), so
    concat/xfade still see identical dimensions.
    """
    rf = program.reframe
    if rf is None:
        return ""
    aw, ah = rf.aspect.split(":")
    # Target width at full height is ih*aw/ah; target height at full width is
    # iw*ah/aw. min() picks whichever fits inside the source (crop), max()
    # whichever contains it (pad).
    if rf.strategy == "pad":
        return (f",pad=w='trunc((max(iw,ih*{aw}/{ah})+1)/2)*2'"
                f":h='trunc((max(ih,iw*{ah}/{aw})+1)/2)*2'"
                f":x=(ow-iw)/2:y=(oh-ih)/2")
    fx = rf.focus_x[cut_index] if cut_index < len(rf.focus_x) else 0.5
    return (f",crop=w='trunc(min(iw,ih*{aw}/{ah})/2)*2'"
            f":h='trunc(min(ih,iw*{ah}/{aw})/2)*2'"
            f":x='clip(iw*{fx:.4f}-ow/2,0,iw-ow)':y='(ih-oh)/2'")


def _crossfade_chain(parts: list, program: EditProgram, n: int, has_audio: bool) -> None:
    """Chain xfade (video) + acrossfade (audio) across the segments, ending in
    [cv]/[outa]. Each transition overlaps neighbours by ``duration`` seconds, so
    video and audio shorten together and stay in sync."""
    d = program.transitions[0].duration
    # Video: offset of each xfade is the accumulated length so far, minus d.
    acc = program.cuts[0].duration
    prev = "v0"
    for i in range(1, n):
        off = acc - d
        out = "cv" if i == n - 1 else f"vt{i}"
        parts.append(f"[{prev}][v{i}]xfade=transition=fade:duration={d}:"
                     f"offset={off:.3f}[{out}];")
        prev = out
        acc += program.cuts[i].duration - d
    if has_audio:
        aprev = "a0"
        for i in range(1, n):
            aout = "outa" if i == n - 1 else f"at{i}"
            parts.append(f"[{aprev}][a{i}]acrossfade=d={d}[{aout}];")
            aprev = aout


def _build_filtergraph(program: EditProgram, has_audio: bool, srt_path: str | None):
    parts: list[str] = []
    labels: list[str] = []
    elapsed = 0.0
    # xfade requires a constant frame rate; after trim+setpts it isn't, so force
    # one on every segment when transitions are in play.
    fps_fix = ",fps=30" if program.transitions and len(program.cuts) > 1 else ""
    for i, cut in enumerate(program.cuts):
        s, e = cut.source_start, cut.source_end
        scale = _zoom_scale_for(program, elapsed, elapsed + cut.duration)
        # A punch-in: scale up, then crop back to the original size (centered),
        # so every segment stays the same dimensions and concat still works.
        zoom_chain = (f",scale=iw*{scale}:ih*{scale},crop=iw/{scale}:ih/{scale}"
                      if scale else "")
        parts.append(
            f"[0:v]trim=start={s:.3f}:end={e:.3f},setpts=PTS-STARTPTS"
            f"{zoom_chain}{_reframe_chain(program, i)}{fps_fix}[v{i}];")
        if has_audio:
            parts.append(f"[0:a]atrim=start={s:.3f}:end={e:.3f},asetpts=PTS-STARTPTS[a{i}];")
        labels.append(f"[v{i}][a{i}]" if has_audio else f"[v{i}]")
        elapsed += cut.duration

    n = len(program.cuts)
    if program.transitions and n > 1:
        _crossfade_chain(parts, program, n, has_audio)
    elif has_audio:
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

    # Background music (from the K Library) mixed under the original audio. The
    # music is input [1:a], looped, lowered to its volume, and trimmed to the
    # video length (duration=first).
    alabel = "outa"
    if has_audio and program.music:
        vol = program.music[0].volume
        parts.append(f"[1:a]volume={vol}[mus];"
                     f"[outa][mus]amix=inputs=2:duration=first:dropout_transition=0[amx];")
        alabel = "amx"

    return "".join(parts).rstrip(";"), vlabel, alabel


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

    graph, vlabel, alabel = _build_filtergraph(program, has_audio, srt_path)
    script = str(Path(tmp) / "graph.txt")
    Path(script).write_text(graph, encoding="utf-8")

    # A background music track becomes a second, looped input.
    music_track = program.music[0].track if (has_audio and program.music) else None

    cmd = [ffmpeg_bin(), "-y", "-i", video_path]
    if music_track:
        cmd += ["-stream_loop", "-1", "-i", music_track]
    cmd += [
        "-filter_complex_script", script,
        "-map", f"[{vlabel}]",
        *(["-map", f"[{alabel}]"] if has_audio else []),
        "-c:v", "libx264", "-crf", str(crf), "-preset", preset,
        "-movflags", "+faststart",
        *(["-c:a", "aac", "-b:a", "128k"] if has_audio else []),
        out_path,
    ]
    if verbose:
        print(f"[dsl] {len(program.cuts)} cuts, {len(program.subtitles)} subtitles, "
              f"{len(program.music)} music -> {out_path}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    shutil.rmtree(tmp, ignore_errors=True)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-8:])
        raise RuntimeError(f"ffmpeg failed:\n{tail}")
    return out_path

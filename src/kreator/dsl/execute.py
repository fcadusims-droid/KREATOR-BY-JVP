"""Execute an EditProgram with FFmpeg — the deterministic operations runner.

Today it runs the `cut` spine (trim/concat, frame-accurate), burns `subtitle`
overlays (libass) and word-level `caption` karaoke, applies `zoom` punch-ins
and `transition` crossfades, mixes a `music` bed and `sfx` one-shots under the
audio, overlays `broll` cutaways (real K Library clips, scaled to the frame),
reframes to a target aspect (`reframe`: 9:16 Shorts via focus-aware crop or
pad), and scales to the target height.
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


def _input_map(program: EditProgram, has_audio: bool):
    """Assign an FFmpeg input index to every extra media file the program
    needs, in a fixed order (music, sfx…, broll…). The command builder and the
    filtergraph builder both derive from this, so they can never disagree."""
    idx = 1
    music_idx = None
    if has_audio and program.music:
        music_idx = idx
        idx += 1
    sfx_idxs = []
    if has_audio:
        for _ in program.sfx:
            sfx_idxs.append(idx)
            idx += 1
    broll_idxs = []
    for _ in program.broll:
        broll_idxs.append(idx)
        idx += 1
    return music_idx, sfx_idxs, broll_idxs


def _reframed_dims(src_w: int, src_h: int, program: EditProgram):
    """The main video's dimensions after the (optional) reframe step — what a
    b-roll overlay must be scaled to. Mirrors the executor's crop/pad math."""
    rf = program.reframe
    if rf is None:
        return src_w, src_h
    if rf.strategy == "pad":
        aw, ah = (int(x) for x in rf.aspect.split(":"))
        pw = max(src_w, src_h * aw / ah)
        ph = max(src_h, src_w * ah / aw)
        even_up = lambda x: int((x + 1) // 2) * 2  # noqa: E731
        return even_up(pw), even_up(ph)
    from ..reframe import crop_window

    _, _, w, h = crop_window(src_w, src_h, rf.aspect)
    return w, h


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


def _build_filtergraph(program: EditProgram, has_audio: bool,
                       subs_path: str | None, main_dims=None):
    music_idx, sfx_idxs, broll_idxs = _input_map(program, has_audio)
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
    # B-roll cutaways go under the captions: each library clip is scaled to
    # the main frame (dims known from the probe + reframe math), shifted to
    # its window start, and overlaid only inside its window — the main video
    # continues underneath and resumes after (eof_action=repeat keeps the
    # stream alive; enable gates what is actually shown).
    if program.broll and broll_idxs:
        if main_dims is None:
            raise ValueError("broll requires the main video dimensions")
        bw, bh = _reframed_dims(main_dims[0], main_dims[1], program)
        for j, (b, bi) in enumerate(zip(program.broll, broll_idxs)):
            end = b.start + b.duration
            parts.append(
                f"[{bi}:v]scale={bw}:{bh},setpts=PTS+{b.start:.3f}/TB[bd{j}];"
                f"[{vlabel}][bd{j}]overlay=eof_action=repeat:"
                f"enable='between(t,{b.start:.3f},{end:.3f})'[bo{j}];")
            vlabel = f"bo{j}"
    if subs_path:
        # A karaoke .ass carries its own style; a plain .srt gets the house one.
        if subs_path.endswith(".ass"):
            parts.append(f"[{vlabel}]subtitles='{subs_path}'[sv];")
        else:
            style = ("FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
                     "BorderStyle=1,Outline=2,Shadow=0,Bold=1,Alignment=2,MarginV=28")
            parts.append(f"[{vlabel}]subtitles='{subs_path}':force_style='{style}'[sv];")
        vlabel = "sv"
    if program.height:
        parts.append(f"[{vlabel}]scale=-2:{int(program.height)}[outs];")
        vlabel = "outs"

    # Audio layers under the original track: a looped K Library music bed
    # (lowered to its volume) and sfx one-shots (delayed to their instant).
    # normalize=0 keeps the creator's own audio at full level — amix's default
    # would divide everything by the input count.
    alabel = "outa"
    layers: list[str] = []
    if has_audio and program.music and music_idx is not None:
        vol = program.music[0].volume
        parts.append(f"[{music_idx}:a]volume={vol}[mus];")
        layers.append("mus")
    for j, (sf, si) in enumerate(zip(program.sfx, sfx_idxs)):
        ms = int(round(sf.at * 1000))
        parts.append(f"[{si}:a]adelay={ms}|{ms},volume={sf.volume}[sx{j}];")
        layers.append(f"sx{j}")
    if has_audio and layers:
        labels = "".join(f"[{l}]" for l in layers)
        parts.append(f"[outa]{labels}amix=inputs={1 + len(layers)}:"
                     f"duration=first:dropout_transition=0:normalize=0[amx];")
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
    subs_path = None
    if program.captions:
        from .captions import write_ass

        subs_path = str(Path(tmp) / "subs.ass")
        write_ass(program.captions, subs_path, style=program.caption_style)
    elif program.subtitles:
        subs_path = str(Path(tmp) / "subs.srt")
        write_srt(program.subtitles, subs_path)

    # B-roll overlays need the main video's dimensions to scale to.
    main_dims = None
    if program.broll:
        from ..validator.check import probe

        info = probe(video_path)
        main_dims = (info["width"], info["height"])

    graph, vlabel, alabel = _build_filtergraph(program, has_audio, subs_path,
                                               main_dims=main_dims)
    script = str(Path(tmp) / "graph.txt")
    Path(script).write_text(graph, encoding="utf-8")

    # Extra media files become inputs in _input_map's fixed order.
    music_idx, sfx_idxs, _broll_idxs = _input_map(program, has_audio)
    cmd = [ffmpeg_bin(), "-y", "-i", video_path]
    if music_idx is not None:
        cmd += ["-stream_loop", "-1", "-i", program.music[0].track]
    for sf, _ in zip(program.sfx, sfx_idxs):
        cmd += ["-i", sf.sound]
    for b in program.broll:
        cmd += ["-i", b.path]
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

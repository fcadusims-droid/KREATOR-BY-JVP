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


def _atempo_chain(speed: float) -> str:
    """An atempo filter chain for ``speed`` (atempo only accepts 0.5–100 per
    stage, so extreme slow-mo chains stages)."""
    if speed == 1.0:
        return ""
    parts = []
    remaining = speed
    while remaining < 0.5:
        parts.append("atempo=0.5")
        remaining /= 0.5
    parts.append(f"atempo={remaining:g}")
    return "," + ",".join(parts)


# Named color treatments — deterministic filter chains, a LUT's job done
# programmatically on real pixels.
_GRADES = {
    "vivid": "eq=contrast=1.08:saturation=1.25:brightness=0.01",
    "cinematic": ("eq=contrast=1.12:saturation=0.92,"
                  "colorbalance=bs=0.06:ms=0.02:hs=-0.04"),
    "punchy": "eq=contrast=1.15:saturation=1.35:gamma=0.98",
}


def _zoom_chain(program: EditProgram, dims) -> str:
    """One zoompan combining every zoom move: PunchZoom pulses (exponential
    snap-and-ease at the event) and KenBurns ramps (a slow linear push across
    a window). Runs on the concatenated (post-reframe) stream, so ``dims`` are
    its dimensions. Empty when there is no zoom move."""
    if not (program.punch_zooms or program.ken_burns):
        return ""
    terms = ["1"]
    for p in program.punch_zooms:
        terms.append(f"{p.amount}*exp(-abs(in-{p.at * 30:.0f})"
                     f"/{max(p.width, 0.1) * 15:.1f})")
    for k in program.ken_burns:
        f0, f1 = k.start * 30, k.end * 30
        span = max(f1 - f0, 1.0)
        # (z_from-1) + (z_to-z_from)*progress, active only inside the window.
        terms.append(
            f"between(in,{f0:.0f},{f1:.0f})*"
            f"({k.z_from - 1:+.3f}{k.z_to - k.z_from:+.3f}"
            f"*clip((in-{f0:.0f})/{span:.1f},0,1))")
    # Horizontal pan for a Ken Burns move: drift the crop across the frame.
    pan = program.ken_burns[0].pan if program.ken_burns else 0.0
    if pan:
        f0, f1 = program.ken_burns[0].start * 30, program.ken_burns[0].end * 30
        span = max(f1 - f0, 1.0)
        x = (f"iw/2-(iw/zoom/2)+{pan:.2f}*(iw-iw/zoom)"
             f"*clip((in-{f0:.0f})/{span:.1f},0,1)")
    else:
        x = "iw/2-(iw/zoom/2)"
    w, h = dims
    return (f",zoompan=z='{'+'.join(terms)}'"
            f":d=1:x='{x}':y='ih/2-(ih/zoom/2)'"
            f":s={w}x{h}:fps=30")


def _shake_chain(program: EditProgram) -> str:
    """Slight upscale + crop-window jitter inside each Shake window. The
    incommensurate sin/cos frequencies read as impact, not oscillation."""
    if not program.shakes:
        return ""
    jx = "+".join(f"between(t,{s.start:.3f},{s.end:.3f})*{s.amplitude:g}*sin(53*t)"
                  for s in program.shakes)
    jy = "+".join(f"between(t,{s.start:.3f},{s.end:.3f})*{s.amplitude * 0.75:g}*cos(41*t)"
                  for s in program.shakes)
    return (",scale=iw*1.06:ih*1.06"
            ",crop=w='trunc(iw/1.06/2)*2':h='trunc(ih/1.06/2)*2'"
            f":x='(iw-ow)/2+{jx}':y='(ih-oh)/2+{jy}'")


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
    acc = program.cuts[0].edited_duration
    prev = "v0"
    for i in range(1, n):
        off = acc - d
        out = "cv" if i == n - 1 else f"vt{i}"
        parts.append(f"[{prev}][v{i}]xfade=transition=fade:duration={d}:"
                     f"offset={off:.3f}[{out}];")
        prev = out
        acc += program.cuts[i].edited_duration - d
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
    # xfade and zoompan require a constant frame rate; after trim+setpts it
    # isn't, so force one when either is in play.
    fps_fix = (",fps=30" if (program.transitions and len(program.cuts) > 1)
               or program.punch_zooms else "")
    for i, cut in enumerate(program.cuts):
        s, e = cut.source_start, cut.source_end
        scale = _zoom_scale_for(program, elapsed, elapsed + cut.edited_duration)
        # A punch-in: scale up, then crop back to the original size (centered),
        # so every segment stays the same dimensions and concat still works.
        zoom_chain = (f",scale=iw*{scale}:ih*{scale},crop=iw/{scale}:ih/{scale}"
                      if scale else "")
        # Playback speed: video PTS divided, audio tempo-matched below.
        setpts = ("PTS-STARTPTS" if cut.speed == 1.0
                  else f"(PTS-STARTPTS)/{cut.speed:g}")
        parts.append(
            f"[0:v]trim=start={s:.3f}:end={e:.3f},setpts={setpts}"
            f"{zoom_chain}{_reframe_chain(program, i)}{fps_fix}[v{i}];")
        if has_audio:
            parts.append(f"[0:a]atrim=start={s:.3f}:end={e:.3f},"
                         f"asetpts=PTS-STARTPTS{_atempo_chain(cut.speed)}[a{i}];")
        labels.append(f"[v{i}][a{i}]" if has_audio else f"[v{i}]")
        elapsed += cut.edited_duration

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
    # K Motion effects run on the assembled (post-reframe) stream, before
    # captions burn — text must not zoom or shake.
    if program.punch_zooms or program.ken_burns:
        if main_dims is None:
            raise ValueError("zoom moves require the main video dimensions")
        dims = _reframed_dims(main_dims[0], main_dims[1], program)
        parts.append(f"[{vlabel}]{_zoom_chain(program, dims)[1:]}[pz];")
        vlabel = "pz"
    if program.shakes:
        parts.append(f"[{vlabel}]{_shake_chain(program)[1:]}[shk];")
        vlabel = "shk"
    if program.grade and program.grade.preset in _GRADES:
        parts.append(f"[{vlabel}]{_GRADES[program.grade.preset]}[grd];")
        vlabel = "grd"
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
    voice = "outa"
    duck = has_audio and program.music and program.music[0].duck
    if duck:
        # Split the creator's audio: one copy is the key that ducks the music.
        parts.append("[outa]asplit=2[voice][duckkey];")
        voice = "voice"
    if has_audio and program.music and music_idx is not None:
        vol = program.music[0].volume
        parts.append(f"[{music_idx}:a]volume={vol}[mus];")
        if duck:
            # Sidechain-compress the bed under the voice — the narration cuts
            # through, the music swells back in the gaps.
            parts.append("[mus][duckkey]sidechaincompress="
                         "threshold=0.03:ratio=8:attack=20:release=350[musd];")
            layers.append("musd")
        else:
            layers.append("mus")
    for j, (sf, si) in enumerate(zip(program.sfx, sfx_idxs)):
        ms = int(round(sf.at * 1000))
        parts.append(f"[{si}:a]adelay={ms}|{ms},volume={sf.volume}[sx{j}];")
        layers.append(f"sx{j}")
    if has_audio and layers:
        labels = "".join(f"[{l}]" for l in layers)
        parts.append(f"[{voice}]{labels}amix=inputs={1 + len(layers)}:"
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

    # B-roll overlays and zoom moves (pulses, Ken Burns) need the main dims.
    main_dims = None
    if program.broll or program.punch_zooms or program.ken_burns:
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

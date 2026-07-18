"""Build renderable Shorts from ranked candidates.

Pure parts (``fit_span``, ``build_short_program``) are testable with no video;
``make_shorts`` is the driver that runs the real pipeline end to end.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ..dsl import (EditProgram, captions_from_transcript, execute_program,
                   subtitles_from_transcript)
from ..dsl.program import Reframe
from ..types import Timespan


@dataclass(frozen=True)
class ShortSpec:
    """How to shape each Short."""
    min_len: float = 15.0     # a Short below this doesn't read as a moment
    max_len: float = 60.0     # platform ceiling for Shorts
    aspect: str | None = "9:16"
    height: int | None = 1080
    subtitles: bool = True
    karaoke: bool = True      # word-by-word captions when word timings exist
    style: str = "montage"    # K Motion preset: montage|cinematic|clean|none


def fit_span(span: Timespan, video_duration: float, spec: ShortSpec) -> Timespan:
    """Fit a candidate span into ``[min_len, max_len]``, inside the video.

    Too short → grow symmetrically around the center (context on both sides);
    too long → trim symmetrically around the center (the trigger sits mid-span
    by construction of the Analyst window). Always clamped to the video, and if
    the video itself is shorter than ``min_len``, the whole video is the Short.
    """
    if video_duration <= spec.min_len:
        return Timespan(0.0, video_duration)

    start, end = span.start, span.end
    if span.duration < spec.min_len:
        need = (spec.min_len - span.duration) / 2.0
        start, end = start - need, end + need
    elif span.duration > spec.max_len:
        excess = (span.duration - spec.max_len) / 2.0
        start, end = start + excess, end - excess

    # Clamp while preserving the fitted length where possible.
    if start < 0.0:
        end = min(end - start, video_duration)
        start = 0.0
    if end > video_duration:
        start = max(0.0, start - (end - video_duration))
        end = video_duration
    return Timespan(start, end)


def build_short_program(
    span: Timespan,
    spec: ShortSpec,
    *,
    focus_x: float = 0.5,
    transcript: list | None = None,
    events: list | None = None,
    rationale: list[str] | None = None,
) -> EditProgram:
    """One candidate → one EditProgram, with the K Motion treatment.

    The cut spine, slow-mo split, zoom pulses, shake, and grade come from the
    motion planner, keyframed on the clip's GameSense events; captions remap
    correctly through the slow-mo (speed-aware timeline).
    """
    from ..motion import plan_motion

    motion = plan_motion(span, events or [], style=spec.style)
    cuts = motion.cuts
    caps = (captions_from_transcript(transcript, cuts, reason="spoken dialogue")
            if spec.karaoke and spec.subtitles and transcript else [])
    subs = (subtitles_from_transcript(transcript, cuts, reason="spoken dialogue")
            if spec.subtitles and transcript and not caps else [])
    reframe = None
    if spec.aspect:
        # The split cuts are the same moment — one focus serves them all.
        reframe = Reframe(aspect=spec.aspect, strategy="crop",
                          focus_x=tuple(focus_x for _ in cuts),
                          reason=f"reframed to {spec.aspect} following the action")
    return EditProgram(cuts=cuts, subtitles=subs, captions=caps,
                       punch_zooms=motion.punch_zooms, shakes=motion.shakes,
                       grade=motion.grade, reframe=reframe,
                       height=spec.height,
                       rationale=list(rationale or []) + motion.rationale)


def make_shorts(
    video_path: str,
    out_dir: str,
    *,
    top_n: int = 5,
    spec: ShortSpec | None = None,
    transcript: list | None = None,
    bundle=None,
    focus_profile: str = "follow",
    gamesense: bool = True,
    provenance_log: str | None = None,
    progress=lambda s: None,
) -> dict:
    """Rank the video's moments and render each of the top-N as a Short.

    Returns a manifest dict (also written to ``out_dir/shorts.json``): one entry
    per Short with its file, source span, score, rationale, and validation.
    ``bundle`` lets a caller reuse an existing signal analysis; ``transcript``
    (source-time SpeechSegments) enables burned captions. With ``gamesense``
    the game's own screen (and the announcer, via the transcript) re-scores
    the candidates: a multikill medal boosts a moment, the player dying on
    screen sinks it — signal energy alone cannot tell those apart.
    """
    from ..evidence import KAnalyst
    from ..gamesense import announcer_events, read_screen_events, viral_adjustment
    from ..planner import KClipper
    from ..reframe import cut_focus_centers
    from ..signal_layer import analyze_video
    from ..validator import validate_render

    spec = spec or ShortSpec()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    if bundle is None:
        progress("Analyzing video (motion, audio, scenes)…")
        bundle = analyze_video(video_path)
    has_audio = any(a > 0.0 for a in bundle.audio)

    progress("Ranking the best moments…")
    evidences = KAnalyst().analyze(bundle, video_path=video_path)
    # Rank extra candidates: fitting a span to Short length can make two
    # nearby moments overlap heavily even though their raw windows didn't
    # (seen on real footage: moments 8s apart became near-identical 15s
    # Shorts). Dedup happens *after* fitting, so extras fill the gaps.
    pool = KClipper().rank(evidences, top_n=top_n * 3)
    pool_spans = [fit_span(c.span, bundle.duration, spec) for c in pool]

    # GameSense pass: what did the game itself say happened in each window?
    hud_events: list = []
    if gamesense and pool_spans:
        progress("Reading the game's screen (OCR over candidate windows)…")
        hud_events = read_screen_events(
            video_path, [(s.start, s.end) for s in pool_spans])

    scored = []
    for cand, span in zip(pool, pool_spans):
        window = [e for e in hud_events if span.start <= e.time <= span.end]
        window += announcer_events(transcript or [], span)
        delta, reasons = viral_adjustment(window)
        scored.append((cand.score + delta, cand, span, window, reasons))
    # Re-rank on the event-adjusted score; original rank breaks ties.
    scored.sort(key=lambda x: (-x[0], x[1].rank))

    candidates, fitted, extras = [], [], []
    for adj, cand, span, window, reasons in scored:
        # Over a third of shared footage reads as the same Short twice.
        if any(span.intersection(f) / max(span.duration, 1e-6) > 0.35
               for f in fitted):
            continue
        candidates.append(cand)
        fitted.append(span)
        extras.append((adj, window, reasons))
        if len(candidates) >= top_n:
            break
    focus = [0.5] * len(fitted)
    if spec.aspect:
        progress("Finding the action's focus in each moment…")
        focus = cut_focus_centers(video_path,
                                  [(s.start, s.end) for s in fitted],
                                  profile=focus_profile)

    entries = []
    for i, (cand, span, (adj, window, reasons)) in enumerate(
            zip(candidates, fitted, extras), start=1):
        progress(f"Rendering Short {i}/{len(candidates)}…")
        rationale = [f"Signal rank #{cand.rank}: {cand.rationale}"] + reasons
        program = build_short_program(
            span, spec, focus_x=focus[i - 1], transcript=transcript,
            events=window, rationale=rationale)
        dest = str(out / f"short_{i:02d}.mp4")
        execute_program(video_path, program, dest, has_audio=has_audio)
        report = validate_render(dest, program, has_audio=has_audio)
        if provenance_log:
            from ..provenance import record_render
            record_render(provenance_log, source_video=video_path,
                          output_path=dest, program=program.to_dict())
        entries.append({
            "file": Path(dest).name,
            "rank": i,
            "signal_rank": cand.rank,
            "score": round(adj, 3),
            "signal_score": cand.score,
            "source_span": {"start": round(span.start, 2), "end": round(span.end, 2)},
            "duration": round(span.duration, 2),
            "rationale": " ".join(rationale),
            "game_events": [e.to_dict() for e in window],
            "subtitles": len(program.subtitles),
            "captions": len(program.captions),
            "aspect": spec.aspect,
            "validation": report.to_dict(),
        })

    manifest = {"video": video_path, "top_n": top_n, "shorts": entries}
    (out / "shorts.json").write_text(json.dumps(manifest, indent=2),
                                     encoding="utf-8")
    return manifest

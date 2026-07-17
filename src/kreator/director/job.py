"""One upload → several deliverables, from a single analysis pass.

This is the production flow from the spec (§3, §11): "here's my session — give
me the full edit *and* five Shorts". The expensive understanding (signals, VLM
scenes, transcript) runs **once**; each deliverable is then composed from that
shared understanding, rendered, validated, and listed in a manifest with its
rationale. The guided web UI and the conversational parser both produce a
``JobRequest`` — it is the form the Director fills in, however you ask.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ..cache import ANALYSIS_VERSION, AnalysisCache, content_key
from ..dsl import compose_program, execute_program
from ..editor import Condenser, pause_cut_plan
from ..provenance import record_render
from ..reframe import cut_focus_centers
from ..shorts import ShortSpec, make_shorts
from ..speech import SpeechSegment, Word, presence_series, transcribe
from ..types import SignalBundle
from ..validator import validate_render
from .auto import Understanding, _pick_music, understand_video
from .content import EDITING_PRESETS, detect_content


# How aggressively to condense, when the user picks instead of the preset.
_KEEP_BY_INTENSITY = {"light": 0.55, "medium": 0.40, "heavy": 0.28}


@dataclass
class JobRequest:
    """What the creator asked for. Defaults reproduce the autonomous edit."""
    long_edit: bool = True
    shorts: int = 0                  # how many vertical Shorts to also produce
    aspect: str | None = None        # long-edit aspect (None = keep source)
    captions: str = "auto"           # auto | none | plain | karaoke
    language: str | None = None      # spoken-language ISO code; None = detect
    intensity: str = "auto"          # auto | light | medium | heavy
    height: int = 720
    music: bool = True
    min_short_len: float = 15.0
    max_short_len: float = 60.0
    notes: list[str] = field(default_factory=list)  # how this request was formed

    def to_dict(self) -> dict:
        return {"long_edit": self.long_edit, "shorts": self.shorts,
                "aspect": self.aspect, "captions": self.captions,
                "language": self.language,
                "intensity": self.intensity, "height": self.height,
                "music": self.music, "min_short_len": self.min_short_len,
                "max_short_len": self.max_short_len, "notes": self.notes}


def _cached_understanding(
    video_path: str, cache: AnalysisCache, vlm_frames: int, vlm_backend,
    progress: Callable[[str], None],
) -> Understanding:
    """understand_video with an incremental cache in front of it: on a hit the
    signals and scene labels come from disk and no video is decoded at all."""
    from ..vlm import visual_keep_series
    from ..vlm.label import SceneLabel

    kb = content_key(video_path, {"stage": "signals", "v": ANALYSIS_VERSION})
    ks = content_key(video_path, {"stage": "scenes", "v": ANALYSIS_VERSION,
                                  "frames": vlm_frames})
    b, s = cache.get(kb), cache.get(ks)
    if b is not None and s is not None:
        progress("Reusing cached analysis (signals + scenes)…")
        bundle = SignalBundle.from_dict(b)
        labels = [SceneLabel(d["time"], d["scene_type"], d["description"])
                  for d in s]
        profile = detect_content([lab.description for lab in labels])
        return Understanding(bundle, labels,
                             visual_keep_series(labels, bundle.times),
                             profile, any(a > 0.0 for a in bundle.audio))

    und = understand_video(video_path, vlm_frames=vlm_frames,
                           vlm_backend=vlm_backend, progress=progress)
    cache.put(kb, und.bundle.to_dict())
    cache.put(ks, [lab.to_dict() for lab in und.labels])
    return und


def _cached_transcript(
    video_path: str, cache: AnalysisCache | None, want_words: bool,
    language: str | None, progress: Callable[[str], None],
) -> list:
    key = None
    if cache is not None:
        key = content_key(video_path, {"stage": "transcript",
                                       "v": ANALYSIS_VERSION,
                                       "words": want_words,
                                       "language": language})
        hit = cache.get(key)
        if hit is not None:
            progress("Reusing cached transcript…")
            return [
                SpeechSegment(d["start"], d["end"], d["text"],
                              tuple(Word(w["start"], w["end"], w["text"])
                                    for w in d.get("words", [])))
                for d in hit
            ]
    progress("Transcribing dialogue…" + (" (word timings)" if want_words else ""))
    transcript = transcribe(video_path, word_timestamps=want_words,
                            language=language)
    if cache is not None and key is not None:
        cache.put(key, [s.to_dict() for s in transcript])
    return transcript


def _needs_transcript(req: JobRequest, preset: dict, has_audio: bool) -> bool:
    if not has_audio:
        return False
    if req.captions in ("plain", "karaoke"):
        return True
    return bool(preset["keep_dialogue"] or req.shorts)


def _render_long_edit(
    video_path: str, out_path: str, und: Understanding, req: JobRequest,
    transcript: list, library_root, progress: Callable[[str], None],
    prov_log: str | None = None,
) -> dict:
    """The condensed full edit — the autonomous editor's deliverable, but
    shaped by the request (intensity, aspect, caption style)."""
    preset = EDITING_PRESETS[und.profile.preset]
    target_keep = _KEEP_BY_INTENSITY.get(req.intensity, preset["target_keep"])

    progress("Deciding what to keep and cut…")
    if und.profile.preset == "talking" and transcript:
        # Speech-driven edit: keep what was said, cut the dead air.
        plan = pause_cut_plan(transcript, und.bundle.duration,
                              min_pause=preset["min_cut"])
    else:
        speech = (presence_series(transcript, und.bundle.times)
                  if transcript and preset["keep_dialogue"] else None)
        plan = Condenser(target_keep=target_keep,
                         min_cut_seconds=preset["min_cut"]).plan(
            und.bundle, speech=speech, visual_keep=und.visual)
    if not plan.segments:
        raise RuntimeError("nothing clearly worth keeping was found")

    karaoke = req.captions in ("auto", "karaoke") and any(
        getattr(s, "words", ()) for s in transcript)
    use_subs = bool(transcript) and req.captions != "none" and preset["keep_dialogue"]

    focus = None
    if req.aspect:
        progress("Finding the action's focus for the reframe…")
        focus = cut_focus_centers(
            video_path, [(s.span.start, s.span.end) for s in plan.segments])

    rationale = [
        f"Recognized {und.profile.label} → '{und.profile.preset}' preset: "
        f"{preset['note']}.",
        f"Kept {plan.keep_ratio:.0%} of the video across {len(plan.segments)} "
        f"coherent segments (never cutting mid-action).",
    ]
    if req.intensity in _KEEP_BY_INTENSITY:
        rationale.append(f"Cut intensity set by the creator: {req.intensity}.")
    if use_subs:
        rationale.append("Karaoke captions from the spoken dialogue."
                         if karaoke else
                         "Burned the spoken dialogue as subtitles.")
    if req.aspect:
        rationale.append(f"Reframed to {req.aspect} following the action.")

    music_track, music_asset = _pick_music(
        library_root, preset.get("music") if req.music else None, und.has_audio)
    if music_track:
        rationale.append(f"Music bed from the K Library "
                         f"({music_asset.path.name}), mixed under the audio.")

    program = compose_program(
        plan, transcript=transcript if use_subs else None,
        subtitles=use_subs and not karaoke, captions=use_subs and karaoke,
        zoom=bool(preset["zoom"]), music_track=music_track,
        height=req.height, aspect=req.aspect, focus_x=focus,
        rationale=rationale)

    progress(f"Rendering the full edit at {req.height}p…")
    execute_program(video_path, program, out_path, has_audio=und.has_audio)
    report = validate_render(out_path, program, has_audio=und.has_audio)
    if not report.ok:
        raise RuntimeError("render validation failed: " + "; ".join(report.issues))

    if prov_log:
        record_render(prov_log, source_video=video_path, output_path=out_path,
                      program=program.to_dict(),
                      assets=[music_track] if music_track else [])

    return {
        "kind": "long_edit", "file": Path(out_path).name,
        "original_duration": plan.original_duration,
        "kept_duration": plan.kept_duration,
        "keep_ratio": plan.keep_ratio,
        "segments": len(plan.segments),
        "subtitles": len(program.subtitles), "captions": len(program.captions),
        "zooms": len(program.zooms), "music": len(program.music),
        "aspect": req.aspect, "rationale": program.rationale,
        "validation": report.to_dict(),
    }


def run_job(
    video_path: str,
    out_dir: str,
    req: JobRequest | None = None,
    *,
    library_root=None,
    vlm_backend=None,
    vlm_frames: int = 14,
    understanding: Understanding | None = None,
    cache_dir: str | None = None,
    progress: Callable[[str], None] = lambda s: None,
) -> dict:
    """Produce every requested deliverable from one shared analysis.

    Returns the manifest (also written to ``out_dir/manifest.json``):
    the understanding, the request, and one entry per deliverable. Passing
    ``understanding`` skips re-analysis for this call; ``cache_dir`` persists
    the analysis so *future* runs on the same video skip it too.
    """
    req = req or JobRequest()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cache = AnalysisCache(cache_dir) if cache_dir else None

    if understanding is not None:
        und = understanding
    elif cache is not None:
        und = _cached_understanding(video_path, cache, vlm_frames,
                                    vlm_backend, progress)
    else:
        und = understand_video(video_path, vlm_frames=vlm_frames,
                               vlm_backend=vlm_backend, progress=progress)
    preset = EDITING_PRESETS[und.profile.preset]

    transcript: list = []
    if _needs_transcript(req, preset, und.has_audio):
        want_words = req.captions in ("auto", "karaoke")
        transcript = _cached_transcript(video_path, cache, want_words,
                                        req.language, progress)

        # With the transcript in hand, the Director can recognize *talking*
        # content (vlog/podcast) — an edit driven by speech, not by action.
        if transcript and und.bundle.duration > 0:
            ratio = sum(s.end - s.start for s in transcript) / und.bundle.duration
            better = detect_content([lab.description for lab in und.labels],
                                    speech_ratio=ratio)
            if better.preset != und.profile.preset:
                progress(f"Re-recognized as {better.label} "
                         f"({ratio:.0%} of it is speech).")
                und.profile = better
                preset = EDITING_PRESETS[better.preset]

    prov_log = str(out / "provenance.jsonl")
    deliverables: list[dict] = []
    if req.long_edit:
        deliverables.append(_render_long_edit(
            video_path, str(out / "long_edit.mp4"), und, req, transcript,
            library_root, progress, prov_log=prov_log))

    if req.shorts > 0:
        spec = ShortSpec(min_len=req.min_short_len, max_len=req.max_short_len,
                         subtitles=req.captions != "none",
                         karaoke=req.captions in ("auto", "karaoke"),
                         height=1080)
        shorts_manifest = make_shorts(
            video_path, str(out), top_n=req.shorts, spec=spec,
            transcript=transcript, bundle=und.bundle, progress=progress,
            provenance_log=prov_log)
        for s in shorts_manifest["shorts"]:
            deliverables.append({"kind": "short", **s})

    manifest = {
        "video": video_path,
        "request": req.to_dict(),
        "understanding": {
            "genre": und.profile.genre, "label": und.profile.label,
            "preset": und.profile.preset, "preset_note": preset["note"],
            "scenes": [lab.to_dict() for lab in und.labels],
        },
        "deliverables": deliverables,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2),
                                       encoding="utf-8")
    progress("done")
    return manifest

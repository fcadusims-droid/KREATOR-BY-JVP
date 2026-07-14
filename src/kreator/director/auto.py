"""Autonomous edit — the full pipeline with zero user input.

Kreator looks at the video, works out what kind of gameplay it is, picks an
editing preset for that genre, and produces the edit. This is what the app runs
when there are no options: upload → understand → edit → download.

Nothing generative is added: the output is only the creator's own footage,
cut and reassembled. (See ``docs/not-generative.md``.)
"""

from __future__ import annotations

from typing import Callable

from ..dsl import compose_program, execute_program
from ..editor import Condenser
from ..library import KLibrary
from ..signal_layer import analyze_video
from ..speech import presence_series, transcribe
from ..validator import validate_render
from ..vlm import label_keyframes, select_keyframes, visual_keep_series
from ..vlm.backends import LocalVLMBackend
from .content import EDITING_PRESETS, detect_content


def _pick_music(library_root, mood, has_audio):
    """Resolve a K Library music track for ``mood``, or ``None``. Returns
    ``(track_path, asset)``. No library / no match / silent video → no music."""
    if not (library_root and mood and has_audio):
        return None, None
    asset = KLibrary(library_root).find_music(mood)
    return (str(asset.path), asset) if asset else (None, None)


def autonomous_edit(
    video_path: str,
    out_path: str,
    *,
    vlm_frames: int = 14,
    height: int = 720,
    library_root=None,
    progress: Callable[[str], None] = lambda s: None,
    vlm_backend=None,
) -> dict:
    """Run the whole autonomous pipeline and render the edit.

    Returns a summary dict (detected genre, preset, durations, scene labels).
    ``progress`` is called with a short human status at each stage.
    ``library_root``, if given, is a K Library directory the Director may pull a
    background music bed from (only real, free-to-use files the user added).
    """
    progress("Analyzing video (motion, audio, scenes)…")
    bundle = analyze_video(video_path)
    has_audio = any(a > 0.0 for a in bundle.audio)

    progress("Understanding the scenes (local VLM)…")
    backend = vlm_backend or LocalVLMBackend()
    keyframes = select_keyframes(bundle, max_frames=vlm_frames)
    labels = label_keyframes(video_path, keyframes, backend)
    visual = visual_keep_series(labels, bundle.times)

    profile = detect_content([lab.description for lab in labels])
    preset = EDITING_PRESETS[profile.preset]
    progress(f"Recognized: {profile.label} → editing as '{profile.preset}'.")

    segs = []
    speech = None
    if preset["keep_dialogue"] and has_audio:
        progress("Transcribing dialogue so story/mission talk is kept…")
        segs = transcribe(video_path)
        speech = presence_series(segs, bundle.times)

    progress("Deciding what to keep and cut…")
    plan = Condenser(
        target_keep=preset["target_keep"],
        min_cut_seconds=preset["min_cut"],
    ).plan(bundle, speech=speech, visual_keep=visual)
    if not plan.segments:
        raise RuntimeError("nothing clearly worth keeping was found")

    # The Director's decision log — the "why" carried into the plan.
    use_subs = bool(preset["keep_dialogue"] and segs)
    rationale = [
        f"Recognized {profile.label} → '{profile.preset}' preset: {preset['note']}.",
        f"Kept {plan.keep_ratio:.0%} of the video across {len(plan.segments)} "
        f"coherent segments (never cutting mid-action).",
    ]
    if use_subs:
        rationale.append("Burned the spoken dialogue as subtitles so the "
                         "story/mission stays followable.")
    if preset["zoom"]:
        rationale.append("Added subtle punch-ins on the most intense moments.")

    # A background music bed from the K Library, if the preset wants one and the
    # library actually has a matching (real, free-to-use) track.
    music_track, music_asset = _pick_music(
        library_root, preset.get("music"), has_audio)
    if music_track:
        rationale.append(
            f"Laid a '{preset['music']}' music bed ({music_asset.path.name}) "
            "under the edit from the K Library, mixed below the game audio.")

    # Compose the edit as an operations program: cut spine + subtitles (the
    # creator's own spoken words) + zoom punch-ins + music bed, each justified.
    program = compose_program(
        plan, transcript=segs,
        subtitles=use_subs,
        zoom=bool(preset["zoom"]),
        music_track=music_track,
        height=height,
        rationale=rationale,
    )

    progress(f"Rendering the edited video at {height}p…")
    execute_program(video_path, program, out_path, has_audio=has_audio)

    progress("Validating the finished video…")
    report = validate_render(out_path, program, has_audio=has_audio)
    if not report.ok:
        raise RuntimeError("render validation failed: " + "; ".join(report.issues))

    return {
        "genre": profile.genre,
        "label": profile.label,
        "preset": profile.preset,
        "preset_note": preset["note"],
        "tags": profile.tags,
        "original_duration": plan.original_duration,
        "kept_duration": plan.kept_duration,
        "keep_ratio": plan.keep_ratio,
        "segments": len(plan.segments),
        "subtitles": len(program.subtitles),
        "zooms": len(program.zooms),
        "music": len(program.music),
        "rationale": program.rationale,
        "program": program.to_dict(),
        "validation": report.to_dict(),
        "scenes": [lab.to_dict() for lab in labels],
        "out": out_path,
    }

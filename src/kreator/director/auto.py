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
from ..signal_layer import analyze_video
from ..speech import presence_series, transcribe
from ..vlm import label_keyframes, select_keyframes, visual_keep_series
from ..vlm.backends import LocalVLMBackend
from .content import EDITING_PRESETS, detect_content


def autonomous_edit(
    video_path: str,
    out_path: str,
    *,
    vlm_frames: int = 14,
    height: int = 720,
    progress: Callable[[str], None] = lambda s: None,
    vlm_backend=None,
) -> dict:
    """Run the whole autonomous pipeline and render the edit.

    Returns a summary dict (detected genre, preset, durations, scene labels).
    ``progress`` is called with a short human status at each stage.
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

    # Compose the edit as an operations program: the cut spine plus subtitles
    # (the creator's own spoken words) where the preset keeps dialogue — which
    # also helps a viewer follow a mission, the one real editing complaint we
    # found in the wild.
    program = compose_program(
        plan, transcript=segs,
        subtitles=bool(preset["keep_dialogue"] and segs),
        height=height,
    )

    progress(f"Rendering the edited video at {height}p…")
    execute_program(video_path, program, out_path, has_audio=has_audio)

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
        "scenes": [lab.to_dict() for lab in labels],
        "out": out_path,
    }

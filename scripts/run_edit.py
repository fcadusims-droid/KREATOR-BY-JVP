#!/usr/bin/env python3
"""K Editor: condense a long unedited gameplay into its interesting parts.

    Signal Layer → interest curve → Condenser (keep/cut plan) → FFmpeg render

Takes a long, no-commentary gameplay and produces a shorter edited video that
keeps the action and cuts the boring stretches, plus a JSON plan describing
exactly what was kept and why.

Usage:
    python scripts/run_edit.py --video data/videos/gta5_freeroam.mp4 \
        --target-keep 0.35 -o out/gta5_freeroam.edited.mp4
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.editor import Condenser, render_segments  # noqa: E402
from kreator.signal_layer import analyze_video  # noqa: E402
from kreator.speech import presence_series, transcribe  # noqa: E402
from kreator.types import format_tc  # noqa: E402
from kreator.vlm import (  # noqa: E402
    LocalVLMBackend, label_keyframes, select_keyframes, visual_keep_series,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Kreator K Editor: condense a video.")
    ap.add_argument("--video", required=True, help="path to the source video")
    ap.add_argument("--bundle", default=None,
                    help="cached bundle JSON (from analyze_cache.py) — skips "
                         "re-analysis and reuses its baked-in speech")
    ap.add_argument("--target-keep", type=float, default=0.35,
                    help="fraction of the most-active video to keep (0..1)")
    ap.add_argument("--pad", type=float, default=1.0,
                    help="context seconds padded around each kept region")
    ap.add_argument("--min-cut", type=float, default=3.0,
                    help="never cut a boring gap shorter than this (seconds)")
    ap.add_argument("--speech", action="store_true",
                    help="transcribe dialogue (CPU Whisper) and keep talky moments")
    ap.add_argument("--captions", action="store_true",
                    help="with --speech + --aspect: burn word-by-word karaoke "
                         "captions instead of plain subtitles")
    ap.add_argument("--whisper-model", default="base",
                    help="faster-whisper model size (tiny/base/small)")
    ap.add_argument("--vlm", action="store_true",
                    help="describe sampled keyframes with a local CPU VLM and keep "
                         "scenic/dialogue/action scenes (slow, offline, no GPU)")
    ap.add_argument("--vlm-frames", type=int, default=20,
                    help="how many keyframes the VLM looks at")
    ap.add_argument("--height", type=int, default=None,
                    choices=[480, 720, 1080],
                    help="output resolution height (480/720/1080); default keeps source")
    ap.add_argument("--aspect", default=None, choices=["9:16", "1:1", "16:9"],
                    help="reframe the edit to this aspect (9:16 = vertical "
                         "Shorts); default keeps the source aspect")
    ap.add_argument("--reframe", default="crop", choices=["crop", "pad"],
                    help="with --aspect: 'crop' follows the action inside a "
                         "real-pixel window, 'pad' fits the frame with bars")
    ap.add_argument("-o", "--out", default="out/edited.mp4",
                    help="edited video output path")
    ap.add_argument("--plan-out", default=None, help="edit-plan JSON output path")
    ap.add_argument("--no-render", action="store_true",
                    help="compute the plan only, skip rendering")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    if args.bundle:
        from kreator.types import SignalBundle
        print(f"Loading cached bundle {args.bundle} …")
        bundle = SignalBundle.from_dict(json.loads(Path(args.bundle).read_text()))
    else:
        print(f"Analyzing {args.video} …")
        bundle = analyze_video(args.video, verbose=args.verbose)
    has_audio = any(a > 0.0 for a in bundle.audio)

    # A cached bundle already has speech presence baked into bundle.speech.
    speech = bundle.speech if (args.bundle and any(bundle.speech)) else None
    segments = []
    if args.speech and not args.bundle:
        print("Transcribing dialogue (Whisper, CPU)…")
        segments = transcribe(args.video, model_size=args.whisper_model,
                              word_timestamps=args.captions,
                              verbose=args.verbose)
        speech = presence_series(segments, bundle.times)
        talk_time = sum(s.end - s.start for s in segments)
        print(f"  {len(segments)} speech segments, {format_tc(talk_time)} of dialogue")
        transcript_out = str(Path(args.out).with_suffix(".transcript.json"))
        Path(transcript_out).write_text(
            json.dumps([s.to_dict() for s in segments], indent=2), encoding="utf-8")
        print(f"  wrote transcript: {transcript_out}")

    visual_keep = None
    if args.vlm:
        keyframes = select_keyframes(bundle, max_frames=args.vlm_frames)
        print(f"Describing {len(keyframes)} keyframes with a local VLM (CPU, slow)…")
        labels = label_keyframes(args.video, keyframes, LocalVLMBackend(),
                                 verbose=args.verbose)
        visual_keep = visual_keep_series(labels, bundle.times)
        from collections import Counter
        kinds = Counter(lab.scene_type for lab in labels)
        print(f"  scene types: {dict(kinds)}")
        labels_out = str(Path(args.out).with_suffix(".scenes.json"))
        Path(labels_out).write_text(
            json.dumps([lab.to_dict() for lab in labels], indent=2), encoding="utf-8")
        print(f"  wrote scene labels: {labels_out}")

    condenser = Condenser(
        target_keep=args.target_keep,
        pad_seconds=args.pad,
        min_cut_seconds=args.min_cut,
    )
    plan = condenser.plan(bundle, speech=speech, visual_keep=visual_keep)

    print(f"\nOriginal: {format_tc(plan.original_duration)}  →  "
          f"Edited: {format_tc(plan.kept_duration)}  "
          f"({plan.keep_ratio:.0%} kept, {len(plan.segments)} segments, "
          f"audio={'yes' if has_audio else 'no'})")
    for i, seg in enumerate(plan.segments, 1):
        print(f"  keep {i:2d}: {seg.span}  (interest {seg.mean_interest:.2f})")

    plan_out = args.plan_out or str(Path(args.out).with_suffix(".plan.json"))
    Path(plan_out).parent.mkdir(parents=True, exist_ok=True)
    Path(plan_out).write_text(json.dumps(plan.to_dict(), indent=2), encoding="utf-8")
    print(f"\nWrote plan: {plan_out}")

    if args.no_render:
        return 0
    if not plan.segments:
        print("No segments to render — try a higher --target-keep.")
        return 1

    if args.aspect:
        # Reframed renders go through the DSL: cut spine + Reframe op, with a
        # per-cut horizontal focus so the crop follows the action.
        from kreator.dsl import compose_program, execute_program
        from kreator.validator import validate_render

        focus = None
        if args.reframe == "crop":
            from kreator.reframe import cut_focus_centers
            print("Finding the action's horizontal focus per kept segment…")
            focus = cut_focus_centers(
                args.video, [(s.span.start, s.span.end) for s in plan.segments])
        program = compose_program(
            plan, transcript=segments, subtitles=bool(segments),
            captions=args.captions,
            height=args.height, aspect=args.aspect,
            reframe_strategy=args.reframe, focus_x=focus,
            rationale=[f"reframed to {args.aspect} via --aspect"])
        print(f"Rendering {args.aspect} video (FFmpeg, {args.reframe})…")
        out = execute_program(args.video, program, args.out,
                              has_audio=has_audio, verbose=args.verbose)
        report = validate_render(out, program, has_audio=has_audio)
        if not report.ok:
            print("Validation FAILED: " + "; ".join(report.issues))
            return 1
        print(f"Wrote edited video: {out} (validated)")
        return 0

    print("Rendering edited video (FFmpeg re-encode of kept parts)…")
    out = render_segments(args.video, plan, args.out, has_audio=has_audio,
                          height=args.height, verbose=args.verbose)
    print(f"Wrote edited video: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

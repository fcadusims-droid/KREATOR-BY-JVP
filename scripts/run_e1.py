#!/usr/bin/env python3
"""Run the E1 slice end-to-end: video → candidate ranking (JSON).

    Signal Layer → K Analyst (Evidence) → Planner / K Clipper → ranking.json

This is the *entire* machine side of E1. There is deliberately no editing,
captioning, thumbnailing, or publishing here — none of it changes whether the
ranking is good, and E1 exists precisely to answer that before any of it gets
built.

Usage:
    # Real gameplay video (needs opencv + a decoder installed):
    python scripts/run_e1.py --video path/to/gameplay.mp4 --top-n 5 -o out/ranking.json

    # No video? Run the built-in synthetic demo to see the ranking format:
    python scripts/run_e1.py --demo -o out/ranking.demo.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make ``src/`` importable without an install step.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.evidence import KAnalyst  # noqa: E402
from kreator.planner import KClipper, ScoringProfile  # noqa: E402
from kreator.signal_layer import analyze_video, synthetic_bundle  # noqa: E402


def _demo_bundle():
    """A reproducible 3-minute 'session' with a few planted highlights."""
    return synthetic_bundle(
        duration=180.0,
        peaks=[
            {"time": 22.0, "motion": 0.6, "audio": 0.5, "speech": 1.0, "width": 4.0},
            {"time": 61.0, "motion": 0.95, "audio": 0.9, "speech": 1.0, "width": 3.0},
            {"time": 95.0, "motion": 0.4, "audio": 0.35, "speech": 0.0, "width": 5.0},
            {"time": 132.0, "motion": 0.88, "audio": 0.7, "speech": 1.0, "width": 3.0},
            {"time": 160.0, "motion": 0.55, "audio": 0.95, "speech": 1.0, "width": 2.5},
        ],
        scene_cuts=[20.0, 60.0, 130.0, 159.0],
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Kreator E1: rank clip candidates.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--video", help="path to a real gameplay video file")
    src.add_argument("--demo", action="store_true", help="run a synthetic demo")
    ap.add_argument("--top-n", type=int, default=5, help="candidates to return")
    ap.add_argument("--profile", default="default-gameplay", help="scoring profile name")
    ap.add_argument("-o", "--out", default="ranking.json", help="output JSON path")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    if args.demo:
        bundle = _demo_bundle()
        video_path = None
        source = "demo"
    else:
        bundle = analyze_video(args.video, verbose=args.verbose)
        video_path = args.video
        source = args.video

    analyst = KAnalyst()  # signal-only; pass vlm=/asr= backends on a GPU box
    evidences = analyst.analyze(bundle, video_path=video_path)

    clipper = KClipper(ScoringProfile(name=args.profile))
    candidates = clipper.rank(evidences, top_n=args.top_n)

    result = {
        "source": source,
        "duration": round(bundle.duration, 2),
        "n_events": len(bundle.events),
        "n_evidence": len(evidences),
        "analyst_source": analyst.source_tag,
        "profile": {"name": clipper.profile.name, "version": clipper.profile.version},
        "candidates": [c.to_dict() for c in candidates],
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"Analyzed {source}: {len(bundle.events)} events → "
          f"{len(evidences)} evidence → top {len(candidates)} candidates")
    for c in candidates:
        print(f"  #{c.rank}  {c.span}  score={c.score:.3f}  {c.rationale}")
    print(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""K Shorts: rank a video's best moments and render each as a vertical Short.

    Signal Layer → K Analyst → K Clipper (rank) → fit → reframe 9:16 → render

Usage:
    python scripts/make_shorts.py --video data/videos/clip.mp4 --top-n 5 -o out/shorts
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.shorts import ShortSpec, make_shorts  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Kreator: render the top moments as Shorts.")
    ap.add_argument("--video", required=True, help="path to the source video")
    ap.add_argument("--top-n", type=int, default=5, help="how many Shorts to make")
    ap.add_argument("--min-len", type=float, default=15.0, help="minimum Short length (s)")
    ap.add_argument("--max-len", type=float, default=60.0, help="maximum Short length (s)")
    ap.add_argument("--aspect", default="9:16", choices=["9:16", "1:1", "16:9", "source"],
                    help="output aspect ('source' keeps the original)")
    ap.add_argument("--height", type=int, default=1080, choices=[480, 720, 1080])
    ap.add_argument("--speech", action="store_true",
                    help="transcribe dialogue and burn it as captions")
    ap.add_argument("--whisper-model", default="base")
    ap.add_argument("-o", "--out", default="out/shorts", help="output directory")
    args = ap.parse_args()

    transcript = None
    if args.speech:
        from kreator.speech import transcribe
        print("Transcribing dialogue with word timings (Whisper, CPU)…")
        transcript = transcribe(args.video, model_size=args.whisper_model,
                                word_timestamps=True)

    spec = ShortSpec(min_len=args.min_len, max_len=args.max_len,
                     aspect=None if args.aspect == "source" else args.aspect,
                     height=args.height, subtitles=bool(transcript))
    manifest = make_shorts(args.video, args.out, top_n=args.top_n, spec=spec,
                           transcript=transcript, progress=print)

    print(f"\n{len(manifest['shorts'])} Shorts in {args.out}:")
    for s in manifest["shorts"]:
        ok = "✓" if s["validation"]["ok"] else "✗ " + "; ".join(s["validation"]["issues"])
        print(f"  {s['file']}  {s['duration']}s  [{ok}]  {s['rationale']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

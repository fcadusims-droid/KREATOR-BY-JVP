#!/usr/bin/env python3
"""Analyze a video once and cache its SignalBundle, so parameter tuning can
iterate on the (instant) condenser without re-decoding the video each time.

    python scripts/analyze_cache.py --video data/videos/x.mp4 --speech

Writes out/cache/<name>.bundle.json (and, with --speech, the speech presence
baked into the bundle plus a <name>.transcript.json artifact).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.signal_layer import analyze_video  # noqa: E402
from kreator.speech import presence_series, transcribe  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Cache a video's SignalBundle.")
    ap.add_argument("--video", required=True)
    ap.add_argument("--speech", action="store_true", help="also transcribe dialogue")
    ap.add_argument("--whisper-model", default="base")
    ap.add_argument("--cache-dir", default="out/cache")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    name = Path(args.video).stem
    print(f"[{name}] analyzing…")
    bundle = analyze_video(args.video, verbose=args.verbose)

    if args.speech:
        print(f"[{name}] transcribing…")
        segments = transcribe(args.video, model_size=args.whisper_model)
        bundle.speech = presence_series(segments, bundle.times)
        Path(args.cache_dir).mkdir(parents=True, exist_ok=True)
        (Path(args.cache_dir) / f"{name}.transcript.json").write_text(
            json.dumps([s.to_dict() for s in segments], indent=2), encoding="utf-8")
        print(f"[{name}] {len(segments)} speech segments")

    Path(args.cache_dir).mkdir(parents=True, exist_ok=True)
    out = Path(args.cache_dir) / f"{name}.bundle.json"
    out.write_text(json.dumps(bundle.to_dict()), encoding="utf-8")
    print(f"[{name}] cached → {out}  ({bundle.duration:.0f}s, {len(bundle.events)} events)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

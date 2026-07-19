#!/usr/bin/env python3
"""One upload → several deliverables (full edit + Shorts), one analysis pass.

    python scripts/run_job.py --video clip.mp4 --shorts 3 -o out/job
    python scripts/run_job.py --video clip.mp4 \
        --instruction "make 3 shorts of ~30 seconds with animated captions"

The --instruction sentence is read by the deterministic conversational parser;
explicit flags override whatever it understood.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.director import JobRequest, parse_instruction, run_job  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Kreator: multi-deliverable edit job.")
    ap.add_argument("--video", required=True)
    ap.add_argument("--instruction", default=None,
                    help="plain-language request (en/pt), e.g. "
                         "'3 shorts of ~30s with animated captions, no music'")
    ap.add_argument("--no-long-edit", action="store_true")
    ap.add_argument("--shorts", type=int, default=None)
    ap.add_argument("--aspect", default=None, choices=["9:16", "1:1"])
    ap.add_argument("--captions", default=None,
                    choices=["auto", "none", "plain", "karaoke"])
    ap.add_argument("--template", default=None,
                    choices=["auto", "simple", "vlog", "tutorial",
                             "cinematic", "montage"],
                    help="editing doctrine (simple → cinematic); fills the "
                         "knobs you don't set explicitly")
    ap.add_argument("--intensity", default=None,
                    choices=["auto", "light", "medium", "heavy"])
    ap.add_argument("--language", default=None,
                    help="spoken-language ISO code for transcription/captions "
                         "(e.g. en, pt, es); default auto-detects")
    ap.add_argument("--height", type=int, default=None, choices=[480, 720, 1080])
    ap.add_argument("--library", default=None, help="K Library directory")
    ap.add_argument("--cache", default=None, help="analysis cache directory")
    ap.add_argument("-o", "--out", default="out/job", help="output directory")
    args = ap.parse_args()

    req = parse_instruction(args.instruction) if args.instruction else JobRequest()
    if args.template:
        req.template = args.template
    if args.no_long_edit:
        req.long_edit = False
    if args.shorts is not None:
        req.shorts = args.shorts
    if args.aspect:
        req.aspect = args.aspect
    if args.captions:
        req.captions = args.captions
    if args.intensity:
        req.intensity = args.intensity
    if args.language:
        req.language = args.language
    if args.height:
        req.height = args.height

    if req.notes:
        print("Understood from the instruction:")
        for n in req.notes:
            print(f"  - {n}")

    manifest = run_job(args.video, args.out, req, library_root=args.library,
                       cache_dir=args.cache, progress=print)

    print(f"\n{len(manifest['deliverables'])} deliverable(s) in {args.out}:")
    for d in manifest["deliverables"]:
        ok = "✓" if d["validation"]["ok"] else "✗"
        print(f"  [{ok}] {d['kind']}: {d['file']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

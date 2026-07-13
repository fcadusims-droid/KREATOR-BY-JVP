#!/usr/bin/env python3
"""Convert plain-text moment notes into the *.truth.json files E1 expects.

You don't need to write JSON by hand. Watch the video, and every time you
see a moment you'd cut into a Short, jot down its start-end time. Then run
this script to turn that list into the exact file eval_e1.py needs, in the
exact place it looks for it.

--- How to note down moments ---
One moment per line, in the order you'd rank them (best first is nice but
not required). Times can be mm:ss or plain seconds. Use a dash between
start and end. Blank lines and lines starting with # are ignored.

Example (save as picks_gameplay_01.txt):

    # gameplay_01 — my picks, best first
    00:58-01:06
    02:09-02:17
    05:41-05:52

--- Usage ---
    python scripts/make_truth.py gameplay_01.mp4 picks_gameplay_01.txt

This writes BOTH of the following (identical content, two locations),
because the batch evaluator looks in out/ and the single-pair example in
the README points at data/labels/ — writing both means either workflow
works without you having to remember which one:

    data/labels/gameplay_01.truth.json
    out/gameplay_01.truth.json

Then, after you've run run_e1.py to produce out/gameplay_01.ranking.json
for the same video, either of these works:

    python scripts/eval_e1.py --batch out/
    python scripts/eval_e1.py --ranking out/gameplay_01.ranking.json \\
                               --truth   data/labels/gameplay_01.truth.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def _parse_time(token: str) -> float:
    token = token.strip()
    if ":" in token:
        parts = token.split(":")
        if len(parts) == 2:
            m, s = parts
            return int(m) * 60 + float(s)
        if len(parts) == 3:
            h, m, s = parts
            return int(h) * 3600 + int(m) * 60 + float(s)
        raise ValueError(f"can't parse time '{token}'")
    return float(token)


def parse_picks(text: str) -> list[dict]:
    picks = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^(.+?)\s*-\s*(.+)$", line)
        if not m:
            raise ValueError(f"line {lineno}: expected 'start-end', got: {raw!r}")
        start = _parse_time(m.group(1))
        end = _parse_time(m.group(2))
        if end <= start:
            raise ValueError(f"line {lineno}: end must be after start: {raw!r}")
        picks.append({"start": round(start, 2), "end": round(end, 2)})
    return picks


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", help="video filename as referenced in the truth file, e.g. gameplay_01.mp4")
    ap.add_argument("picks_file", help="text file with one 'start-end' moment per line")
    ap.add_argument("--repo-root", default=None,
                    help="path to the repo root (default: auto-detected from this script's location)")
    args = ap.parse_args()

    text = Path(args.picks_file).read_text(encoding="utf-8")
    try:
        picks = parse_picks(text)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if not picks:
        print("error: no picks found in the file — did you forget the '-' between start and end?", file=sys.stderr)
        return 1

    video_stem = Path(args.video).stem
    payload = {"video": args.video, "picks": picks}

    root = Path(args.repo_root) if args.repo_root else Path(__file__).resolve().parent.parent
    targets = [
        root / "data" / "labels" / f"{video_stem}.truth.json",
        root / "out" / f"{video_stem}.truth.json",
    ]
    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {target}  ({len(picks)} picks)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

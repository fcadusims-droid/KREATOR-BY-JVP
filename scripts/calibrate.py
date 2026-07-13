#!/usr/bin/env python3
"""Sweep K Editor condenser parameters over cached bundles and report how the
segmentation behaves — so tuning is driven by numbers across several videos,
not one eyeballed render.

Needs bundles from analyze_cache.py in --cache-dir. Runs the (instant)
condenser only — no video decoding.

    python scripts/calibrate.py --cache-dir out/cache
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.editor import Condenser  # noqa: E402
from kreator.types import SignalBundle  # noqa: E402


def _load(cache_dir: str) -> dict[str, SignalBundle]:
    out = {}
    for f in sorted(Path(cache_dir).glob("*.bundle.json")):
        out[f.name.replace(".bundle.json", "")] = SignalBundle.from_dict(
            json.loads(f.read_text()))
    return out


def _metrics(plan) -> dict:
    lengths = [s.span.duration for s in plan.segments]
    return {
        "keep": plan.keep_ratio,
        "n": len(plan.segments),
        "mean_len": (sum(lengths) / len(lengths)) if lengths else 0.0,
        "min_len": min(lengths) if lengths else 0.0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Calibrate K Editor params.")
    ap.add_argument("--cache-dir", default="out/cache")
    ap.add_argument("--target-keep", type=float, default=0.40)
    args = ap.parse_args()

    bundles = _load(args.cache_dir)
    if not bundles:
        print(f"No cached bundles in {args.cache_dir}. Run analyze_cache.py first.")
        return 1
    print(f"Loaded {len(bundles)} bundle(s): {', '.join(bundles)}\n")

    # Sweep the coherence-relevant knobs: envelope window and hysteresis exit.
    episode_grid = [8.0, 12.0, 16.0, 20.0]
    exit_grid = [0.45, 0.55, 0.7]

    print(f"target_keep={args.target_keep}  (mean over {len(bundles)} videos)")
    print(f"{'episode_s':>9} {'exit':>5} | {'keep%':>6} {'segs':>5} "
          f"{'mean_len':>9} {'min_len':>8}")
    print("-" * 52)
    for es in episode_grid:
        for ex in exit_grid:
            rows = []
            for b in bundles.values():
                cond = Condenser(target_keep=args.target_keep, episode_seconds=es,
                                 exit_ratio=ex, min_cut_seconds=4.0, pad_seconds=1.5)
                rows.append(_metrics(cond.plan(b, speech=b.speech or None)))
            keep = sum(r["keep"] for r in rows) / len(rows)
            nseg = sum(r["n"] for r in rows) / len(rows)
            mlen = sum(r["mean_len"] for r in rows) / len(rows)
            minl = sum(r["min_len"] for r in rows) / len(rows)
            print(f"{es:>9.0f} {ex:>5.2f} | {keep*100:>5.0f}% {nseg:>5.1f} "
                  f"{mlen:>8.1f}s {minl:>7.1f}s")

    # Per-video detail at a sensible default.
    print("\nPer-video at episode_s=16, exit=0.55:")
    print(f"{'video':<28} {'keep%':>6} {'segs':>5} {'mean_len':>9}")
    for name, b in bundles.items():
        cond = Condenser(target_keep=args.target_keep, episode_seconds=16.0,
                         exit_ratio=0.55, min_cut_seconds=4.0, pad_seconds=1.5)
        m = _metrics(cond.plan(b, speech=b.speech or None))
        print(f"{name:<28} {m['keep']*100:>5.0f}% {m['n']:>5} {m['mean_len']:>8.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

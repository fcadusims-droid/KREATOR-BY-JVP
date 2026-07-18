#!/usr/bin/env python3
"""Train (or inspect) the creator's taste model from judged clips.

    python scripts/train_taste.py --dataset web/_work/_dataset/labels.jsonl \
        -o web/_work/_dataset/model.json

The dataset grows as a side effect of use: every 👍/👎 in the web UI appends
one labeled example. This CLI retrains on demand and prints the per-feature
weights, so the learned taste stays inspectable.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.learn import FEATURES, load_dataset, save_model, train  # noqa: E402
from kreator.learn.model import MIN_PER_CLASS  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Train the Kreator taste model.")
    ap.add_argument("--dataset", required=True, help="labels.jsonl path")
    ap.add_argument("-o", "--out", default=None,
                    help="model output path (omit for a dry run)")
    args = ap.parse_args()

    X, y = load_dataset(args.dataset)
    pos, neg = sum(1 for v in y if v == 1), sum(1 for v in y if v == 0)
    print(f"{len(y)} examples ({pos} approved, {neg} rejected)")

    model = train(X, y)
    if model is None:
        print(f"Not enough data yet — need at least {MIN_PER_CLASS} of each "
              f"class. Keep judging clips in the web UI.")
        return 1

    print(f"train accuracy: {model['train_accuracy']:.0%}\n")
    print("what the model learned (standardized weights):")
    ranked = sorted(zip(FEATURES, model["weights"]),
                    key=lambda kv: -abs(kv[1]))
    for name, w in ranked:
        bar = "+" if w > 0 else "-"
        print(f"  {name:<16} {w:+.3f}  {bar * min(int(abs(w) * 20), 30)}")

    if args.out:
        save_model(model, args.out)
        print(f"\nWrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

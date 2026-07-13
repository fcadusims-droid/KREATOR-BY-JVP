#!/usr/bin/env python3
"""Evaluate E1: does K Clipper's ranking agree with a human editor's picks?

This is the measurement that decides whether the rest of the product is worth
building. It compares a ranking produced by ``run_e1.py`` against a human
editor's chosen moments for the same video, and reports the agreement rate.

Success criterion (spec §27, E1): **majority agreement** between the system's
top-N ranking and the human editor's choices.

Ground-truth format (JSON): a list of the moments the editor actually chose,
each as a span in seconds — optionally ranked by the editor:

    {
      "video": "gameplay_01.mp4",
      "picks": [
        {"start": 58.0, "end": 66.0},
        {"start": 129.0, "end": 137.0}
      ]
    }

Usage:
    python scripts/eval_e1.py --ranking out/ranking.json --truth labels/gameplay_01.json
    python scripts/eval_e1.py --batch out/           # aggregate over many pairs
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _iou(a: dict, b: dict) -> float:
    """Intersection-over-union of two [start, end] spans."""
    inter = max(0.0, min(a["end"], b["end"]) - max(a["start"], b["start"]))
    union = (a["end"] - a["start"]) + (b["end"] - b["start"]) - inter
    return inter / union if union > 0 else 0.0


def _center_in(candidate: dict, pick: dict) -> bool:
    center = (pick["start"] + pick["end"]) / 2.0
    return candidate["start"] <= center <= candidate["end"]


def evaluate(ranking: dict, truth: dict, *, iou_threshold: float = 0.3) -> dict:
    """A human pick counts as 'found' if some system candidate overlaps it by
    IoU ≥ threshold, or contains its center. Agreement = found / total picks.

    For misses, ``closest_iou`` reports the best overlap achieved by *any*
    candidate even when it fell short of the threshold — this is what lets
    you tell a near-miss (likely an offset/boundary calibration issue) apart
    from a total miss (the ranking found nothing near the event at all).
    """
    candidates = ranking.get("candidates", [])
    picks = truth.get("picks", [])
    if not picks:
        return {"video": truth.get("video"), "picks": 0, "found": 0, "agreement": None}

    matches = []
    for pick in picks:
        best_match_iou = 0.0
        best_overlap_iou = 0.0
        best_rank = None
        for cand in candidates:
            iou = _iou(cand, pick)
            best_overlap_iou = max(iou, best_overlap_iou)
            if (iou >= iou_threshold or _center_in(cand, pick)) and iou >= best_match_iou:
                best_match_iou = max(iou, best_match_iou)
                best_rank = cand["rank"]
        matches.append({
            "pick": [pick["start"], pick["end"]],
            "found": best_rank is not None,
            "matched_rank": best_rank,
            "iou": round(best_match_iou, 3),
            "closest_iou": round(best_overlap_iou, 3),
        })

    found = sum(1 for m in matches if m["found"])
    return {
        "video": truth.get("video"),
        "picks": len(picks),
        "found": found,
        "agreement": round(found / len(picks), 3),
        "matches": matches,
    }


def _print_report(report: dict) -> None:
    agree = report["agreement"]
    verdict = "—" if agree is None else ("PASS" if agree > 0.5 else "FAIL")
    print(f"\n{report['video']}: {report['found']}/{report['picks']} human picks "
          f"found in ranking → agreement={agree} [{verdict}]")
    for m in report.get("matches", []):
        if m["found"]:
            rank = f"rank #{m['matched_rank']}"
            print(f"  ✓ pick {m['pick']}  ({rank}, IoU={m['iou']})")
        else:
            print(f"  ✗ pick {m['pick']}  (not ranked; closest candidate overlap IoU={m.get('closest_iou', 0.0)})")


def main() -> int:
    ap = argparse.ArgumentParser(description="Kreator E1 agreement evaluator.")
    ap.add_argument("--ranking", help="ranking.json from run_e1.py")
    ap.add_argument("--truth", help="human ground-truth JSON")
    ap.add_argument("--batch", help="dir with *.ranking.json + *.truth.json pairs")
    ap.add_argument("--iou", type=float, default=0.3, help="IoU match threshold")
    args = ap.parse_args()

    reports = []
    if args.batch:
        base = Path(args.batch)
        for ranking_file in sorted(base.glob("*.ranking.json")):
            truth_file = base / ranking_file.name.replace(".ranking.json", ".truth.json")
            if not truth_file.exists():
                print(f"[skip] no truth for {ranking_file.name}")
                continue
            ranking = json.loads(ranking_file.read_text())
            truth = json.loads(truth_file.read_text())
            reports.append(evaluate(ranking, truth, iou_threshold=args.iou))
    else:
        if not (args.ranking and args.truth):
            ap.error("provide --ranking and --truth, or --batch")
        ranking = json.loads(Path(args.ranking).read_text())
        truth = json.loads(Path(args.truth).read_text())
        reports.append(evaluate(ranking, truth, iou_threshold=args.iou))

    for report in reports:
        _print_report(report)

    scored = [r for r in reports if r["agreement"] is not None]
    if scored:
        mean_agreement = sum(r["agreement"] for r in scored) / len(scored)
        passing = sum(1 for r in scored if r["agreement"] > 0.5)
        print(f"\n=== E1 summary: mean agreement={mean_agreement:.3f} over "
              f"{len(scored)} video(s); {passing}/{len(scored)} pass majority ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

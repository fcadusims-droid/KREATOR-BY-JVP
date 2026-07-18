"""The labeled-example store — append-only JSONL, like provenance.

Every judged clip is one row: the feature vector Kreator computed, the human
verdict, and enough metadata to audit where the example came from. The store
grows as a *side effect of normal use* — the creator approving or rejecting
Shorts IS the labeling session.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from .features import FEATURES


def record_verdict(
    store_path: str | Path,
    features: list[float],
    label: int,
    *,
    source: str = "user",
    meta: dict | None = None,
) -> dict:
    """Append one labeled example (label: 1 approved, 0 rejected)."""
    row = {
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "features": [round(float(x), 4) for x in features],
        "feature_names": list(FEATURES),
        "label": int(label),
        "source": source,
    }
    if meta:
        row["meta"] = meta
    p = Path(store_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")
    return row


def load_dataset(store_path: str | Path) -> tuple[list[list[float]], list[int]]:
    """Read the store back as (X, y), skipping rows whose feature list no
    longer matches the current FEATURES contract."""
    p = Path(store_path)
    if not p.exists():
        return [], []
    X: list[list[float]] = []
    y: list[int] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if row.get("feature_names") != list(FEATURES):
            continue
        X.append([float(v) for v in row["features"]])
        y.append(int(row["label"]))
    return X, y

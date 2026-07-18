"""A small, deterministic logistic taste model — numpy only, CPU, seconds.

Right-sized for the data that actually exists (dozens to hundreds of the
creator's own verdicts), fully inspectable (per-feature weights are printed
by the training CLI), and honest about the cold start: it refuses to train
until both classes have enough examples, and its influence on the ranking is
bounded either way.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from .features import FEATURES, feature_vector

# Don't pretend to know taste from almost nothing.
MIN_PER_CLASS = 4
# The learned opinion can move a candidate at most this much, either way —
# the rules and signals always stay in charge of the bulk of the score.
MAX_DELTA = 0.25


def train(
    X: list[list[float]],
    y: list[int],
    *,
    l2: float = 1.0,
    lr: float = 0.5,
    epochs: int = 400,
) -> dict | None:
    """L2-regularized logistic regression by full-batch gradient descent.

    Deterministic (zero init, fixed schedule). Returns the model dict, or
    ``None`` when a class has fewer than MIN_PER_CLASS examples — the caller
    then simply keeps ranking on rules alone.
    """
    import numpy as np

    if min(sum(1 for v in y if v == 1), sum(1 for v in y if v == 0)) < MIN_PER_CLASS:
        return None
    Xa = np.asarray(X, dtype=float)
    ya = np.asarray(y, dtype=float)
    n, d = Xa.shape

    # Standardize so weights are comparable across features.
    mu = Xa.mean(axis=0)
    sd = Xa.std(axis=0)
    sd[sd == 0] = 1.0
    Xs = (Xa - mu) / sd

    w = np.zeros(d)
    b = 0.0
    for _ in range(epochs):
        p = 1.0 / (1.0 + np.exp(-(Xs @ w + b)))
        grad_w = Xs.T @ (p - ya) / n + l2 * w / n
        grad_b = float((p - ya).mean())
        w -= lr * grad_w
        b -= lr * grad_b

    p = 1.0 / (1.0 + np.exp(-(Xs @ w + b)))
    acc = float(((p >= 0.5) == (ya == 1)).mean())
    return {
        "features": list(FEATURES),
        "weights": [round(float(x), 6) for x in w],
        "bias": round(float(b), 6),
        "mean": [round(float(x), 6) for x in mu],
        "std": [round(float(x), 6) for x in sd],
        "train_accuracy": round(acc, 4),
        "n_examples": int(n),
    }


def score_features(model: dict, row: list[float]) -> float:
    """P(the creator would approve this clip), for one feature row."""
    z = model["bias"]
    for x, w, m, s in zip(row, model["weights"], model["mean"], model["std"]):
        z += w * (x - m) / (s or 1.0)
    return 1.0 / (1.0 + math.exp(-z))


def learned_adjustment(model: dict | None, signals: dict, events: list) -> tuple[float, str]:
    """The taste model's bounded vote on one clip: (delta, reason)."""
    if not model or model.get("features") != list(FEATURES):
        return 0.0, ""
    p = score_features(model, feature_vector(signals, events))
    delta = (p - 0.5) * 2.0 * MAX_DELTA
    if abs(delta) < 0.02:
        return 0.0, ""
    verb = "matches" if delta > 0 else "clashes with"
    return delta, (f"{'boost' if delta > 0 else 'demote'}: {verb} the "
                   f"creator's learned taste (p={p:.2f})")


def save_model(model: dict, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(model, indent=2), encoding="utf-8")


def load_model(path: str | Path) -> dict | None:
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

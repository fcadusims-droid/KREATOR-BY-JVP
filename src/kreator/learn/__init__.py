"""K Learn — the taste model: learn what *this* creator calls a highlight.

The rules (signals + GameSense) carry the cold start; this module carries the
convergence. Every clip the creator judges (👍/👎 in the web UI) becomes a
labeled example — features Kreator already computed, verdict from the human.
A small, deterministic logistic model trains on those examples and its
probability becomes one more *bounded* adjustment in the ranking, always
complementing the rules, never replacing the deterministic Planner (spec §4:
the model scores; the Planner decides).

Honest scale: this is a per-channel taste model over Kreator's own feature
vector — trainable on CPU from dozens of examples, refusing to train before
it has enough of each class. The path to larger public datasets
(QVHighlights, ESTA, …) is the importer + docs/training.md.
"""

from .features import FEATURES, feature_vector
from .dataset import load_dataset, record_verdict
from .model import (learned_adjustment, load_model, save_model, score_features,
                    train)

__all__ = ["FEATURES", "feature_vector", "record_verdict", "load_dataset",
           "train", "score_features", "learned_adjustment",
           "save_model", "load_model"]

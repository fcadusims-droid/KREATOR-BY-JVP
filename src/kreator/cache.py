"""Incremental analysis cache — canonical key, JSON store (Part II §7-RT).

The expensive work (decoding signals, VLM scene labels, transcription) depends
only on the *content* of the upload plus the module version and parameters —
so it is cached under ``hash(canonical_input + module_version + params)`` and
never recomputed for the same video. A second deliverable, a re-run with new
options, or a retry after a crash reuses the analysis instead of paying for it
again. Deleting the cache directory is always safe.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

# Bump when a stage's output shape or semantics change — old entries then miss.
# v2: the audio series is now decoded via ffmpeg-extracted WAV (v1 bundles can
# carry a silently empty audio track).
ANALYSIS_VERSION = "2"

_SAMPLE = 1024 * 1024  # hash the first+last MB, not the whole multi-GB file


def content_key(path: str, extra: dict | None = None) -> str:
    """A stable identity for (file content, stage, params).

    Reads only the file's size and its first/last megabyte — enough to tell
    files apart without re-reading gigabytes — and folds in ``extra``
    (stage name, module version, parameters) canonically serialized.
    """
    p = Path(path)
    h = hashlib.sha256()
    size = p.stat().st_size
    h.update(str(size).encode())
    with p.open("rb") as fh:
        h.update(fh.read(_SAMPLE))
        if size > 2 * _SAMPLE:
            fh.seek(-_SAMPLE, 2)
            h.update(fh.read(_SAMPLE))
    h.update(json.dumps(extra or {}, sort_keys=True).encode())
    return h.hexdigest()


class AnalysisCache:
    """A trivial key → JSON store on disk. Corrupt/missing entries read as a
    miss, so the cache can never make a run fail."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.root / f"{key}.json"

    def get(self, key: str):
        p = self._path(key)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None

    def put(self, key: str, value) -> None:
        self._path(key).write_text(json.dumps(value), encoding="utf-8")

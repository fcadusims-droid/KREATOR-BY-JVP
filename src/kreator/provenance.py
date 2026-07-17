"""Append-only provenance — every render traces back to real footage (§9-RT).

The strong authenticity claim ("nothing generated") is backed by *provenance*,
not by a synthetic-content classifier: each produced file gets a record saying
which upload it came from (by content hash), which operations program produced
it, and which library assets were mixed in. The log is JSONL, append-only —
records are never rewritten, matching the spec's append-only requirement.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from .cache import content_key


def record_render(
    log_path: str | Path,
    *,
    source_video: str,
    output_path: str,
    program: dict,
    assets: list[str] | None = None,
    extra: dict | None = None,
) -> dict:
    """Append one render's provenance and return the written record."""
    entry = {
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": {"path": source_video, "content": content_key(source_video)},
        "output": {"path": str(output_path),
                   "content": content_key(str(output_path))},
        "program": program,
        "assets": [
            {"path": a, "content": content_key(a)} for a in (assets or [])
        ],
    }
    if extra:
        entry.update(extra)
    p = Path(log_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    return entry


def read_log(log_path: str | Path) -> list[dict]:
    p = Path(log_path)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out

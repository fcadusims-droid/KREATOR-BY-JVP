"""Tests for the K Library asset registry — a temp dir, no real media."""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.library import KLibrary


def _make_library(tmp: Path):
    (tmp / "music").mkdir()
    (tmp / "music" / "war-theme.mp3").write_bytes(b"x")
    (tmp / "music" / "calm.mp3").write_bytes(b"x")
    (tmp / "manifest.json").write_text(json.dumps({
        "war-theme.mp3": {"kind": "music", "moods": ["tense", "war"]},
    }))


def test_lists_and_finds_music_by_mood():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        _make_library(tmp)
        lib = KLibrary(tmp)
        assert len(lib.list_music()) == 2
        # mood matches a manifest tag
        assert lib.find_music("tense").path.name == "war-theme.mp3"
        # mood matches a filename
        assert lib.find_music("calm").path.name == "calm.mp3"
        # unknown mood → falls back to some track
        assert lib.find_music("nonexistent") is not None


def test_empty_library_returns_none():
    with tempfile.TemporaryDirectory() as d:
        lib = KLibrary(d)
        assert lib.list_music() == []
        assert lib.find_music("tense") is None


if __name__ == "__main__":
    import traceback

    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except Exception:
                failures += 1
                print(f"FAIL {name}")
                traceback.print_exc()
    raise SystemExit(1 if failures else 0)

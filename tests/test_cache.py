"""Tests for the analysis cache and the provenance log."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.cache import AnalysisCache, content_key
from kreator.provenance import read_log, record_render


def _tmpfile(data: bytes) -> str:
    f = tempfile.NamedTemporaryFile(delete=False)
    f.write(data)
    f.close()
    return f.name


def test_content_key_stable_for_same_content_and_params():
    p = _tmpfile(b"same bytes" * 1000)
    assert content_key(p, {"stage": "signals"}) == content_key(p, {"stage": "signals"})


def test_content_key_changes_with_content_and_params():
    a = _tmpfile(b"aaaa" * 1000)
    b = _tmpfile(b"bbbb" * 1000)
    assert content_key(a) != content_key(b)
    assert content_key(a, {"stage": "signals"}) != content_key(a, {"stage": "scenes"})
    assert content_key(a, {"v": "1"}) != content_key(a, {"v": "2"})


def test_cache_roundtrip_and_miss():
    root = tempfile.mkdtemp()
    cache = AnalysisCache(root)
    assert cache.get("nope") is None
    cache.put("k1", {"duration": 12.5, "events": [1, 2, 3]})
    assert cache.get("k1") == {"duration": 12.5, "events": [1, 2, 3]}


def test_corrupt_entry_reads_as_miss():
    root = tempfile.mkdtemp()
    cache = AnalysisCache(root)
    (Path(root) / "bad.json").write_text("{not json", encoding="utf-8")
    assert cache.get("bad") is None


def test_provenance_appends_and_traces_to_source():
    src = _tmpfile(b"source video bytes" * 100)
    out = _tmpfile(b"rendered output bytes" * 100)
    log = str(Path(tempfile.mkdtemp()) / "provenance.jsonl")

    record_render(log, source_video=src, output_path=out,
                  program={"operations": [{"type": "cut"}]})
    record_render(log, source_video=src, output_path=out,
                  program={"operations": []}, assets=[src])

    entries = read_log(log)
    assert len(entries) == 2                       # append-only: both remain
    first = entries[0]
    assert first["source"]["content"] == content_key(src)
    assert first["output"]["content"] == content_key(out)
    assert first["program"]["operations"][0]["type"] == "cut"
    assert entries[1]["assets"][0]["content"] == content_key(src)


def test_read_log_missing_file_is_empty():
    assert read_log("/nonexistent/provenance.jsonl") == []


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

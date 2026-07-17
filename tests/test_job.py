"""Tests for the multi-deliverable job — request logic, no video/models."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kreator.director import EDITING_PRESETS, JobRequest
from kreator.director.job import _KEEP_BY_INTENSITY, _needs_transcript


def test_defaults_reproduce_the_autonomous_edit():
    req = JobRequest()
    assert req.long_edit and req.shorts == 0
    assert req.captions == "auto" and req.intensity == "auto"
    assert req.aspect is None and req.music


def test_intensity_map_covers_choices():
    assert set(_KEEP_BY_INTENSITY) == {"light", "medium", "heavy"}
    assert _KEEP_BY_INTENSITY["light"] > _KEEP_BY_INTENSITY["heavy"]


def test_transcript_needed_for_captions_or_shorts():
    preset = dict(EDITING_PRESETS["punchy"])          # keep_dialogue=False
    assert not _needs_transcript(JobRequest(), preset, has_audio=True)
    assert _needs_transcript(JobRequest(captions="karaoke"), preset, True)
    assert _needs_transcript(JobRequest(shorts=3), preset, True)
    # A silent video never needs one, whatever was asked.
    assert not _needs_transcript(JobRequest(captions="karaoke", shorts=3),
                                 preset, has_audio=False)


def test_transcript_needed_when_preset_keeps_dialogue():
    mission = EDITING_PRESETS["mission"]
    assert _needs_transcript(JobRequest(), mission, has_audio=True)


def test_request_serializes_for_the_manifest():
    d = JobRequest(shorts=3, captions="karaoke", notes=["3 Short(s) requested"]).to_dict()
    assert d["shorts"] == 3 and d["captions"] == "karaoke"
    assert d["notes"] == ["3 Short(s) requested"]


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

"""faster-whisper transcription over a video's audio track (CPU-friendly).

Heavy imports are lazy so importing ``kreator.speech`` costs nothing until you
actually transcribe. The model is loaded once and cached per process.
"""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ..ffmpeg import ffmpeg_bin

_MODEL_CACHE: dict[str, object] = {}


@dataclass(frozen=True)
class Word:
    """One spoken word with its own timestamps — what karaoke captions need."""
    start: float
    end: float
    text: str

    def to_dict(self) -> dict[str, object]:
        return {"start": round(self.start, 2), "end": round(self.end, 2),
                "text": self.text.strip()}


@dataclass(frozen=True)
class SpeechSegment:
    start: float
    end: float
    text: str
    words: tuple[Word, ...] = ()   # per-word timing when transcribed with it

    def to_dict(self) -> dict[str, object]:
        d: dict[str, object] = {
            "start": round(self.start, 2),
            "end": round(self.end, 2),
            "text": self.text.strip(),
        }
        if self.words:
            d["words"] = [w.to_dict() for w in self.words]
        return d


def _extract_wav(video_path: str) -> str:
    """Decode the audio track to a temp 16 kHz mono WAV for the ASR model."""
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    cmd = [
        ffmpeg_bin(), "-y", "-i", video_path,
        "-vn", "-ac", "1", "-ar", "16000", tmp.name,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        Path(tmp.name).unlink(missing_ok=True)
        tail = "\n".join(proc.stderr.strip().splitlines()[-4:])
        raise RuntimeError(f"audio extraction failed:\n{tail}")
    return tmp.name


def _model(model_size: str):  # pragma: no cover - loads weights
    if model_size not in _MODEL_CACHE:
        from faster_whisper import WhisperModel  # type: ignore

        _MODEL_CACHE[model_size] = WhisperModel(
            model_size, device="cpu", compute_type="int8"
        )
    return _MODEL_CACHE[model_size]


def transcribe(
    video_path: str, *, model_size: str = "base", word_timestamps: bool = False,
    language: str | None = None, verbose: bool = False
) -> list[SpeechSegment]:
    """Transcribe speech in ``video_path``. Returns time-stamped segments.

    ``vad_filter`` is on so gunfire, music, and engine noise are not mistaken
    for speech — important for gameplay audio. ``word_timestamps`` also times
    each word (slower), which is what animated karaoke captions need.
    ``language`` is an ISO code ("pt", "en", "es", …) to pin the spoken
    language; ``None`` lets Whisper auto-detect it.
    """
    wav = _extract_wav(video_path)
    try:
        model = _model(model_size)
        segments, info = model.transcribe(wav, vad_filter=True,
                                          language=language,
                                          word_timestamps=word_timestamps)
        out = []
        for s in segments:
            if not (s.text and s.text.strip()):
                continue
            words = tuple(
                Word(float(w.start), float(w.end), w.word.strip())
                for w in (s.words or [])
                if w.word and w.word.strip()
            ) if word_timestamps else ()
            out.append(SpeechSegment(float(s.start), float(s.end), s.text, words))
        if verbose:
            print(f"[asr] {info.language}: {len(out)} speech segments")
        return out
    finally:
        Path(wav).unlink(missing_ok=True)


def presence_series(
    segments: list[SpeechSegment], times: list[float]
) -> list[float]:
    """Map speech segments onto a time grid as a 0/1 presence signal."""
    if not times:
        return []
    presence = [0.0] * len(times)
    if not segments:
        return presence
    ordered = sorted(segments, key=lambda s: s.start)
    j = 0
    for i, t in enumerate(times):
        while j < len(ordered) and ordered[j].end < t:
            j += 1
        if j < len(ordered) and ordered[j].start <= t <= ordered[j].end:
            presence[i] = 1.0
    return presence

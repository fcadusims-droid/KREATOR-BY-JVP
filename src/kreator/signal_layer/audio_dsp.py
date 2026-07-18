"""Audio energy series + a coarse energy-based VAD, lazily imported.

Audio amplitude peaks are the spec's additional highlight trigger (a reaction,
a hit, a laugh). We compute short-window RMS energy and normalize it. A simple
energy threshold doubles as a lightweight voice-activity proxy for gameplay,
where dedicated VAD is secondary.

Decoding note: soundfile cannot read video containers, and librosa's audioread
fallback fails silently without a system ffmpeg — a real 36-minute mp4 came
back with an all-zero audio series that way. So the track is first extracted
to a temp WAV with the project's own ffmpeg (the same one every render uses),
and librosa reads that. When even that fails the caller degrades to
motion+scene signals — see ``pipeline``.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from ..ffmpeg import ffmpeg_bin


class AudioUnavailable(RuntimeError):
    """Raised when no decoder can read the audio track."""


def _extract_wav(video_path: str, sr: int) -> str:
    """Decode the container's audio to a temp mono WAV soundfile can read."""
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    proc = subprocess.run(
        [ffmpeg_bin(), "-y", "-i", video_path,
         "-vn", "-ac", "1", "-ar", str(sr), tmp.name],
        capture_output=True, text=True)
    if proc.returncode != 0:
        Path(tmp.name).unlink(missing_ok=True)
        tail = "\n".join(proc.stderr.strip().splitlines()[-3:])
        raise AudioUnavailable(f"audio extraction failed:\n{tail}")
    return tmp.name


def audio_series(
    video_path: str, hop_seconds: float = 0.5
) -> tuple[list[float], list[float], list[float]]:
    """Return ``(times, energy, speech)``.

    ``energy`` is normalized RMS per hop window; ``speech`` is a 0/1 flag from a
    relative energy threshold. Raises ``AudioUnavailable`` if the track can't be
    decoded.
    """
    try:
        import librosa  # type: ignore
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise AudioUnavailable("librosa not installed") from exc

    sr = 16000
    wav = _extract_wav(video_path, sr)
    try:
        y, sr = librosa.load(wav, sr=sr, mono=True)
    except Exception as exc:  # pragma: no cover - decoder dependent
        raise AudioUnavailable(f"could not decode audio: {exc}") from exc
    finally:
        Path(wav).unlink(missing_ok=True)

    if y is None or len(y) == 0:
        raise AudioUnavailable("empty audio track")

    hop = max(1, int(hop_seconds * sr))
    times: list[float] = []
    raw: list[float] = []
    for start in range(0, len(y), hop):
        window = y[start : start + hop]
        if len(window) == 0:
            continue
        rms = float((window**2).mean() ** 0.5)
        raw.append(rms)
        times.append(start / sr)

    energy = _normalize(raw)
    # Relative threshold: speech/reaction where energy clears 35% of a
    # video-local reference (median of the non-silent portion).
    ref = _reference(energy)
    speech = [1.0 if e >= 0.35 * ref else 0.0 for e in energy]
    return times, energy, speech


def _normalize(xs: list[float]) -> list[float]:
    if not xs:
        return []
    hi = max(xs)
    if hi <= 0:
        return [0.0 for _ in xs]
    return [x / hi for x in xs]


def _reference(xs: list[float]) -> float:
    nonzero = sorted(x for x in xs if x > 0)
    if not nonzero:
        return 1.0
    return nonzero[len(nonzero) // 2]  # median of the non-silent portion

"""Audio energy series + a coarse energy-based VAD, lazily imported.

Audio amplitude peaks are the spec's additional highlight trigger (a reaction,
a hit, a laugh). We compute short-window RMS energy and normalize it. A simple
energy threshold doubles as a lightweight voice-activity proxy for gameplay,
where dedicated VAD is secondary.

Loading audio from a container needs a decoder (ffmpeg/soundfile). When none is
available the caller degrades to motion+scene signals — see ``pipeline``.
"""

from __future__ import annotations


class AudioUnavailable(RuntimeError):
    """Raised when no decoder can read the audio track."""


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

    try:
        y, sr = librosa.load(video_path, sr=16000, mono=True)
    except Exception as exc:  # pragma: no cover - decoder/ffmpeg dependent
        raise AudioUnavailable(f"could not decode audio: {exc}") from exc

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

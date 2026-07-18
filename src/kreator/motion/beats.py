"""Beat tracking for beat-synced effects. Lazy librosa; pure snap helper."""

from __future__ import annotations


def beat_times(audio_path: str) -> list[float]:
    """Beat instants (seconds) of a music track, via librosa's beat tracker.
    Returns [] when librosa or the decode is unavailable — beat sync is an
    enhancement, never a requirement."""
    try:
        import librosa  # type: ignore

        y, sr = librosa.load(audio_path, sr=22050, mono=True)
        _tempo, frames = librosa.beat.beat_track(y=y, sr=sr)
        return [float(t) for t in librosa.frames_to_time(frames, sr=sr)]
    except Exception:
        return []


def snap_to_beats(times: list[float], beats: list[float],
                  *, tol: float = 0.35) -> list[float]:
    """Snap each time to its nearest beat when within ``tol`` seconds."""
    if not beats:
        return list(times)
    out = []
    for t in times:
        nearest = min(beats, key=lambda b: abs(b - t))
        out.append(nearest if abs(nearest - t) <= tol else t)
    return out

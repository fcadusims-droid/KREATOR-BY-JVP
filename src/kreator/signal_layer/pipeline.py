"""Signal Layer orchestration: video → SignalBundle.

Combines motion, audio, and scene signals into one deterministic bundle and
derives discrete trigger events (peaks). Degrades gracefully: if the audio
track can't be decoded (no ffmpeg/decoder), it proceeds with motion + scene
signals and says so, rather than failing the whole analysis.

``synthetic_bundle`` builds a bundle from explicit peak specs, so the Planner
and the E1 harness can be exercised deterministically without any video.
"""

from __future__ import annotations

import math

from ..types import Event, SignalBundle
from .audio_dsp import AudioUnavailable, audio_series
from .motion import motion_series
from .scenes import detect_scene_cuts


def detect_peaks(
    times: list[float],
    series: list[float],
    kind: str,
    *,
    min_separation: float = 4.0,
    k: float = 1.0,
) -> list[Event]:
    """Find local maxima that stand out above ``mean + k·std``.

    Deterministic peak picking: a point is a peak if it is the local maximum,
    exceeds the adaptive threshold, and is at least ``min_separation`` seconds
    from an already-accepted, stronger peak. Strength is the normalized series
    value at the peak.
    """
    if not times or not series or len(times) != len(series):
        return []

    mean = sum(series) / len(series)
    var = sum((x - mean) ** 2 for x in series) / len(series)
    std = math.sqrt(var)
    threshold = mean + k * std

    # Candidate peaks: strictly greater than neighbours (or plateau start).
    raw: list[tuple[float, float]] = []  # (time, strength)
    for i, val in enumerate(series):
        if val < threshold:
            continue
        left = series[i - 1] if i > 0 else -math.inf
        right = series[i + 1] if i < len(series) - 1 else -math.inf
        if val >= left and val >= right:
            raw.append((times[i], val))

    # Enforce spacing, keeping stronger peaks first (deterministic tie-break by
    # earlier time).
    raw.sort(key=lambda p: (-p[1], p[0]))
    accepted: list[tuple[float, float]] = []
    for t, strength in raw:
        if all(abs(t - at) >= min_separation for at, _ in accepted):
            accepted.append((t, strength))

    accepted.sort(key=lambda p: p[0])
    return [Event(time=t, kind=kind, strength=min(1.0, s)) for t, s in accepted]


def analyze_video(
    video_path: str,
    *,
    hop_seconds: float = 0.5,
    verbose: bool = False,
) -> SignalBundle:
    """Run the full Signal Layer over a real video file."""
    times, motion, duration, fps = motion_series(video_path, hop_seconds)

    audio_times: list[float] = []
    energy: list[float] = []
    speech: list[float] = []
    try:
        audio_times, energy, speech = audio_series(video_path, hop_seconds)
    except AudioUnavailable as exc:
        if verbose:
            print(f"[signal] audio unavailable ({exc}); motion+scene only")

    # Resample audio series onto the motion timebase so all series share ``times``.
    energy_on_grid = _resample(times, audio_times, energy)
    speech_on_grid = _resample(times, audio_times, speech)

    try:
        scene_cuts = detect_scene_cuts(video_path)
    except Exception as exc:  # pragma: no cover - dependency/format dependent
        if verbose:
            print(f"[signal] scene detection unavailable ({exc})")
        scene_cuts = []

    events: list[Event] = []
    events += detect_peaks(times, motion, "motion_peak")
    if energy_on_grid:
        events += detect_peaks(times, energy_on_grid, "audio_peak")
    events += [Event(time=t, kind="scene_cut", strength=1.0) for t in scene_cuts]

    return SignalBundle(
        duration=duration,
        fps=fps,
        events=events,
        times=times,
        motion=motion,
        audio=energy_on_grid,
        speech=speech_on_grid,
        scene_cuts=scene_cuts,
    )


def _resample(grid: list[float], src_times: list[float], src: list[float]) -> list[float]:
    """Nearest-neighbour resample ``src`` (at ``src_times``) onto ``grid``."""
    if not src or not src_times:
        return []
    out: list[float] = []
    j = 0
    for t in grid:
        while j + 1 < len(src_times) and abs(src_times[j + 1] - t) <= abs(src_times[j] - t):
            j += 1
        out.append(src[j])
    return out


def synthetic_bundle(
    duration: float,
    peaks: list[dict],
    *,
    hop_seconds: float = 0.5,
    scene_cuts: list[float] | None = None,
) -> SignalBundle:
    """Build a deterministic bundle from explicit peak specs (for tests/demos).

    Each peak spec: ``{"time": float, "motion": 0..1, "audio": 0..1,
    "speech": 0..1, "width": seconds}``. Signals are laid down as triangular
    bumps around each peak time on a regular grid. No video, no models — just
    a reproducible fixture the Planner and E1 harness can run against.
    """
    scene_cuts = scene_cuts or []
    n = max(1, int(duration / hop_seconds))
    times = [i * hop_seconds for i in range(n + 1)]
    motion = [0.0] * len(times)
    audio = [0.0] * len(times)
    speech = [0.0] * len(times)

    for spec in peaks:
        pt = float(spec["time"])
        width = float(spec.get("width", 3.0))
        for i, t in enumerate(times):
            d = abs(t - pt)
            if d > width:
                continue
            falloff = 1.0 - d / width
            motion[i] = max(motion[i], float(spec.get("motion", 0.0)) * falloff)
            audio[i] = max(audio[i], float(spec.get("audio", 0.0)) * falloff)
            if d <= width * 0.6:
                speech[i] = max(speech[i], float(spec.get("speech", 0.0)))

    events: list[Event] = []
    events += detect_peaks(times, motion, "motion_peak")
    events += detect_peaks(times, audio, "audio_peak")
    events += [Event(time=t, kind="scene_cut", strength=1.0) for t in scene_cuts]

    return SignalBundle(
        duration=duration,
        fps=1.0 / hop_seconds,
        events=events,
        times=times,
        motion=motion,
        audio=audio,
        speech=speech,
        scene_cuts=scene_cuts,
    )

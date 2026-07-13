"""K Analyst — assembles Evidence from a SignalBundle.

Operating principle (spec §6, §4-RT): the AI does not process the whole video.
The Signal Layer flags candidate instants; the Analyst forms a span around each
flagged instant, summarizes the deterministic signals inside that span, and —
only if a model backend is configured — asks the VLM/ASR to *label* that exact
span. The span itself is never moved by a model.
"""

from __future__ import annotations

from ..types import Event, SignalBundle, Timespan
from .backends import ASRBackend, VLMBackend
from .types import Evidence, bucket


# Capture window around a trigger. The spec's K Clipper uses ~7s before and
# ~3s after an event; a moment's build-up matters more than its aftermath.
PRE_OFFSET = 7.0
POST_OFFSET = 3.0

# Triggers below this normalized strength are ignored as noise.
MIN_TRIGGER_STRENGTH = 0.25


class KAnalyst:
    def __init__(
        self,
        vlm: VLMBackend | None = None,
        asr: ASRBackend | None = None,
        *,
        pre_offset: float = PRE_OFFSET,
        post_offset: float = POST_OFFSET,
        min_trigger_strength: float = MIN_TRIGGER_STRENGTH,
    ) -> None:
        self.vlm = vlm
        self.asr = asr
        self.pre_offset = pre_offset
        self.post_offset = post_offset
        self.min_trigger_strength = min_trigger_strength

    @property
    def source_tag(self) -> str:
        parts = [b.name for b in (self.vlm, self.asr) if b is not None]
        return "+".join(parts) if parts else "signal-only"

    def analyze(
        self, bundle: SignalBundle, video_path: str | None = None
    ) -> list[Evidence]:
        """Produce one Evidence per non-trivial trigger, deduplicated by span."""
        triggers = [
            e
            for e in bundle.events
            if e.strength >= self.min_trigger_strength
            or e.kind == "scene_cut"
        ]
        # Deterministic order: by time, then kind, then strength.
        triggers.sort(key=lambda e: (e.time, e.kind, -e.strength))

        evidences: list[Evidence] = []
        for ev in triggers:
            span = self._window(ev, bundle.duration)
            # Skip a trigger whose window is essentially covered by an existing
            # one — keeps evidence one-per-moment, not one-per-signal.
            if any(span.intersection(e.span) / max(span.duration, 1e-6) > 0.7
                   for e in evidences):
                continue
            evidences.append(self._build(ev, span, bundle, video_path))
        return evidences

    def _window(self, ev: Event, duration: float) -> Timespan:
        raw = Timespan(ev.time - self.pre_offset, ev.time + self.post_offset)
        return raw.clamp(0.0, duration)

    def _build(
        self,
        trigger: Event,
        span: Timespan,
        bundle: SignalBundle,
        video_path: str | None,
    ) -> Evidence:
        signals = self._summarize_signals(span, bundle, trigger)
        labels: dict[str, object] = {}
        source = "signal-only"

        if self.vlm is not None and video_path is not None:  # pragma: no cover
            labels.update(self.vlm.label(video_path, span))
            source = self.source_tag
        if self.asr is not None and video_path is not None:  # pragma: no cover
            text = self.asr.transcribe(video_path, span)
            if text:
                labels["transcript"] = text
            source = self.source_tag

        return Evidence(span=span, signals=signals, labels=labels, source=source)

    def _summarize_signals(
        self, span: Timespan, bundle: SignalBundle, trigger: Event
    ) -> dict[str, float]:
        """Reduce the dense series inside ``span`` to a few normalized features.

        These are the deterministic, model-free properties the Planner scores
        on. All are bucketed so tiny numerical differences don't reorder the
        ranking (the stability guarantee of the Evidence Layer).
        """
        motion = self._slice(span, bundle.times, bundle.motion)
        audio = self._slice(span, bundle.times, bundle.audio)
        speech = self._slice(span, bundle.times, bundle.speech)

        scene_activity = sum(1 for t in bundle.scene_cuts if span.start <= t < span.end)

        features = {
            "trigger_strength": trigger.strength,
            "visual_energy": _peak(motion),
            "visual_energy_mean": _mean(motion),
            "audio_intensity": _peak(audio),
            "hook_strength": _onset_slope(audio, motion),
            "speech_density": _mean(speech),
            "scene_activity": min(1.0, scene_activity / 4.0),
        }
        return {k: bucket(v) for k, v in features.items()}

    @staticmethod
    def _slice(span: Timespan, times: list[float], series: list[float]) -> list[float]:
        if not times or not series:
            return []
        return [
            v
            for t, v in zip(times, series)
            if span.start <= t < span.end
        ]


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _peak(xs: list[float]) -> float:
    return max(xs) if xs else 0.0


def _onset_slope(audio: list[float], motion: list[float]) -> float:
    """Proxy for a 'hook': how sharply energy rises in the first third of the
    window. A moment that erupts quickly reads as a stronger opener for a Short
    than one that ramps slowly."""
    combined = [max(a, m) for a, m in zip(audio, motion)] or audio or motion
    if len(combined) < 3:
        return 0.0
    third = max(1, len(combined) // 3)
    early = _mean(combined[:third])
    peak = _peak(combined)
    return min(1.0, max(0.0, peak - early))

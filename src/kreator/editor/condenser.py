"""The condenser — turns the interest curve into a keep/cut edit plan.

This is a deterministic Planner decision (spec: "the AI classifies; the Planner
decides"): given the interest curve, it decides which spans survive into the
edited video. All the craft is in *not* producing a choppy result — padding
kept regions for context, refusing to make jarring micro-cuts, and dropping
keeps too short to watch.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..types import SignalBundle, Timespan, format_tc
from .interest import envelope, interest_curve


@dataclass(frozen=True)
class KeepSegment:
    span: Timespan
    mean_interest: float

    def to_dict(self) -> dict[str, object]:
        return {
            "start": round(self.span.start, 2),
            "end": round(self.span.end, 2),
            "start_tc": format_tc(self.span.start),
            "end_tc": format_tc(self.span.end),
            "duration": round(self.span.duration, 2),
            "mean_interest": round(self.mean_interest, 3),
        }


@dataclass(frozen=True)
class EditPlan:
    segments: list[KeepSegment]
    original_duration: float
    threshold: float

    @property
    def kept_duration(self) -> float:
        return sum(s.span.duration for s in self.segments)

    @property
    def keep_ratio(self) -> float:
        return self.kept_duration / self.original_duration if self.original_duration else 0.0

    def to_dict(self) -> dict[str, object]:
        return {
            "original_duration": round(self.original_duration, 2),
            "kept_duration": round(self.kept_duration, 2),
            "keep_ratio": round(self.keep_ratio, 3),
            "num_segments": len(self.segments),
            "threshold": round(self.threshold, 4),
            "segments": [s.to_dict() for s in self.segments],
        }


class Condenser:
    def __init__(
        self,
        *,
        target_keep: float = 0.35,
        pad_seconds: float = 1.0,
        min_cut_seconds: float = 3.0,
        min_keep_seconds: float = 1.5,
        min_interest: float = 0.05,
        episode_seconds: float = 12.0,
        exit_ratio: float = 0.65,  # calibrated over 4 GTA videos (docs/calibration)
        speech_floor: float = 0.5,
    ) -> None:
        # Keep roughly the most-active ``target_keep`` fraction of the video.
        self.target_keep = target_keep
        # Context padding added on each side of a kept region.
        self.pad_seconds = pad_seconds
        # Never cut a boring gap shorter than this — micro-cuts read as glitches.
        self.min_cut_seconds = min_cut_seconds
        # Drop a surviving keep shorter than this — too short to watch.
        self.min_keep_seconds = min_keep_seconds
        # Absolute floor: below this, a stretch is never "interesting" no matter
        # what the percentile says. Guards the case where most of the video is
        # near-zero interest and the percentile threshold collapses to ~0.
        self.min_interest = min_interest
        # Window over which "are we in an action *sequence*" is judged. This is
        # what stops a brief lull (the screaming stops, but the chase goes on)
        # from ending an episode mid-action.
        self.episode_seconds = episode_seconds
        # Hysteresis: once inside an episode, stay until the envelope falls to
        # ``exit_ratio`` of the entry threshold — so a dip doesn't cut the scene.
        self.exit_ratio = exit_ratio
        # Interest floor applied wherever speech is present — enough to survive
        # the keep threshold, so quiet dialogue is not cut as "boring".
        self.speech_floor = speech_floor

    def plan(
        self,
        bundle: SignalBundle,
        *,
        speech: list[float] | None = None,
    ) -> EditPlan:
        times, interest = interest_curve(bundle)
        duration = bundle.duration
        if not times:
            return EditPlan([], duration, 0.0)
        step = (times[1] - times[0]) if len(times) > 1 else 0.5

        # Speech rescue: where there is dialogue, lift interest to at least
        # ``speech_floor`` even if the scene is quiet and still — so a story
        # beat isn't cut just because nothing is exploding. Applied before the
        # envelope, so a talky stretch forms its own coherent episode.
        if speech:
            interest = [
                max(v, self.speech_floor) if (i < len(speech) and speech[i] > 0) else v
                for i, v in enumerate(interest)
            ]

        # The envelope is the sustained-activity signal that keeps an ongoing
        # sequence coherent across brief cue drops.
        env = envelope(times, interest, self.episode_seconds)

        # Solve for the entry threshold that actually hits ``target_keep``. The
        # envelope of a uniformly-active video is flat, so a fixed percentile
        # would keep far too much; searching the threshold enforces the target
        # regardless of the envelope's shape — while episodes stay coherent.
        enter = self._solve_threshold(times, env, duration, step)
        kept = self._segments_for(times, env, enter, duration, step)

        segments = [
            KeepSegment(Timespan(s, e), self._mean_interest(times, interest, s, e))
            for s, e in kept
        ]
        return EditPlan(segments, duration, enter)

    def _segments_for(
        self, times: list[float], env: list[float], enter: float,
        duration: float, step: float,
    ) -> list[tuple[float, float]]:
        """Full keep/cut pipeline for a given entry threshold: episodes (with
        hysteresis) → merge short cuts → pad → drop too-short keeps."""
        episodes = self._episodes(times, env, enter, enter * self.exit_ratio,
                                  duration, step)
        merged = self._merge_close(episodes, self.min_cut_seconds)
        padded = self._pad_and_remerge(merged, duration)
        return [(s, e) for s, e in padded if e - s >= self.min_keep_seconds]

    def _solve_threshold(
        self, times: list[float], env: list[float], duration: float, step: float,
    ) -> float:
        """Binary-search the entry threshold so the kept fraction ≈ target_keep.

        Kept fraction decreases monotonically as the threshold rises, so a
        bisection converges quickly. Bounded below by ``min_interest`` so a
        low target never starts keeping genuinely dead footage."""
        lo, hi = self.min_interest, max(env) if env else self.min_interest
        if hi <= lo or duration <= 0:
            return max(lo, hi)

        def kept_ratio(thr: float) -> float:
            segs = self._segments_for(times, env, thr, duration, step)
            return sum(e - s for s, e in segs) / duration

        best = lo
        for _ in range(24):
            mid = (lo + hi) / 2.0
            r = kept_ratio(mid)
            best = mid
            if r > self.target_keep:
                lo = mid   # keeping too much → raise threshold
            else:
                hi = mid   # keeping too little → lower threshold
        return best

    @staticmethod
    def _episodes(
        times: list[float], env: list[float], enter: float, exit_thr: float,
        duration: float, step: float,
    ) -> list[tuple[float, float]]:
        """Schmitt-trigger episode detection: enter when the envelope rises past
        ``enter``, stay in until it falls below ``exit_thr``. The gap between the
        two thresholds is what keeps a scene whole through a brief lull."""
        runs: list[tuple[float, float]] = []
        start: float | None = None
        for i, t in enumerate(times):
            if start is None and env[i] >= enter:
                start = t
            elif start is not None and env[i] < exit_thr:
                runs.append((start, t))
                start = None
        if start is not None:
            runs.append((start, min(duration, times[-1] + step)))
        return runs

    @staticmethod
    def _union(runs: list[tuple[float, float]]) -> list[tuple[float, float]]:
        """Merge a set of possibly-overlapping intervals into disjoint ones."""
        if not runs:
            return []
        ordered = sorted(runs)
        out = [ordered[0]]
        for s, e in ordered[1:]:
            ps, pe = out[-1]
            if s <= pe:
                out[-1] = (ps, max(pe, e))
            else:
                out.append((s, e))
        return out

    @staticmethod
    def _merge_close(
        runs: list[tuple[float, float]], min_gap: float
    ) -> list[tuple[float, float]]:
        """Merge two kept runs whose gap is shorter than ``min_gap`` — the
        boring bit between them is too short to be worth a cut."""
        if not runs:
            return []
        merged = [runs[0]]
        for s, e in runs[1:]:
            ps, pe = merged[-1]
            if s - pe < min_gap:
                merged[-1] = (ps, max(pe, e))
            else:
                merged.append((s, e))
        return merged

    def _pad_and_remerge(
        self, runs: list[tuple[float, float]], duration: float
    ) -> list[tuple[float, float]]:
        padded = [
            (max(0.0, s - self.pad_seconds), min(duration, e + self.pad_seconds))
            for s, e in runs
        ]
        # Padding can create fresh overlaps; collapse them.
        return self._merge_close(padded, 0.0001)

    @staticmethod
    def _mean_interest(
        times: list[float], interest: list[float], s: float, e: float
    ) -> float:
        vals = [interest[i] for i, t in enumerate(times) if s <= t < e]
        return sum(vals) / len(vals) if vals else 0.0

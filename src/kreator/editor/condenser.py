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
from .interest import interest_curve, percentile


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

    def plan(self, bundle: SignalBundle) -> EditPlan:
        times, interest = interest_curve(bundle)
        duration = bundle.duration
        if not times:
            return EditPlan([], duration, 0.0)

        # Adaptive threshold: the top ``target_keep`` fraction of interest, but
        # never below the absolute interest floor.
        threshold = max(percentile(interest, 1.0 - self.target_keep), self.min_interest)

        raw = self._runs_above(times, interest, threshold, duration)
        merged = self._merge_close(raw, self.min_cut_seconds)
        padded = self._pad_and_remerge(merged, duration)
        kept = [(s, e) for s, e in padded if e - s >= self.min_keep_seconds]

        segments = [
            KeepSegment(Timespan(s, e), self._mean_interest(times, interest, s, e))
            for s, e in kept
        ]
        return EditPlan(segments, duration, threshold)

    @staticmethod
    def _runs_above(
        times: list[float], interest: list[float], thr: float, duration: float
    ) -> list[tuple[float, float]]:
        """Contiguous runs where interest is at or above the threshold."""
        runs: list[tuple[float, float]] = []
        start: float | None = None
        step = (times[1] - times[0]) if len(times) > 1 else 0.5
        for i, t in enumerate(times):
            above = interest[i] >= thr
            if above and start is None:
                start = t
            elif not above and start is not None:
                runs.append((start, t))
                start = None
        if start is not None:
            runs.append((start, min(duration, times[-1] + step)))
        return runs

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

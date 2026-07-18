"""Choose which real frames deserve to be thumbnail candidates. Pure logic."""

from __future__ import annotations

from ..editor.interest import interest_curve


def pick_thumbnail_times(
    bundle, n: int = 3, *, min_separation_ratio: float = 0.08
) -> list[float]:
    """The ``n`` strongest, mutually distant instants of the video.

    Ranked by the same interest curve the editor trusts, greedily keeping only
    times at least ``min_separation_ratio`` of the duration apart — so three
    candidates are three different *moments*, not three frames of one burst.
    """
    times, interest = interest_curve(bundle)
    if not times:
        return []
    min_gap = bundle.duration * min_separation_ratio
    ranked = sorted(range(len(times)), key=lambda i: (-interest[i], times[i]))
    picked: list[float] = []
    for i in ranked:
        t = times[i]
        if all(abs(t - p) >= min_gap for p in picked):
            picked.append(t)
        if len(picked) >= n:
            break
    return picked

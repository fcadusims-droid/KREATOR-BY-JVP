"""Chapter a transcript at topic turns, and find the hook. Pure, deterministic.

A topic turn is where the vocabulary changes: consecutive windows of content
words with little overlap (low Jaccard). Turns are only accepted after a
minimum chapter length and, when scene cuts are known, snapped to the nearest
one — a chapter break that lands on a visual cut reads as intentional. Each
chapter is titled by its most frequent content words.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..types import format_tc
from ..story.score import score_segment

# Words too common to signal a topic (en + pt). Small on purpose.
_STOP = frozenset("""
a an and the of to in on for with is are was were be been it this that these
those i you he she we they me my your our their his her its as at by from or
but so if then than there here what which who when where how why not no yes do
does did just like really very much more most some any all can will would could
should about into out up down over under again once o a os as um uma uns umas de
do da dos das em no na nos nas para por com que se e ou mas nao sim eu voce ele
ela nos eles elas meu minha seu sua isso isto esse essa aquilo la aqui como
quando onde porque muito mais bem ja tem ter foi era ser estar vai vou
""".split())


@dataclass(frozen=True)
class Chapter:
    start: float
    end: float
    title: str

    def to_dict(self) -> dict:
        return {"start": round(self.start, 2), "start_tc": format_tc(self.start),
                "end": round(self.end, 2), "title": self.title}


def _content_words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-zA-Zà-úÀ-Ú]+", text.lower())
            if len(w) > 2 and w not in _STOP]


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _title(words: list[str], n: int = 3) -> str:
    freq: dict[str, int] = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    top = sorted(freq, key=lambda w: (-freq[w], w))[:n]
    return " ".join(top).title() if top else "Chapter"


def chapter_transcript(
    transcript: list, *, scene_cuts: list | None = None,
    min_chapter: float = 20.0, snap_window: float = 4.0, threshold: float = 0.12,
) -> list[Chapter]:
    """Segment the transcript into titled chapters at topic turns.

    ``scene_cuts`` (optional) pull a boundary onto the nearest visual cut.
    Returns at least one chapter spanning the whole transcript.
    """
    segs = sorted((s for s in transcript if (s.text or "").strip()),
                  key=lambda s: s.start)
    if not segs:
        return []
    if segs[-1].end - segs[0].start < min_chapter * 1.5:
        words = _content_words(" ".join(s.text for s in segs))
        return [Chapter(segs[0].start, segs[-1].end, _title(words))]

    boundaries = [0]
    for i in range(1, len(segs)):
        prev = set(_content_words(" ".join(
            s.text for s in segs[max(boundaries[-1], i - 3):i])))
        nxt = set(_content_words(" ".join(s.text for s in segs[i:i + 3])))
        if segs[i].start - segs[boundaries[-1]].start < min_chapter:
            continue
        if _jaccard(prev, nxt) <= threshold:
            boundaries.append(i)

    # Build chapters, snapping each internal boundary to a nearby scene cut.
    chapters: list[Chapter] = []
    cuts = sorted(scene_cuts or [])
    for b, idx in enumerate(boundaries):
        start = segs[idx].start
        end = (segs[boundaries[b + 1]].start if b + 1 < len(boundaries)
               else segs[-1].end)
        if b > 0 and cuts:
            near = min(cuts, key=lambda c: abs(c - start))
            if abs(near - start) <= snap_window:
                start = near
                if chapters:
                    chapters[-1] = Chapter(chapters[-1].start, near,
                                           chapters[-1].title)
        title = _title(_content_words(
            " ".join(s.text for s in segs[idx:(boundaries[b + 1]
                     if b + 1 < len(boundaries) else len(segs))])))
        chapters.append(Chapter(start, end, title))
    return chapters


def detect_hook(transcript: list, *, within: float = 30.0):
    """The strongest opening beat: the best-scoring line in the first
    ``within`` seconds, or None. Reuses K Story's clippability scorer."""
    segs = sorted((s for s in transcript if (s.text or "").strip()),
                  key=lambda s: s.start)
    if not segs:
        return None
    t0 = segs[0].start
    opening = [s for s in segs if s.start - t0 <= within]
    best, best_score = None, 0.0
    for s in opening:
        sc, _ = score_segment(s.text)
        if sc > best_score:
            best, best_score = s, sc
    if best is None:
        return None
    from ..types import Timespan
    return Timespan(best.start, best.end)

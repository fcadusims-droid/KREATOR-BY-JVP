"""A tiny asset registry over a local library directory.

Layout:
    <root>/
      manifest.json        # optional: {"war-theme.mp3": {"kind":"music","moods":["tense","war"]}}
      music/  sfx/  memes/  # asset files (real, free-to-use — never committed)

A missing manifest is fine: files are classified by their sub-folder and matched
on filename. Every asset must be an actual licensed file the user added; the
registry never fetches or generates anything.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

_AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
_VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm"}
_KIND_DIRS = {"music": "music", "sfx": "sfx", "meme": "memes",
              "broll": "broll"}


@dataclass(frozen=True)
class Asset:
    path: Path
    kind: str                       # "music" | "sfx" | "meme"
    moods: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {"path": str(self.path), "kind": self.kind, "moods": list(self.moods)}


class KLibrary:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self._manifest = self._load_manifest()

    def _load_manifest(self) -> dict:
        mf = self.root / "manifest.json"
        if mf.exists():
            try:
                return json.loads(mf.read_text())
            except Exception:
                return {}
        return {}

    def _assets_of_kind(self, kind: str) -> list[Asset]:
        sub = self.root / _KIND_DIRS.get(kind, kind)
        if not sub.is_dir():
            return []
        wanted = (_VIDEO_EXT if kind == "broll"
                  else _AUDIO_EXT if kind in ("music", "sfx") else None)
        out: list[Asset] = []
        for f in sorted(sub.iterdir()):
            if wanted is not None and f.suffix.lower() not in wanted:
                continue
            meta = self._manifest.get(f.name, {})
            moods = tuple(meta.get("moods", []))
            out.append(Asset(f, kind, moods))
        return out

    def list_music(self) -> list[Asset]:
        return self._assets_of_kind("music")

    def _find(self, kind: str, mood: str | None) -> Asset | None:
        assets = self._assets_of_kind(kind)
        if not assets:
            return None
        if mood:
            m = mood.lower()
            for a in assets:
                if m in [x.lower() for x in a.moods] or m in a.path.stem.lower():
                    return a
        return assets[0]

    def find_music(self, mood: str | None = None) -> Asset | None:
        """Return a music asset matching ``mood`` (by tag or filename), or any
        available track, or ``None`` if the library has no music."""
        return self._find("music", mood)

    def find_sfx(self, name: str | None = None) -> Asset | None:
        """A sound effect matching ``name`` (tag or filename), or any, or None."""
        return self._find("sfx", name)

    def find_broll(self, query: str | None = None) -> Asset | None:
        """A b-roll clip matching ``query`` (tag or filename), or any, or None."""
        return self._find("broll", query)

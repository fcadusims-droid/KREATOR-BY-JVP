"""K Library — the pool of free-to-use assets Kreator may add to an edit.

This is the *only* content Kreator ever adds that isn't the creator's own
footage — and it is never generated: it's real, licensed, free-to-use files the
user (or the community) drops into the library. Music, sound effects, memes.
The DSL's `music`/`broll` operations reference assets by what the library
returns; if the library is empty, those operations simply aren't available.

See ``docs/not-generative.md``: gameplay is 100% the creator's; a library asset
is a real licensed file, not something a model dreamed up.
"""

from .registry import KLibrary, Asset

__all__ = ["KLibrary", "Asset"]

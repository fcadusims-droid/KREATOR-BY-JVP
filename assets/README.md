# K Library — free-to-use assets

This is the only content Kreator ever adds that isn't the creator's own footage
— and it is **never generated**. Everything here must be a real, licensed,
**free-to-use** file that you (or the community) put here. Music, sound effects,
memes.

## Layout

```
assets/
  manifest.json     # optional tags: {"war-theme.mp3": {"kind":"music","moods":["tense","war"]}}
  music/            # background tracks
  sfx/              # sound effects
  memes/            # image/clip memes
```

Drop `.mp3`/`.wav`/… files into `music/` (etc.). Tag them in `manifest.json` by
mood so Kreator can pick a fitting track (e.g. tense music for a shootout). A
missing manifest is fine — files are then matched by filename.

**The media files themselves are gitignored** (they're yours/licensed, not part
of the code). Only this README and `manifest.example.json` are tracked.

## Where to get free-to-use assets

Use only clearly free/CC0/royalty-free sources you have the right to use, e.g.
public-domain music libraries. Kreator never downloads or generates assets — it
only uses what's in this folder.

See [`../docs/not-generative.md`](../docs/not-generative.md).

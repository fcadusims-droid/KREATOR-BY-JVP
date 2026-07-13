# E1 data — running the moment-curation experiment

E1 is the first and highest-weight validation in the spec (§27): **does
K Clipper rank the moments a creator would actually publish?** This folder is
where you assemble the material to answer it.

## What you need

1. **10 real gameplay recordings.** Raw sessions, the messier the better —
   the point is to test the ranking on real material, not a curated reel.
   Put them in `data/videos/` (gitignored; never committed).

2. **A human editor's picks for each video** — the ground truth. For every
   video, an editor watches it and marks the moments they would turn into a
   Short. **Do this before running the system** — an independent human judgment
   is exactly what gives E1 its validity. Mark **3–5 moments per video**: the
   system returns a top-5 by default (`--top-n 5`), so marking many more than 5
   just inflates misses that E1 isn't trying to measure.

## Ground-truth format

One file per video, named `<video>.truth.json`:

```json
{
  "video": "gameplay_01.mp4",
  "picks": [
    { "start": 58.0, "end": 66.0 },
    { "start": 129.0, "end": 137.0 }
  ]
}
```

`start` / `end` are seconds. List the moments the editor chose, best first if
you want to compare rank order later. See `example.truth.json`.

### You don't have to write that JSON by hand

Use `scripts/make_truth.py`. Note each moment in a plain `.txt`, one
`mm:ss-mm:ss` per line (`#` comments and blank lines ignored):

```
# gameplay_01 — my picks, best first
00:58-01:06
02:09-02:17
```

Then convert it:

```bash
python scripts/make_truth.py gameplay_01.mp4 picks_gameplay_01.txt
```

It writes the truth file to **both** `data/labels/<video>.truth.json` and
`out/<video>.truth.json`. That second location matters: the `--batch` evaluator
looks for truth files **next to the rankings in `out/`**, not in `data/labels/`.
Writing both means either workflow below just works.

## Running it

```bash
# 1. Generate the system's ranking for each video
python scripts/run_e1.py --video data/videos/gameplay_01.mp4 \
    --top-n 5 -o out/gameplay_01.ranking.json

# 2. Score it against the human picks
python scripts/eval_e1.py \
    --ranking out/gameplay_01.ranking.json \
    --truth   data/labels/gameplay_01.truth.json

# Or, once you have all 10 ranked into out/ with matching *.truth.json:
python scripts/eval_e1.py --batch out/
```

## Reading the result

The evaluator reports, per video, how many human picks the system's ranking
found, and an **agreement rate**. The spec's success criterion is **majority
agreement** — the system's top-N ranking overlaps more than half of what the
human editor chose.

- **Agreement clears majority across the 10 videos → E1 passes.** The curation
  premise holds; it is worth building K Editor, K Subtitle, K Thumbnail, and
  the rest on top of it.
- **Agreement is low → E1 fails, and that is the cheap, valuable answer.**
  Iterate on the Planner's `ScoringProfile` weights and the Signal Layer's
  triggers *before* building anything downstream — exactly the retrabalho E1
  exists to prevent.

Add the VLM/ASR backends (`requirements-models.txt`) and re-run to measure how
much model labels improve agreement over the signal-only baseline.

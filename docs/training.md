# Training Kreator's taste — the dataset loop

Kreator's ranking is rules-first (signals + K GameSense), and that is
deliberate: rules carry the cold start, are explainable, and never hallucinate.
What rules cannot do is converge on *one creator's* taste. That is the taste
model's job — and this document is the honest description of how the data for
it exists, grows, and gets used.

## The loop that runs today

1. **Every generated Short already carries its features** — the Clipper's
   signal breakdown plus the GameSense event counts (`signals` and
   `game_events` in the manifest). No extra analysis is ever run for training.
2. **Every 👍/👎 in the web UI is a labeled example.** The verdict plus the
   stored features append one row to `web/_work/_dataset/labels.jsonl`
   (append-only, like provenance). Judging clips *is* the labeling session.
3. **The model retrains on the spot** (a deterministic logistic regression,
   numpy, sub-second at this scale) once both classes have at least 4
   examples, and is saved to `web/_work/_dataset/model.json`.
4. **The next job ranks with it**: the model's probability becomes one more
   *bounded* adjustment (±0.25 max) on top of the rules — the deterministic
   Planner always stays in charge (spec §4: the model scores; the Planner
   decides). Its reason string ("matches the creator's learned taste, p=0.82")
   lands in the manifest like every other justification.

Inspect what it learned at any time:

```bash
python scripts/train_taste.py --dataset web/_work/_dataset/labels.jsonl
```

## Why this scale, and not a video model

The honest constraint (spec §23–24): training an end-to-end editing model
needs data that does not exist yet, and would replace the auditable Planner
with a black box. A per-channel logistic model over Kreator's own features is
the right size for the data that *does* exist (the creator's verdicts), is
fully inspectable (the CLI prints per-feature weights), and its failure mode
is graceful — with no data it simply abstains.

## Growing the dataset beyond one channel

Public datasets that fit this loop, for when scale is wanted:

- **QVHighlights** (10k videos, human saliency ratings) — the standard
  highlight-detection benchmark; its clips can be run through Kreator's
  analysis to produce feature rows with public labels.
- **ESTA** (CS:GO pro matches, event streams) — ground-truth kill/round events
  to validate K GameSense against.
- **Kill-feed/HUD datasets** (Roboflow: Valorant kill feed, CoD HUD YOLO
  sets) — the training path for a *visual* death/kill detector, which is the
  known OCR gap (killcam-sized text at 720p is below tesseract readability).

The import path is the same schema: run Kreator's analysis over the public
video, pair the resulting feature row with the public label, append to a
JSONL. Rows whose feature list doesn't match the current `FEATURES` contract
are skipped on load, so the store survives feature evolution.

## What would justify the next step up

A trained *visual* HUD event detector (YOLO-class, per the Roboflow datasets)
enters when the OCR gap measurably costs ranking quality — it has a clear
seat: it would emit the same `GameEvent`s into the same scoring, changing
nothing downstream. An end-to-end learned editor stays out until the
per-channel data makes it more than a demo (spec §15/§24).

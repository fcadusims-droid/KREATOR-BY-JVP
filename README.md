# Kreator

**The Operating System for Human Creativity** — *Human Creativity. AI Operations.*

Kreator amplifies real creators instead of replacing them: the human records
the content; a team of specialized **K Agents** handles the operational work —
understanding, editing, captioning, thumbnails, SEO, publishing, and learning —
always grounded in the creator's own footage. Full vision and runtime spec:
[`Kreator.md`](./Kreator.md).

---

## Where this repo is right now: the E1 slice

The product spec is deliberate that the MVP's job is not to win the market — it
is to **cheaply validate the two assumptions everything else rests on**, before
building the full system:

- **E1 — moment-curation quality.** Does K Clipper rank the moments a creator
  would actually publish? *(Highest weight — the gate for everything.)*
- **E2 — real unit cost.** Can a video be processed for less than it's charged?

This repo currently implements **exactly the slice needed to answer E1**, and
nothing more:

```
Signal Layer  →  K Analyst (Evidence)  →  Planner / K Clipper  →  ranking.json
```

There is intentionally **no** K Editor, K Subtitle, K Thumbnail, K Publisher,
provenance store, or incremental cache yet. None of them changes whether the
ranking is good — and if E1 fails, iterating on the ranking is far cheaper than
having built all of that first. That is the whole point of E1 as a gate.

### What each piece does

| Component | Role | Status |
|---|---|---|
| **Signal Layer** (`signal_layer/`) | Deterministic, CPU-only signals: optical-flow motion, audio energy, scene cuts → trigger events | Real; degrades gracefully if audio can't be decoded |
| **K Analyst** (`evidence/`) | Forms an evidence window around each trigger, summarizes signals, buckets them for stability. VLM/ASR are pluggable backends | Signal-only path works today; model backends are lazy adapters |
| **Planner / K Clipper** (`planner/`) | Deterministic ranking of candidates with per-signal rationale — *the AI classifies; the Planner decides* | Real, fully unit-tested |
| **E1 harness** (`scripts/`) | `run_e1.py` produces a ranking; `make_truth.py` turns plain-text picks into ground truth; `eval_e1.py` scores the ranking against a human's picks | Real |

## Quick start

```bash
# No dependencies needed for the Planner tests or the demo:
python tests/test_planner.py
python tests/test_signal_layer.py

# See the ranking format on a synthetic session (no video, no models):
python scripts/run_e1.py --demo -o out/ranking.demo.json

# Score a ranking against human picks:
python scripts/eval_e1.py --ranking out/ranking.demo.json --truth data/example.truth.json
```

To run over **real gameplay**, install the deterministic core and follow
[`data/README.md`](./data/README.md):

```bash
pip install -r requirements.txt
python scripts/run_e1.py --video data/videos/gameplay_01.mp4 -o out/gameplay_01.ranking.json
```

Add the VLM/ASR backends (`requirements-models.txt`, needs a GPU) to let the
model confirm events and lift scores above the signal-only baseline.

## Design principles carried from the spec

- **Models are commodity; infrastructure is not.** The VLM/ASR sit behind
  narrow interfaces; the pipeline depends on the interfaces, never a model.
- **The AI classifies; the Planner decides.** No model chooses what makes the
  final cut. A deterministic, versioned Planner turns evidence into a ranking.
- **Ranks, doesn't decide.** K Clipper returns top-N candidates with rationale
  and keeps the human in the loop — the honest answer to a subjective call.
- **Determinism for testability.** Same evidence + same weights → identical
  ranking, so E1 is measurable and the Planner is unit-testable without a video.

## Layout

```
src/kreator/
  types.py               # dependency-free domain types
  signal_layer/          # deterministic signals (CPU): motion, audio, scenes
  evidence/              # K Analyst: signals → normalized evidence; model backends
  planner/               # K Clipper: scoring + deterministic ranking
scripts/
  run_e1.py              # video → ranking.json
  make_truth.py          # plain-text picks → <video>.truth.json
  eval_e1.py             # ranking vs human picks → agreement rate
tests/                   # deterministic tests (no video, no models)
data/                    # how to assemble the 10-gameplay E1 experiment
```

## Next steps (gated on E1)

1. Run E1 on 10 real gameplays; measure agreement against a human editor.
2. **If E1 passes:** measure E2 (VLM + ASR cost) on the same batch — the
   expensive work already ran, so adding cost measurement is nearly free.
3. **Only then:** build downstream agents (Editor, Subtitle, Thumbnail,
   Publisher) and the runtime (contracts, provenance, incremental cache) on a
   validated foundation.

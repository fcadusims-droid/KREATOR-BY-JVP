# Visual understanding with no GPU — the local, offline path

Constraint: **everything must run locally and offline, at zero cost.** No cloud
API, no rented GPU, no subscription. So the question is whether Kreator can get
*visual-semantic* understanding — "this is a scenic pause," "this is a briefing,"
"this is a shootout" — on a plain CPU. The answer, from real measurement on this
machine (4 CPU cores, 15 GB RAM, no GPU): **yes, with two design choices.**

## 1. Sample frames — don't run the VLM on every frame

A VLM on all ~2,000 sampled frames of a 17-minute video needs a GPU. Kreator
never does that. `kreator/vlm/keyframes.py` selects ~15–25 frames worth a label
(episode centers, scene boundaries, interest peaks, and the low-action
"scenic candidates" the signal proxy can't classify), and the VLM labels only
those. That's the spec's #1 cost lever, and it's what makes CPU feasible.

## 2. Ask the model to *describe*, not to *judge*

This is the key finding from testing small CPU VLMs on real GTA frames:

| Prompt style | Result on CPU (SmolVLM-2.2B) |
|---|---|
| "Is this intense or calm?" (judge) | **Unreliable** — called a calm street "ACTION", a driving shot "intense" |
| "What is happening?" (describe) | **Accurate** — "a man is shooting a gun", "a truck parked in a lot", "characters at a map board" |

So the VLM produces a *description* (its strength) and a deterministic keyword
classifier (`kreator/vlm/classify.py`) maps it to a scene type — exactly the
spec's split: **the AI describes; the Planner decides.** Observed on real
keyframes, all correct:

- "A man is shooting a gun in a building." → **action** (keep)
- "Three characters standing in front of a white board with a map." → **dialogue** (keep — a briefing the signals would cut)
- "A white truck is parked in a parking lot." → **idle** (cut candidate)

## Measured cost (this CPU, no GPU)

- Model: SmolVLM-2.2B (`HuggingFaceTB/SmolVLM-Instruct`), fp32.
- Load: ~30–50 s (once). Inference: **~45–50 s per frame**.
- So ~20 keyframes ≈ **15–17 min per video** — slow, but it's an **offline,
  opt-in enrichment pass**, not an interactive step. Runs while you do something
  else, costs nothing.

Smaller models (SmolVLM-500M) are ~3× faster but too weak — they misdescribe.
2.2B is the smallest that describes GTA scenes reliably here.

## How it feeds the edit

Scene labels become a *rescue signal* (`visual_keep_series`) exactly like speech
presence: wherever the VLM saw a scenic / dialogue / action frame, interest is
lifted to a floor so that moment survives the cut and forms its own coherent
episode. This is what finally lets Kreator keep the **quiet-but-meaningful**
moments — the scenic pause, the mission briefing — that motion and audio energy
alone read as "boring."

## Trade-offs, stated honestly

- **Speed:** ~15 min/video on CPU. Fine for batch/offline, not for live editing.
- **Quality:** good on clear scenes; a small model still errs on subtle ones.
  It's a *best-effort enrichment* on top of signals + speech, not a replacement.
- **It improves for free over time:** the backend is pluggable
  (`LocalVLMBackend`); when a better small CPU VLM appears, swap the model id.

## Usage

```bash
python scripts/run_edit.py --video data/videos/gta5_casino_bigcon.mp4 \
    --speech --vlm --vlm-frames 20 -o out/edit.mp4
```

Needs `pip install -r requirements-vlm.txt` (torch, torchvision, transformers —
all CPU wheels). Nothing leaves the machine.

# Kreator

**The Operating System for Human Creativity** — *Human Creativity. AI Operations.*

Kreator amplifies real creators instead of replacing them: the human records the
content; Kreator handles the operational work — understanding it, cutting the
boring parts, keeping the action, and delivering a tighter, watchable video.
Everything runs **locally and offline, on CPU — no GPU, no API, no cost.** Full
vision and runtime spec: [`Kreator.md`](./Kreator.md).

## Quick start — edit a video from your browser

The easiest way, no install on your machine: run the web app in GitHub
Codespaces, upload a gameplay video, pick a quality, download the edited result.
Step-by-step: [`docs/codespaces-guide.md`](./docs/codespaces-guide.md).

Locally it's the same app:

```bash
pip install -r requirements.txt -r requirements-web.txt   # + ffmpeg on your PATH
python web/app.py            # open http://localhost:5000
```

Upload a gameplay video → Kreator **understands what game it is and edits it on
its own** (no settings) → **download** the finished edit.

*(The CLI, `scripts/run_edit.py`, still exposes the individual knobs —
`--target-keep`, `--height {480,720,1080}`, `--aspect {9:16,1:1,16:9}`,
`--speech`, `--vlm` — for manual control; the web app is the fully autonomous
path.)*

## What Kreator does today

Two capabilities, both built on the same signal-first pipeline.

### K Editor — condense a long gameplay into its interesting parts
Takes a long, unedited, no-commentary recording and produces a shorter edited
video: it cuts the low-action stretches and keeps the action, coherently (it
never cuts in the middle of an ongoing scene).

```bash
python scripts/run_edit.py --video data/videos/clip.mp4 \
    --target-keep 0.40 --height 720 -o out/edited.mp4
```

How it decides *boring vs interesting* — all on CPU, offline:
| Layer | What it adds | Flag |
|---|---|---|
| **Signals** | motion + audio energy → action; episode detection keeps scenes whole | (always) |
| **Speech** | Whisper transcribes dialogue → keeps quiet story/mission talk | `--speech` |
| **VLM** | SmolVLM *describes* sampled keyframes → keeps scenic/briefing moments | `--vlm` |

The VLM insight, and why it works with no GPU: run it on ~20 *sampled*
keyframes (not every frame), and ask it to **describe** (which small local
models do well) while a deterministic keyword rule **decides** the scene type.
See [`docs/vlm-without-gpu.md`](./docs/vlm-without-gpu.md).

The edit is then produced as a small **operations program** (a cut spine plus
overlays, each carrying its justification) run by an FFmpeg executor. Operations
today: `cut`, `subtitle` (the creator's own transcribed dialogue, remapped to
the edited timeline), `zoom` (punch-in on the action), `transition` (crossfade),
`music` (a background track from the **K Library** of free-to-use assets, mixed
under the audio), and `reframe` (recrop to another aspect — `--aspect 9:16`
turns the edit vertical for Shorts, with the crop window following the action's
motion, or `--reframe pad` to fit with bars). A **K Validator** step checks the
render matches the plan — duration, streams, and aspect — before it's handed
over. `b-roll` is defined in the program but its executor is future work.

The reasoning — the model *plans* an intermediate representation (timeline +
operations + justifications) and a deterministic executor runs it, rather than a
model "editing" video, and why this is preferred over training an editing model
now — is in [`docs/training-vs-dsl.md`](./docs/training-vs-dsl.md). Kreator is
**not a generative AI**: every pixel and sound is the creator's own footage, and
the only added assets are real free-to-use library files
([`docs/not-generative.md`](./docs/not-generative.md)).

### K Clipper — rank the best moments for Shorts (E1)
The validation slice: given a video, deterministically rank the top moments a
creator would clip. Used to test **E1 — moment-curation quality**.

```bash
python scripts/run_e1.py --video data/videos/clip.mp4 -o out/ranking.json
python scripts/eval_e1.py --ranking out/ranking.json --truth data/example.truth.json
```

Details and the experiment setup: [`data/README.md`](./data/README.md).

## Design principles (from the spec)

- **Models are commodity; infrastructure is not.** Every model (Whisper, VLM)
  sits behind a narrow interface; the pipeline depends on the interface.
- **The AI describes; the Planner decides.** No model chooses the final cut. A
  deterministic, versioned Planner turns evidence into a keep/cut decision.
- **Never cut mid-action.** Episodes are detected with an activity envelope +
  hysteresis, so a brief lull doesn't chop an ongoing scene.
- **Local, offline, free.** No GPU, no API — the hard constraint, honoured.

## Layout

```
src/kreator/
  types.py            # dependency-free domain types
  ffmpeg.py           # single place the FFmpeg binary is resolved
  signal_layer/       # deterministic CPU signals: motion, audio, scenes
  evidence/           # K Analyst: signals → normalized evidence (+ backend protocols)
  planner/            # K Clipper: scoring + deterministic ranking (E1)
  editor/             # K Editor: interest curve → condense → render (via the DSL)
  dsl/                # the edit as data: operations program + FFmpeg executor
  reframe/            # aspect reframing: focus-follow crop math for 9:16 Shorts
  director/           # autonomous mode: recognize the game → preset → program
  library/            # K Library: registry of the user's free-to-use assets
  validator/          # K Validator: does the render match the plan?
  speech/             # dialogue transcription (faster-whisper, CPU)
  vlm/                # local scene understanding (keyframes → SmolVLM → classify)
web/app.py            # upload → edit → download frontend (Flask)
scripts/              # run_edit, run_e1, eval_e1, make_truth, analyze_cache, calibrate
tests/                # deterministic tests (no video, no models)
docs/                 # codespaces-guide, vlm-without-gpu, training-vs-dsl, not-generative
```

## Install options

| For | Install |
|---|---|
| The editor + web app | `pip install -r requirements.txt -r requirements-web.txt` |
| Dialogue (`--speech`) | already in `requirements.txt` (faster-whisper, CPU) |
| Scene understanding (`--vlm`) | `pip install -r requirements-vlm.txt --extra-index-url https://download.pytorch.org/whl/cpu` |

`ffmpeg` must be on your PATH (the Codespaces devcontainer installs it for you).

## Tests

```bash
python -m pytest        # or: run each tests/test_*.py directly (no deps needed)
```

All tests are deterministic — no video, no models.

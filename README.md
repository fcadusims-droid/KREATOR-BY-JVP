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

Upload a video → Kreator **understands it and edits it on its own** →
**download** the deliverables. No options required — but you can guide it: ask
for Shorts, set the cut intensity, pick the caption style and spoken language,
or just **type what you want in plain language** (English or Portuguese):
*"make 3 shorts of ~30 seconds with animated captions, no music"*. One upload
can produce the full edit **and** N vertical Shorts from a single analysis
pass.

*(The CLIs expose the same power: `scripts/run_job.py` for multi-deliverable
jobs with `--instruction`, `scripts/make_shorts.py` for Shorts alone,
`scripts/run_edit.py` for the single condensed edit with manual knobs —
`--target-keep`, `--height`, `--aspect {9:16,1:1,16:9}`, `--captions`,
`--speech`, `--vlm`.)*

## What Kreator does today

Built on one signal-first pipeline:

- **Condense** a long recording into its interesting parts (K Editor).
- **Create vertical Shorts** from the top-ranked moments (K Clipper → 9:16
  reframe that follows the action → render).
- **Caption** with the creator's own words — plain subtitles or word-by-word
  **karaoke captions** (word-level Whisper timings burned via libass).
- **Edit talking content** (vlog/podcast/class): recognized by speech coverage,
  edited by *pause removal* — keep what was said, cut the dead air, never
  mid-sentence.
- **Take instructions**: guided web options or a plain-language sentence
  (English or Portuguese) parsed deterministically into the same job form —
  including the spoken language for transcription/captions (auto-detected by
  default, or pinned: en, pt, es, fr, de, it, ja, ko).
- **Compose thumbnails from real frames** (K Thumbnail): pick the strongest
  distinct moments, crop with composition, lift contrast/color, sharpen,
  optionally draw the creator's own title — a Photoshop editor's treatment,
  never a generator.
- **Reuse analysis**: an incremental cache (`content + module version +
  params`) means a second deliverable or re-run never re-analyzes the video,
  and every render appends to an **append-only provenance log** tracing output
  → operations program → source footage hashes.

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
the edited timeline), `caption` (word-by-word karaoke, word timings remapped
individually), `zoom` (punch-in on the action), `transition` (crossfade),
`music` (a background track from the **K Library** of free-to-use assets, mixed
under the audio), `sfx` (a library one-shot mixed in at an instant, without
lowering the creator's own audio), `broll` (a library clip overlaid as a
cutaway for its window, scaled to the frame, while the main audio continues),
and `reframe` (recrop to another aspect — `--aspect 9:16` turns the edit
vertical for Shorts, with the crop window following the action's motion, or
`--reframe pad` to fit with bars). A **K Validator** step checks the render
matches the plan — duration, streams, and aspect — before it's handed over,
and every render appends a provenance record tracing it back to the source
footage.

The reasoning — the model *plans* an intermediate representation (timeline +
operations + justifications) and a deterministic executor runs it, rather than a
model "editing" video, and why this is preferred over training an editing model
now — is in [`docs/training-vs-dsl.md`](./docs/training-vs-dsl.md). Kreator is
**not a generative AI**: every pixel and sound is the creator's own footage, and
the only added assets are real free-to-use library files
([`docs/not-generative.md`](./docs/not-generative.md)).

### K Clipper — rank the best moments, then render them as Shorts
Given a video, deterministically rank the top moments a creator would clip
(the **E1** validation slice) — and now turn each into a finished vertical
Short: span fitted to 15–60s, reframed 9:16 following the action, captioned,
validated, listed in a manifest with its rationale.

```bash
python scripts/make_shorts.py --video data/videos/clip.mp4 --top-n 5 \
    --speech -o out/shorts            # 5 ready Shorts + shorts.json manifest
python scripts/run_e1.py --video data/videos/clip.mp4 -o out/ranking.json
python scripts/eval_e1.py --ranking out/ranking.json --truth data/example.truth.json
```

### One job, several deliverables

```bash
python scripts/run_job.py --video clip.mp4 --shorts 3 --cache .cache -o out/job
# or in plain language:
python scripts/run_job.py --video clip.mp4 \
    --instruction "light full edit + three shorts of ~30s with animated captions"
```

The analysis (signals, VLM scenes, transcript) runs **once** and is cached;
every deliverable is composed from it, validated, and logged with provenance.

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
  cache.py            # incremental analysis cache (content+version+params key)
  provenance.py       # append-only render log: output → program → source hashes
  signal_layer/       # deterministic CPU signals: motion, audio, scenes
  evidence/           # K Analyst: signals → normalized evidence (+ backend protocols)
  planner/            # K Clipper: scoring + deterministic ranking (E1)
  editor/             # K Editor: interest curve → condense; pause removal for talking
  dsl/                # the edit as data: operations program + FFmpeg executor
  reframe/            # aspect reframing: focus-follow crop math for 9:16 Shorts
  shorts/             # ranked moments → finished vertical Shorts + manifest
  thumbnail/          # K Thumbnail: strongest real frames, treated, never generated
  director/           # autonomy: recognize content → preset → multi-deliverable job
  library/            # K Library: registry of the user's free-to-use assets
  validator/          # K Validator: does the render match the plan?
  speech/             # dialogue transcription, word-level timings (faster-whisper)
  vlm/                # local scene understanding (keyframes → SmolVLM → classify)
web/app.py            # upload → guided/autonomous job → downloads (Flask)
scripts/              # run_job, make_shorts, run_edit, run_e1, eval_e1, make_truth, …
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

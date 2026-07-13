# Running the VLM without a GPU

Neither the developer's machine nor this build environment has a GPU, so the
question is real: how does Kreator get *visual-semantic* understanding — "this
is a beautiful scenic moment," "the player is admiring a sunset," "this is a
tense standoff" — which the signal proxy fundamentally cannot see?

The short answer: **a full 7B VLM on every frame needs a GPU, but Kreator was
never supposed to do that.** The spec's #1 cost lever is *intelligent frame
sampling* — run the VLM only on the handful of frames the Signal Layer already
flagged, not on all ~2,000 sampled frames of a 17-minute video. Once you're
labelling ~10–40 frames instead of thousands, the GPU stops being a hard
requirement.

## Why this reframes the problem

| | Naive | Kreator |
|---|---|---|
| Frames sent to the VLM | every frame (~2,000) | ~10–40 keyframes |
| Where they come from | brute force | one per episode + scene boundaries + interest peaks |
| Feasible on CPU? | No | Yes |
| Feasible via a cheap API? | No (cost/latency) | Yes (~20 images/video) |

The editor does not need to know what happens in every second. It needs a label
for each *candidate segment* the condenser is unsure about: keep or cut, and
*why* (action / dialogue / scenic / idle). That's a small number of frames.

## The prerequisite (CPU-only, no VLM): a keyframe sampler

Before any VLM, Kreator needs the code that chooses *which* frames to look at.
This is pure Signal-Layer work and runs on CPU today:

- one representative frame per detected episode (the interest-weighted center),
- frames at scene-cut boundaries,
- frames at the highest interest peaks,
- optionally, frames in *low-action but non-idle* stretches — the scenic
  candidates the signal proxy can't classify, which are exactly the ones a VLM
  should adjudicate.

Output: ~10–40 JPEGs per video + their timestamps. This is buildable now and is
the plug the VLM connects to. It already matches the `VLMBackend` protocol in
`src/kreator/evidence/backends.py` (`label(video_path, span) -> {...}`).

## Two backends, no local GPU — pick per deployment

### Path A — Cloud vision API (recommended default)
Send the sampled keyframes to a hosted vision model (any frontier or open VLM
served behind an API). No GPU anywhere; frontier-quality scene understanding;
~20 images per video is a few cents. Needs an API key and network (this
environment has network). This is "models are commodity" in its purest form —
the backend is an adapter; swap the provider without touching the pipeline.

- **Pros:** best quality, zero local hardware, trivial to run here.
- **Cons:** per-use cost, needs a key, frames leave the machine (a privacy
  trade-off — relevant to the self-host story, fine for the cloud edition).

### Path B — Small VLM on CPU (offline fallback)
Run a small, CPU-friendly VLM (e.g. SmolVLM ~256M–2B, Moondream2 ~1.6B) locally
on the sampled keyframes. Slower per frame (~1–30s depending on model size), but
over ~20 frames that's seconds to a few minutes — the same order as the Whisper
transcription already running on CPU here.

- **Pros:** no key, no network, no frames leave the machine (self-host friendly).
- **Cons:** lower quality than frontier models; model download + RAM.

A hybrid is natural: Path B for a cheap first pass, escalate only the ambiguous
frames to Path A.

## What a VLM label unlocks that signals cannot

- **Scenic appreciation:** low motion + quiet audio is identical, in signal, to
  idling. A VLM frame label ("a sunset over the mountains, player standing
  still") lets the editor *keep* it instead of cutting it as boring — the exact
  case from the product feedback.
- **Scene type for the condenser:** tag each candidate as
  action / dialogue / scenic / travel / idle, so keep/cut is decided on *what
  the moment is*, not just how loud it is.
- **Dialogue importance:** combined with the transcript Kreator already
  produces, a VLM can weight *which* dialogue matters (a mission briefing vs.
  ambient chatter).

## Recommended sequence

1. **Build the keyframe sampler** (CPU, now) — the prerequisite for either path.
2. **Wire a cloud VLM adapter** (Path A) behind the existing `VLMBackend`
   protocol — the fastest way to get real visual understanding here, no GPU.
3. **Add a small-CPU-VLM adapter** (Path B) for the offline/self-host path.
4. Feed scene-type labels into the condenser's interest so scenic and
   context-important moments survive.

The honest bottom line: **the GPU was only ever needed for the brute-force
approach Kreator explicitly rejects.** With signal-driven frame sampling, visual
understanding is reachable either through a cheap API (best here) or a small CPU
model (best for offline/self-host) — the pluggable-backend design means the
choice is a deployment detail, not an architecture change.

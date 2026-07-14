# Editing operations (DSL) vs. training a model — the decision

A guide was proposed for *training* Kreator to edit, in four levels (editing
knowledge → timeline → operations → GUI software control), using academic
datasets (AVE, VideoSham, OpenVE, GUIDE) and behavior-cloning recordings of
editors. This documents what was checked and the decision, so the reasoning
isn't lost.

## What the AVE dataset actually is (read before deciding)

- **Domain: movies** (MovieClips YouTube channel) — professional cinematic
  scenes, *not* gameplay.
- **Annotations: cinematographic shot grammar** — shot size, angle, type,
  motion, subject, location, people count, sound source. It teaches you to
  *recognize* film language; it does **not** contain editing *operations*
  (cuts, music, subtitles, b-roll).
- **Videos must be downloaded from YouTube** — which is blocked from Kreator's
  build environment (bot detection), so the dataset can't even be assembled
  here.

Conclusion on AVE: wrong domain (cinema ≠ gameplay), it's *recognition* not
*operations*, and it's inaccessible here. Not the right dataset for Kreator now.

## The proposal's core insight is right — and already built

> "This is much more like an agent that operates software than like Stable
> Diffusion."

Exactly. Kreator has been built as that from the start: deterministic
**operations executed by FFmpeg**, nothing generative. The four levels map onto
what already exists:

| Level | Proposal | Where Kreator is |
|---|---|---|
| 1 — Editing knowledge | style → concepts (text) | The Director: detected genre → editing preset |
| 2 — Timeline | video → timeline | `EditPlan` is a timeline (segments + scene labels) |
| 3 — Operations (DSL) | emit commands, an executor runs them | `plan → render` already does this for `cut`; **this doc's build extends it** |
| 4 — GUI software control | click/drag in Premiere | **Deliberately not done** — FFmpeg-as-executor is far more robust than GUI automation |

## Decision

**Do not train a model on AVE now. Grow the operations DSL (Level 3) instead.**
Grounded in the project's own staging (`Kreator.md` §24: *integrate → specialize
by config/memory → train only where it creates unique value*):

1. Training an editing model is Phase 3 — premature before the rule-driven
   pipeline is validated.
2. The proposal's own JSON — `{instruction, assets, operations:[cut, zoom,
   subtitle, insert_broll, transition]}` — **is** the right DSL. Kreator's
   `EditPlan` is already a subset of it (the `cut` operation).
3. So: formalize that DSL, add an FFmpeg executor per operation, let the
   Director's rules decide the operations, and **validate cheaply**. Only if
   the rules plateau does training a model to emit the DSL (and the
   behavior-cloning idea) become worth it.

Level 4 (GUI control of Premiere/DaVinci) is explicitly avoided: GUI agents are
fragile and contradict the local/offline/robust goal.

## What gets built first (offline, user's footage only)

Operations that need **no external asset** and use only the creator's own
material — fully aligned with "Kreator is not a generative AI":

- **`subtitle`** — burn the transcript Kreator already produces (the creator's
  own spoken words), remapped onto the edited timeline. *(built + validated)*
- **`zoom`** — a punch-in on high-interest moments. *(next)*
- **`transition`** — crossfade between kept segments. *(next)*

Operations that need a **K Library** of free-to-use assets (`music`, `broll`,
`sfx`, `meme`) are defined in the DSL schema but deferred until that library
exists — and even then stay inside the rule: gameplay is 100% the creator's;
overlaid assets are real licensed files, never generated.

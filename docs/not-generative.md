# Kreator is not a generative AI

This is a hard, inviolable rule of the whole project — stated here plainly so it
is impossible to miss, in code and in docs.

**Every pixel and every sound in Kreator's output comes from the video the user
uploaded.** Kreator does not invent, fabricate, hallucinate, or pull anything
from outside the footage. It only *analyzes, selects, cuts, reorders, and
reassembles* the creator's own material.

## What Kreator does — and does not — do

| Kreator does (transforms real footage) | Kreator never does (fabricates) |
|---|---|
| Cut boring parts, keep the action | Generate a scene, character, or event that wasn't filmed |
| Reorder / condense real segments | Text-to-image / text-to-video of anything |
| Pick a real frame for a thumbnail, crop it, add text | Invent a facial expression, weapon, or setting |
| Transcribe the real dialogue that was spoken | Put words in anyone's mouth |
| Recognize what game it is, to edit it well | Change what actually happened |

Its understanding models (Whisper for speech, SmolVLM for scenes) are used only
to **describe** the real footage so the deterministic Planner can decide how to
cut it. They never generate output content. *The AI describes; the Planner
decides; the footage is the creator's.*

## The one allowed addition: free-to-use assets (opt-in)

Real editors add music, sound effects, and memes. Kreator supports this — but
only from a **K Library of licensed / free-to-use assets** the user added
deliberately (`assets/`), never generated and never scraped from someone else's
work. Today the Director can lay a background *music* bed from that library
under an edit; sound effects and memes follow the same rule when their
executors land. It all stays inside this same rule: the *gameplay* is 100% the
creator's, and any overlaid asset is a real, licensed file from the library —
not something a model dreamed up.

## Why it matters

- **Authenticity** — the thumbnail and the video show what actually happened, so
  the audience isn't misled.
- **Platform compliance** — this is structurally incapable of the
  "misleading AI imagery" violations platforms penalize.
- **Trust** — the creator's identity and footage are preserved, not replaced.

> Image work = a Photoshop editor on real frames. Never an image generator.

Full rationale: `Kreator.md` §4 (Core Philosophy — Zero Generated Images).

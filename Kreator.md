# Kreator
## The Operating System for Human Creativity

> *Human Creativity. AI Operations.*

---

**Author:** Johnny Kestler (pseudonym) — João Vitor Perazzolo
**Document type:** Unified specification — Product vision + Internal runtime architecture

---

## How to read this document

This is a single reference covering both what Kreator delivers to the user (Part I — Product) and how the system delivers it (Part II — Runtime). It is written to be useful for technical due diligence, not as a pitch: claims are stated at the confidence level the evidence supports, and the places where the design carries real, unresolved risk are named in the body rather than hidden.

The governing rule of the project: **models are commodity; infrastructure is not.** The durable value is not in owning the best vision or language model — those are superseded in months — but in an architecture that treats models as interchangeable components and delivers lower cost, higher speed, and stability.

Three structural tensions run through the design and have no clean resolution inside the current architecture. The document does not paper over them; it states each one where it lives, gives the partial mitigation, and marks what remains open:

- **Determinism vs. output variation.** The cache and audit economics require strict determinism; large-scale platform detection may require output variation. These pull in opposite directions (§8, §21, §15-RT).
- **Unit economics vs. GPU spot-price volatility.** The cost model is exposed to spot-price spikes at exactly the demand peaks that make the platform sustainable (§19, §8-RT).
- **The MVP's thin competitive wedge.** Stripped of memory, marketplace, and strategy, the Phase 1 product does not yet carry the differentiation the full platform vision promises (§18, §21).

One decision is deliberately left open rather than asserted: the GPU infrastructure base for the Cloud edition, whose cost/risk trade-off should be made with real peak-load data (§19).

---

# PART I — PRODUCT

Vision, philosophy, the K Agents, the business model, and the validation plan. This part describes *what* the user gets and *why* the project is positioned the way it is. Part II describes *how* the system delivers it.

## Table of Contents — Part I

1. [Overview](#1-overview)
2. [The Problem](#2-the-problem)
3. [The Solution](#3-the-solution)
4. [Core Philosophy](#4-core-philosophy)
5. [The Four Pillars](#5-the-four-pillars)
6. [The K Agents](#6-the-k-agents)
7. [System Architecture](#7-system-architecture)
8. [K Protocol — Coordination, Permissions, Determinism](#8-k-protocol)
9. [Trust Layers and Immutable Core](#9-trust-layers-and-immutable-core)
10. [Editions, Hosting, and the Kreator Network](#10-editions-hosting-and-the-kreator-network)
11. [Full Production Flow](#11-full-production-flow)
12. [K Intelligence — Market Intelligence](#12-k-intelligence)
13. [Editing Profile](#13-editing-profile)
14. [K Memory — Memory and Learning System](#14-k-memory)
15. [The Cold Start Problem](#15-the-cold-start-problem)
16. [Responsible Learning](#16-responsible-learning)
17. [K Store — Marketplace](#17-k-store)
18. [MVP — Initial Product](#18-mvp)
19. [Unit Economics — Cost per Video](#19-unit-economics)
20. [Platform Risks and API Dependencies](#20-platform-risks)
21. [Competitive Analysis and the Differentiation Wedge](#21-competitive-analysis)
22. [Creator Success Program](#22-creator-success-program)
23. [Roadmap](#23-roadmap)
24. [Evolution Toward Proprietary Models](#24-evolution-toward-proprietary-models)
25. [Long-Term Vision](#25-long-term-vision)
26. [Assumed Limitations](#26-assumed-limitations)
27. [Critical Assumptions and Validation Plan](#27-critical-assumptions)
28. [Brand Identity](#28-brand-identity)

---

## 1. Overview

**Kreator is not a content generator.**

It is an **operating system for digital content production.**

Its goal is to automate the entire operational workload of video creation without replacing human creativity. Content always originates from a real creator. The artificial intelligence observes, organizes, edits, optimizes, publishes, analyzes, and learns.

Where other platforms use AI to *replace* people, Kreator uses AI to **scale** people.

Creativity stays human. Style stays human. Artistic decisions stay human. The AI takes on only what computers do better: repetitive tasks, organization, execution, data analysis, and continuous optimization.

> *Kreator does not create creators. Kreator amplifies creators.*

One framing matters from the outset: for the first phase of the product, the amplification is mostly **operational time savings and good defaults**, not deep per-channel intelligence. The intelligence that makes Kreator hard to leave is a compounding reward that arrives later — it is not what the product delivers on day one. Claims in this document that depend on accumulated learning are marked as such where they appear (§15, §21, §26).

---

## 2. The Problem

### The creators' problem

In recent years, generative AI made it trivial to produce thousands of artificial videos. This created an enormous volume of synthetic content — often called *AI slop* — lowering the average quality of online content and eroding trust among creators, platforms, and audiences.

At the same time, authentic human creators face the opposite reality: the more they grow, the more operational demand they accumulate. Editing, thumbnails, SEO, scheduling, metrics analysis, comment replies — all of it consumes the time that should go to creation.

### The editors' problem

Professional video editors are capacity-limited by available time. The more clients they take, the harder it is to maintain quality and speed. Today there are only two ways out: hire more people, or work more hours. Neither scales efficiently.

### The market gap

There is a fundamental distinction no current solution addresses completely:

| Generative AI | Kreator |
|---|---|
| AI creates the content | The human creates the content |
| Synthetic videos | Real videos |
| Fake gameplay | Gameplay recorded by the creator |
| Synthetic voice as the protagonist | Synthetic voice as an optional tool |
| Channel *made* by AI | Channel *operated* by AI |

That last line is the thesis:

> **AI-generated content ≠ AI-operated content**

The market boundary must be stated bluntly. Tools already exist that perform *part* of this work from real footage — automatic Short clipping, reframing, captions. **That is a commodity today, and the best of these tools do it very well.** Kreator's gap is a different one: operating the **entire channel as a studio** — with memory, strategy, publishing, and a marketplace of editorial processes. But "operating the whole channel" is a Phase 2/3 capability. In Phase 1, Kreator competes in the commodity layer, and §21 is explicit about what that means for early positioning.

---

## 3. The Solution

Kreator proposes a third alternative to the creator's and editor's dilemma. Instead of replacing either, the system **amplifies their capacity.**

It works as a digital team of specialized **K Agents** that execute repetitive tasks while fully preserving the creator's identity.

The goal is never to create content from scratch. The goal is to **amplify real content.**

A useful analogy is a film production company: it has a director, an editor, a colorist, an audio operator, a social media manager, an analyst, and a manager. None of them creates the actor or the scene — all of them work on top of the filmed material. Kreator is exactly that: **a digital production company.**

### Supported content

Although the initial focus is YouTube (gameplay and Shorts), Kreator is designed to work with any original media the creator provides: recorded gameplay and streams, camera video and vlogs, podcasts and video interviews, classes and educational content, corporate video, and event/sports coverage.

The system requires no specific format — only that the content is authored by the creator or properly licensed by them.

### The creator sets the level of automation

**Example 1 — technical automation:** the creator uploads gameplay without narration and asks for dynamic editing, smart cuts, zooms, captions, sound effects from their personal library, and Short export. Nothing is invented — the agents only transform the uploaded material.

**Example 2 — production at scale:** the creator uploads 2 hours of video and asks the agents to identify the best moments, produce five Shorts, create a highlights video, and organize the final files. The entire process uses only the uploaded content.

**Example 3 — minimal refinement:** the creator uploads a raw vlog and asks only for pause removal, audio correction, captions, a thumbnail from a real frame, and publish prep. The content stays fully authentic.

### Interaction modes

**Guided Mode** — the creator picks options in the interface: output type, edit intensity, caption style, format, maximum duration, workflow, asset library, and publish destination.

**Conversational Mode** — as the agents mature, Kreator interprets natural-language instructions:

> *"Turn this GTA V gameplay into a ~30-second Short. Pick the funniest moment, use Editor X's K Workflow, add animated captions, memes from my library, subtle sound effects, and export vertical for YouTube Shorts."*

Selecting *the* best moment of a video is the hardest request in the entire system — a subjective editorial judgment. Kreator does not try to nail it alone on the first try: it delivers a **ranking** of candidates, each with the rationale for why it was chosen, and keeps the creator in control until the channel's memory learns their taste. The mechanics are detailed under [K Clipper](#k-clipper). §15 and §26 are explicit that in the cold-start period this ranking will often be mediocre, and that the friction of reviewing it is a real retention risk — not a solved problem.

### Every output stays grounded in the uploaded material

Regardless of automation level, one rule never changes. The K Agents only: analyze, organize, select, edit, synchronize, refine, optimize, and export.

No agent substitutes, fabricates, or invents content. Every produced video keeps the originally provided material as its exclusive base.

> *Kreator does not create content for its users. It amplifies the content they already created — removing repetitive operational tasks while preserving authenticity, authorship, and creative identity.*

---

## 4. Core Philosophy

### Human Creativity. AI Operations.

This is the project's foundational principle. It is not a marketing slogan — it is an **architectural constraint** that governs every system decision.

### Reality First Principle

Every K Agent must obey:

> *Always preserve the authenticity of the original content. Never fabricate events, gameplay, conversations, or situations that did not occur.*

In practice:

- K Voice cannot claim a win happened if the player lost.
- K Editor cannot create an explosion that never existed in the video.
- K Clipper cannot invent a highlight.
- K Thumbnail never synthesizes pixels that were not in the original video — not even to "improve" the image.

The system **never invents events**, never creates false stories, never fabricates gameplay, and never alters the meaning of what happened.

### Zero Generated Images

This is one of the project's most strategic positions — and, being a *policy* rather than a *technology*, it must be argued honestly rather than sold as a moat. It is not one: any competitor can adopt the same policy overnight with an internal memo. Its value is in brand integrity and platform-compliance posture, **not** in defensibility. It is kept because the compliance argument is real, not because it is a competitive wall.

**The inviolable rule:** Kreator never uses generative AI to *fabricate visual content that did not exist* — no agent asks a diffusion model to "generate" a scene, a setting, an expression, a character, a weapon, or an explosion that was not in the video.

Instead, the image agents work like an **experienced Photoshop editor**: they take real frames, crop, adjust color, apply contrast, detect the creator's face, remove or blur the background, compose two real frames, and add text, borders, and programmatic effects. All from pixels that already existed.

The correct boundary is not "use neural networks or not." It is between **two kinds of operation on pixels**:

| Allowed (transforms real pixels) | Forbidden (fabricates new pixels) |
|---|---|
| Cropping, reframing, composing real frames | Text-to-image generation of nonexistent scenes |
| Color, contrast, sharpness adjustment (Pillow/OpenCV) | "Imagining" a facial expression that never happened |
| Background removal/blur via segmentation (rembg) | Inserting invented objects, weapons, settings |
| Upscaling / denoising a real frame (super-resolution) | Creating a synthetic background |

Upscaling and denoising are acceptable because they **do not invent content** — they only increase the fidelity of pixels that already existed. Text-to-image does not.

In practice, the thumbnail pipeline is 100% programmatic from day one: real frame selection + Pillow + OpenCV + rembg + MediaPipe. When a visual quality boost is needed, only super-resolution over the real frame is used — never scene generation.

The consequence is stated plainly: a thumbnail composed of real frames may look slightly less "eye-catching" than a generator-made one. **This is a genuine competitive cost, not a neutral one.** It is treated as an open question in the validation plan (E3, §27), not asserted as a solved trade-off.

**Why the compliance argument holds (with real evidence).** YouTube's enforcement in 2026 does not ban aesthetic use of AI. It targets *misleading* imagery — thumbnails that exaggerate expressions, fabricate reactions, or insert false context that is not in the video. There are documented strikes for exactly this pattern. A pipeline that composes only from real frames is structurally incapable of producing that specific violation. So the principle is not "fear of AI" — it is avoidance of a **named, documented** enforcement category. What it does *not* do is guarantee reach or CTR; those remain the cost side of the trade-off.

Three reasons it matters:

**Audience authenticity.** The thumbnail shows what the video actually contains — reducing early abandonment and improving the satisfaction signals YouTube uses for organic distribution.

**Policy compliance.** YouTube requires thumbnails to represent content faithfully. An AI-generated thumbnail showing something never in the video can lead to penalization or demonetization. Thumbnails composed of real frames are intrinsically compliant against that specific rule.

**Genuine visual identity.** Professional editors do not generate thumbnails from scratch — they pick the best frame, work the image, and add channel text and style. Kreator does exactly that, automatically.

> *Image agents = Photoshop editors. Not image generators.*

---

## 5. The Four Pillars

### Pillar 1 — Human Content
Every video starts from material created by a real human. The creator is the source. The AI is the production team.

### Pillar 2 — AI Operations
A team of specialized K Agents takes on all operational work after recording: understanding, editing, publishing, analysis, and continuous optimization.

### Pillar 3 — Community Learning
The system evolves with its community. Creators and editors who wish to can voluntarily contribute to improving the agents, with explicit, transparent, revocable consent.

### Pillar 4 — Modular Intelligence
Intelligence does not belong to the models. It belongs to the system. If a better open-source model appears tomorrow, you swap a component. The innovation is not in owning the best LLM — it is in owning the best architecture for coordinating dozens of different models. This modularity extends to distribution itself: the user installs only the packages they need, via the **K Packages** model described in [§10](#10-editions-hosting-and-the-kreator-network).

---

## 6. The K Agents

Each **K Agent** has a single responsibility and works in coordination with the others — forming a specialized digital team. The user does not interact with one AI; they work with a full team of specialists, under the principle:

> **One Agent. One Responsibility.**

The system's intelligence emerges from their collaboration.

### K Orchestrator
**Role:** orchestrator / manager of the digital studio.

Receives the material after upload and distributes tasks to all other agents. Never edits video. Never writes scripts. Its only job is to **coordinate** — ensuring each agent gets the right information, at the right time, in the right order.

**Tools:** LangGraph (MIT) as the orchestration engine, implemented as a finite-state graph where each node is a processing step. Native checkpointing guarantees that on failure the pipeline resumes from the last stable point without reprocessing the raw video. Global project state travels in a unified object between nodes. For prototypes, CrewAI offers a gentler learning curve and can be ported to LangGraph later.

### K Analyst
**Role:** complete understanding of the video.

Does not process the whole video at once — no model does that reliably. Operates as a distributed system:

```
Video
  ↓ Automatic segmentation into 20–60s scenes
  ↓ VLM analyzes each segment individually
  ↓ K Memory saves each analysis
  ↓ LLM connects segments into a coherent narrative
  ↓ Complete temporal map of the video
```

Whoever understands the whole story is not a single model — it is the **chain of contexts** preserved by K Memory and connected by the LLM.

Final product — detailed temporal map:

```
00:02:31  Found a tank              Importance: medium
00:07:15  Unexpected explosion      Importance: high
00:15:41  Very funny moment         Importance: very high
```

**Tools:** Qwen2.5-VL 7B (Apache-2.0) as VLM; PySceneDetect (BSD-3) for segmentation; YOLO v8 for object/event detection (HUDs, kill icons, health bars); WhisperX for word-level timestamped transcription. For 2–3h videos, it operates in 20–30 min windows with overlap. The local LLM (Qwen3 or Llama 3 via Ollama) generates the final semantic map in JSON.

### K Clipper
**Role:** evaluate and rank the destination of each moment (Short / long video / discard) and assemble preliminary cuts.

Deciding what "deserves to become a Short" is a subjective editorial judgment, and Kreator treats it with design humility. Instead of imposing a single choice, K Clipper:

1. **Ranks, does not decide** — delivers the top-N candidates with per-signal scoring and rationale (hook, emotional peak, conflict, reveal, quotable line, visual energy).
2. **Keeps the human in the loop** for the first videos: the creator approves or rejects candidates, and each decision feeds K Memory.
3. **Calibrates per channel** over time, until the ranking converges with the creator's taste.

**Tools:** AI-Youtube-Shorts-Generator (MIT) as a transcription-based ranking base; Crispy for visual event detection in FPS/MOBA (kill feed, explosions, end-of-game screens); audio amplitude peaks as an additional trigger. Configurable offsets capture ~7s before and ~3s after each event. Overlapping clips are deduplicated.

**The retention risk this step carries.** The human-in-the-loop stage is the single largest early-retention risk in the product, and it is an open hypothesis (§15, E1 in §27), not a solved feature. The failure mode is concrete: for gameplay specifically, a creator who just recorded a 2-hour session often already knows where the two or three standout moments were. If the system's early rankings are irrelevant — which is the *default* before per-channel data accumulates — the cost of auditing mediocre suggestions can exceed the cost of scrubbing to a remembered timestamp manually. Whether reviewing N candidates is genuinely cheaper than manual clipping depends on the quality of the initial ranking and cannot be assumed. It is the first thing the MVP must prove.

### K Classifier
**Role:** categorize each cut (Epic, Funny, Scary, Bug, Fail, Highlight, Tutorial, Surprise, Tense, Competitive).

**Tools:** local LLM (Qwen3 via Ollama) receives the transcript slice + visual metadata and classifies into JSON; KeyBERT (MIT) extracts dominant terms. Output is persisted with the `segment_id` for later use by K Publisher and K Strategy.

### K Editor
**Role:** the editing itself.

Executes editing decisions with real tools:

```
Temporal map + Transcript
  ↓ LLM → understand context and intent
  ↓ VLM → confirm visual events
  ↓ FFmpeg → cuts
  ↓ K Library → select meme/asset
  ↓ FFmpeg → incorporate and export
```

Actions: zoom, cuts, transitions, effects, memes, music, captions, vertical framing. All elements come from the **K Library** — never from generators.

**Tools:** auto-editor (public domain) for the first pass (silence removal); FFmpeg for all deterministic operations (cuts, zoom, transitions, 9:16, composition); MoviePy as a high-level Python API. Audio normalization via auto-editor (`--edit audio:threshold=0.04`).

### K Subtitle
**Role:** generate and sync captions automatically.

**Tools:** WhisperX (faster-whisper + wav2vec2, BSD-2) with word-level timestamps, enabling word-by-word animated captions. Style (font, color, animation, position) defined by the channel's Editing Profile.

### K Voice
**Role:** narration (when applicable). Four modes: (1) no narration, (2) narration via generic AI, (3) creator's cloned voice with explicit authorization, (4) captions only.

**Tools:** Fish Speech (Apache-2.0) for monetized channels; XTTS v2 (CPML) for maximum cloning quality (from 6s of reference, 15s recommended; 17 languages with cross-lingual transfer); Kokoro-82M (Apache-2.0) for CPU operation in the MVP. In Mode 3, the reference recording is used as conditioning — no additional training.

**Detection-surface note.** A shared TTS voice signature across many channels is one of the technical-convergence vectors discussed in §21. Where narration is used at scale, the acoustic signature of a single open model (Kokoro/Fish Speech) is identical across unrelated channels — a real detection surface, partially mitigated by per-channel voice/seed variation (§21).

### K Motion
**Role:** visual effects and animations.

**Tools:** FFmpeg with `-filter_complex` for layer composition, animated overlays, shake, kinetic zoom, and transitions; MoviePy as abstraction. All assets come from the K Library — the agent does not generate effects from scratch; it selects, parameterizes, and applies existing resources per the Editing Profile.

### K Thumbnail
**Role:** programmatic thumbnail editor — **edits** images, does not generate them.

```
Selected real frame
  ↓ Face detection (MediaPipe)
  ↓ Smart crop (ideal composition)
  ↓ Background removal/blur (rembg / U2Net)
  ↓ Color, contrast, saturation adjustment (Pillow)
  ↓ Selective sharpening (OpenCV)
  ↓ Composition with a second real frame (optional)
  ↓ Channel template (Editing Profile)
  ↓ Text (Pillow + K Library fonts)
  ↓ Borders, glow, shadow (programmatic)
  ↓ Export in multiple versions
```

**What it never does:** create settings, expressions, characters, weapons, or items that did not appear in the video. The principle is detailed in [Core Philosophy](#4-core-philosophy).

**Tools:** VLM (Qwen2.5-VL) + CLIP (MIT) for frame selection; MediaPipe FaceMesh (Apache-2.0) for face detection; rembg (MIT) for segmentation; Pillow/PIL (MIT) and OpenCV (Apache-2.0) for programmatic editing; optional super-resolution over the real frame (no scene fabrication).

### K SEO
**Role:** discovery optimization — title, description, hashtags, and keywords aligned with channel style and K Memory performance patterns.

**Tools:** local LLM (Qwen3-14B or Llama 3 via Ollama/vLLM) with JSON output; DSPy (MIT, Stanford) for programmatic prompt optimization against channel history; KeyBERT for keywords; yt-dlp (Unlicense) for competitor metadata as reference.

**Detection-surface note.** SEO is the convergence vector that survives scrutiny most strongly (§21). If many channels use the same LLM with the same base prompt to generate titles and descriptions, the textual output can converge in a way detectable by semantic analysis — and, unlike visual output, this does not vary with the underlying gameplay, because the text is abstracted from it. **Per-channel prompt and temperature variation in K SEO is therefore a design requirement, not an optional tweak** (full reasoning and cost in §21).

### K Publisher
**Role:** channel publishing and management — schedule/publish, answer simple comments, update playlists, organize structure.

**Tools:** YouTube Data API v3 (Apache-2.0) via `google-api-python-client`; scheduling via `status.publishAt`; chunked upload with retry and exponential backoff.

Automated publishing depends on YouTube API quotas and terms, which makes the authentication architecture a sensitive point. §20 specifies how the quota actually works and why per-creator OAuth does not, by itself, raise the raw upload ceiling.

### K Validator
**Role:** automated authenticity verification before publishing.

Checks: are there unregistered assets? Is there artificially generated imagery? Is there a synthetic frame? Is there synthetic audio without explicit authorization? **If any check fails, the video is not published.**

**The boundary of what this can reliably guarantee.** "Detect a synthetic frame / AI-generated image" is not a reliable deterministic gate: robust detection of AI-generated imagery is an active, adversarial research problem, and current detectors have high false-positive and false-negative rates against modern generators. K Validator's guarantee therefore rests on a different mechanism. Its *reliable* function is verifying that every asset used is **registered in the K Library and cryptographically matches a known component** — a deterministic integrity check (see K Security). Its *best-effort* function is flagging suspected synthetic content for human review, which is useful but is not a guarantee and is not presented as one. The strong claim of authenticity comes from **provenance** — every pixel traces back through a signed chain to a registered real frame (Part II §9-RT) — not from a synthetic-content classifier.

### K Security
**Role:** system integrity — does not touch video.

Verifies digital signatures, hashes, permissions, sandbox isolation, and access control. Confirms that every Workflow, model, or library used is exactly the original, intact, unmodified component. Where K Validator guards *content* authenticity, K Security guards *platform* integrity. Detailed in [§9](#9-trust-layers-and-immutable-core).

### K Analytics
**Role:** monitor real video performance and track channel evolution.

**Tools:** YouTube Analytics API + Grafana (or Metabase / Superset). Feeds K Memory with CTR, retention, comments, shares, and timing.

### K Memory
**Role:** never produces — only remembers. The quietest agent and one of the most important.

Records everything: CTR per video, average retention, comments and sentiment, shares, timing, type/duration/theme, mood/music/thumbnail, titles and descriptions. Over time it discovers patterns invisible to manual analysis:

> Chase + under 28s + fast music + explosion before the 5s mark → **3× more views**

No one programs this pattern — K Memory discovers it. (See §15 for why this only becomes valuable after enough per-channel data exists.)

**Tools (3 layers):**
- **Agent memory:** Mem0 (Apache-2.0) for personalization and semantic retrieval; Letta (Apache-2.0) for long sessions.
- **Vector DB:** pgvector on PostgreSQL for early volumes; migration to Qdrant (Apache-2.0, Rust) at scale.
- **Knowledge graph:** Microsoft GraphRAG (MIT) + Neo4j Community (GPLv3), exposed as an MCP microservice. Enables questions like *"which thumbnails used cool tones in GTA V videos with CTR above 8%?"* without hallucination.

### K Scientist
**Role:** systematic experimentation (autonomous A/B tests).

> "Do red-background thumbnails increase CTR?" → creates two versions → publishes both → waits for data → compares → records the conclusion.

**Tools:** Arize Phoenix (MIT) for observability (OpenTelemetry traces); statsmodels + scipy.stats (BSD-3) for hypothesis testing; PyMC (Apache-2.0) for Bayesian inference with few videos per cohort. Each conclusion is stored in the graph with confidence metadata: `(duration<25s) -[CORRELATES_WITH]→ (retention: +12%, n=8, confidence: low)`. Low-n conclusions are treated as hypotheses to re-test — not as truths.

### K Strategy
**Role:** strategic direction of the channel. After months of operation, it knows the channel better than any external consultant:

- "Stop recording missions. Record chases."
- "Stop posting at 10am. Your audience responds better at 7pm."
- "This long-mission format lost steam — move to shorter cuts."

**Tools:** Prophet (MIT, Meta) for time series and seasonality; AutoGluon (Apache-2.0, AWS) as tabular AutoML to predict performance before recording; LightFM (Apache-2.0) modeling "what to produce next" as a recommender system; LangGraph to synthesize numbers into natural-language recommendations.

---

## 7. System Architecture

### Overview

```
Kreator
├── Base Models (Open Source)
│   ├── LLM (Llama, Qwen)
│   ├── VLM — Vision
│   ├── Whisper — Transcription
│   ├── TTS — Voice Synthesis
│   └── OCR — Text Reading
├── Tools
│   ├── FFmpeg — Video Processing
│   └── Vector DB — Semantic Memory
├── K Library — Collection of Authorized Media
├── K Registry — Index of Workflows, Models, Assets
├── K Validator — Content Authenticity Verification
├── K Security — System Integrity (hashes, signatures)
├── Channel Profile — Channel Profile
├── K Memory — Persistent History
└── K Agents (17 specialized agents)
```

### Intelligence levels

**Level 1 — General knowledge (pre-trained).** Open-source models already master language, vision, and audio. It comes "out of the box."

**Level 2 — Creator configuration.** The user answers a few questions that define the channel profile. This produces a configuration file — not a trained model.

```yaml
channel:
  niche: gta
  humor: high
  subtitles: energetic
  clip_length: 25
  narration: false
```

**Level 3 — Persistent memory.** Learning happens by recording facts, not by fine-tuning. After hundreds of videos, it accumulates real performance patterns.

**Level 4 — Feedback adjustment.** The user rates results (liked / disliked / too long). The system records preferences and applies them — no GPUs, no training.

### K Library

All media used by agents must be registered beforehand and is indexed by the Asset Registry (part of [K Registry](#9-trust-layers-and-immutable-core)). No agent has access to image-generation models.

```
✓ Frames captured from the original video
✓ Video and audio uploaded by the creator
✓ Memes from the personal library
✓ Licensed music
✓ Overlays, templates, fonts, sound effects, stingers
```

### Inter-agent communication

Agents do not exchange video files — only references (lightweight JSON payloads pointing to MinIO):

```json
{
  "task_id": "clip_001",
  "video_path": "/shared-scratch/raw-vods/session_01.mp4",
  "segment_start": "00:07:10",
  "segment_end": "00:07:22",
  "importance": "high",
  "category": "explosion"
}
```

For service-to-service calls, the system uses **MCP (Model Context Protocol)** — an open protocol letting one agent call another's tools in a standardized way. K Memory, for instance, exposes Neo4j queries as MCP microservices.

### Incremental execution

Kreator does not reprocess the whole video on every adjustment. When the creator changes a caption, swaps music, or trims two seconds, the system identifies exactly which steps depend on that change and re-executes **only what is necessary**, reusing everything unchanged from cache. This is what separates an edit that costs cents and seconds from one that costs minutes and dollars of GPU.

The boundary of this claim must be stated precisely, because a broad framing of it would be false:

- **The cache advantage is real for analysis and decision.** Not re-running the VLM (the dominant cost driver, §19) and ASR over an unchanged video is where the money is saved. Trimming a caption should never re-trigger the expensive understanding layer for that video.
- **Final rendering of a visual change is not free.** Burned-in captions and overlays must be fused into the pixel matrix, and FFmpeg cannot alter an encoded stream without re-encoding the affected frames. For a 30–60s clip this is *cheap* (seconds on CPU, cents) — but it is not *instant*, and "instant" is the bar users bring from CapCut/Premiere.
- **The correct fix for instant preview is not re-encoding faster — it is not re-encoding at all during editing.** Captions/overlays should live as a client-side vector layer (text + timestamp over canvas/CSS), with pixel burn-in happening once, asynchronously, only at final export. This is what every NLE does. Kreator's runtime already names the mechanism — the **Projection Engine** (separation of *projection metadata* from *projection pixels*) — and classifies it as future work (Part II, §13-RT). **The consequence: the MVP does not have the decoupling that would make interactive caption editing feel instant. The MVP interaction is approve/reject of pre-rendered candidates, not live editing, so this gap does not block the MVP — but "live editing" is a Phase 2 capability, not a Phase 1 one.**

The full engine (dependency graph, cache policy, invalidation) is specified in Part II.

### Deployment strategy

**Stage 1 — Docker Compose (single-node):** all services on one machine. Ideal for development and first creators.

**Stage 2 — Multi-node distributed:** GPU workers (VLM, TTS) on dedicated machines; communication via Redis Streams; FFmpeg rendering scales horizontally.

**Stage 3 — Kubernetes (multi-channel):** non-GPU workers scale via HPA; databases as StatefulSets; NVIDIA device plugin for per-pod GPU allocation; distributed MinIO.

---

## 8. K Protocol — Coordination, Permissions, Determinism {#8-k-protocol}

Dozens of K Agents may take part in one project, but none has the authority to freely alter another's work. Coordination is centralized in the **K Orchestrator**, which distributes tasks, controls permissions by least privilege, resolves dependencies, and validates every input and output. Each agent has a single responsibility and never communicates directly with another: all exchange passes through the orchestrator, which eliminates concurrent decisions and keeps system behavior predictable.

This coordination obeys a single principle, the **K Protocol**:

> No agent directly alters another's work. Each agent produces a structured artifact — analysis, timeline, metadata, recommendation, or validation — verified by the K Orchestrator before being consumed by the next.

In practice this brings Kreator closer to a microservices architecture than to a pile of chained prompts — it is what lets automation scale without turning into chaos.

Kreator also aims for **auditable reproducibility**: two projects run with the same material, the same configuration, and the same component versions produce equivalent results. With models running on GPU, bit-for-bit identity is infeasible, but fixed seeds, zero temperature where applicable, and complete version logging enable auditing, debugging, and controlled evolution.

**The determinism tension (read alongside §21).** This reproducibility is a genuine engineering virtue for caching and auditing. It is *also* the mechanism that, at scale, produces a shared technical signature across unrelated channels. Strict determinism (canonical parameters, fixed module versions) and output variation — needed to avoid mass-detection of coordinated automation — pull in opposite directions. This is one of the project's three structural tensions. It is not resolved; it is managed, and the management strategy and its limits are in §21.

The internal mechanism — execution contracts between modules, incremental execution engine, sandbox isolation, resource scheduler — is specified in Part II.

---

## 9. Trust Layers and Immutable Core

Kreator's integrity rests on a rigid separation between what is disposable and what is permanent. Each project runs in an isolated **Sandbox** that can be destroyed at the end without affecting anything; the platform core — models, Workflows, libraries, assets — is never altered in production. Components are not edited: they are **replaced by new versions.**

> **Everything is Replaceable. Nothing is Mutable.**

This principle delivers three product guarantees. **Versioning and audit:** nothing is overwritten — each update creates a new version and the previous one still exists, so any project can be reproduced or audited later. **Instant rollback:** if something breaks, the system just re-points to the previous version, rebuilding nothing — the same immutability model behind Git, NixOS, and Docker. **Verifiable integrity:** each component is identified by the hash of its own content and digitally signed, and **K Security** confirms, before each use, that what is running is exactly the original, intact component.

The role split is clear: **K Validator** handles *content* authenticity (Reality First, zero generated images, only registered assets — with the capability caveat in §6), while **K Security** handles *system* integrity. A direct consequence: if an attacker compromises an agent, the most they reach is a Sandbox — the core stays intact, because it is read-only.

The mechanism detail — content-addressed storage, K Registry, versioned database (MVCC), inter-process isolation — is in Part II.

---

## 10. Editions, Hosting, and the Kreator Network

Kreator is distributed as an operating system, not a monolithic app. The same agent architecture runs in different environments; what changes is the origin of resources and the place of execution.

### Editions: Cloud and Local

**Kreator Cloud** is the full ecosystem experience: continuously updated K Agents, K Marketplace, community-published Workflows, shared libraries, real-time market intelligence, cross-device sync, and distributed processing. Suited to those who want the platform's full collaborative potential.

**Kreator Local** runs everything on the user's machine — agents, libraries, own Workflows, compatible open-source models, database, and local memory. No content needs to leave the machine. Suited to those who prioritize privacy, control, and personalization, including specializing agents with their own data (old videos, projects, presets) fully offline. In exchange, features that depend on community licensing — commercial Workflows, licensed libraries, collaborative intelligence — may be unavailable in this edition.

Both editions share the same architecture, allowing projects to migrate between environments without reconstruction.

### K Packages

Installation is modular, like a Linux distribution. Instead of installing "all of Kreator," the user installs only what they need:

```
Kreator Core
├── K Orchestrator
├── K Memory
├── K Security
└── K Workflow Engine

+ K Video Pack
+ K Audio Pack
+ K Subtitle Pack
+ K SEO Pack
+ K Analytics Pack
+ K Market Intelligence Pack
```

Modularity reduces disk and memory footprint, allows updating or replacing a package without reinstalling the platform, and encourages the community to build compatible extensions. It is the concrete materialization of Pillar 4 — Modular Intelligence.

### Hosting models

Custom agents belong exclusively to their creators; the platform neither stores them nor assumes ownership. Each creator decides where to host their infrastructure.

**Self-hosted** — the creator runs their K Agents on their own infrastructure (personal computer, workstation, home server, NAS, VPS, or own cloud), keeping absolute control over models, libraries, Workflows, and availability.

**Kreator Cloud Hosting** — for those who do not want to administer infrastructure, the platform provides servers, scalability, monitoring, backups, and global availability. Even hosted on the official cloud, agents still belong to the creator; the platform acts only as an infrastructure provider.

The creator can migrate agents between environments at any time, without changing agent identity or services already contracted by users.

### The Kreator Network

The marketplace does not distribute agents — it distributes **access** to them. When a user contracts a Workflow or set of agents, they do not receive a copy of the system; Kreator establishes a secure connection to the infrastructure the creator defined, and all execution stays under the owner's control. The user receives only the result of authorized processing.

```
                 Kreator Network
                    Marketplace
                         │
        ──────────────────────────────────
        │               │                │
     Creator A       Creator B       Creator C
     (Self-Host)     (Cloud)          (NAS)
        │               │                │
     K Agents        K Agents        K Agents
```

This federation naturally protects intellectual property: models, parameters, and libraries never leave the creator's infrastructure, and there is no need to distribute proprietary models to thousands of devices.

### Two marketplace layers

The federation coexists with the Workflow marketplace described in [§17](#17-k-store) in a two-layer hierarchy:

- **Base layer — K Workflows.** Lightweight methodologies (parameters, rules, licensed libraries) executed by Kreator's standard agents. The simplest path for an editor to monetize their style without hosting anything.
- **Advanced layer — Federated Custom Agents.** The editor hosts their own agents, with proprietary models and logic, and the Kreator Network federates access. The path for those who developed their own intelligence and want to keep it under their control.

### Verifiable marketplace

Combining federation with the immutability described in [§9](#9-trust-layers-and-immutable-core), the buyer verifies the digital signature and checksum of a Workflow **before** executing it — even when it runs on the creator's own node. Trust does not depend on inspecting the content, but on cryptographic verification that the component is intact and authentic.

### What stays centralized

Most of the system is decentralized. Kreator centralizes only the services that need a single source of truth: user authentication, payments, licensing, agent discovery (registry), reputation and reviews, authorized usage logs, and billing. Even if a central service goes down, agents still belong to creators and can be migrated. This makes Kreator less an AI platform and more a network of creative agents, with the marketplace as a trusted intermediary between those who offer and those who use the services.

### Cost implication

The hosting model shifts where compute is billed. In the Cloud edition, processing cost is the platform's and enters the [Unit Economics](#19-unit-economics) model. In self-hosted, that cost moves to the creator, who in exchange gains full control and margin over their own hardware — a trade-off each profile resolves differently. **This matters for §19: the self-hosted path is also a partial hedge against the GPU spot-price volatility that the Cloud edition is exposed to, because self-hosted creators absorb their own compute at their own cost basis.**

### Philosophy

Kreator holds that creators should own the intelligence they develop. The platform does not centralize that knowledge: it provides the infrastructure to connect creators, agents, and users securely, scalably, and transparently. The ecosystem's value is not in owning the agents, but in letting each creator monetize their own infrastructure while keeping control of their work.

---

## 11. Full Production Flow

```
Creator records the video
        ↓ Automatic upload
   K Orchestrator receives the material
        ↓ K Analyst maps the video
        ↓ K Clipper selects/ranks cuts
        ↓ K Classifier categorizes
        ↓ K Editor produces versions
        ↓ K Subtitle generates captions
        ↓ K Voice generates narration (optional)
        ↓ K Motion adds effects
        ↓ K Thumbnail generates thumbnails
        ↓ K SEO creates title and description
        ↓ K Validator verifies authenticity
        ↓ K Publisher schedules and publishes
            ↓ YouTube
        ↓ K Analytics collects metrics
        ↓ K Memory records everything
        ↓ K Scientist experiments
        ↓ K Strategy learns
   The whole system improves
```

**Latency characteristics of this flow.** The flow is asynchronous by design: the creator uploads and does something else; the approval session is requested only when the batch is ready. That correctly avoids a blocking "loading screen," but it does not make the wait disappear — it relocates it. For 2h of gameplay, the VLM alone is estimated at 0.4–0.8h of GPU time (§19), plus ASR, plus batch rendering of candidates, before the first approval screen. That is minutes-to-tens-of-minutes of asynchronous wait — comparable to established competitors, *not* "instant." The consequences (unit-cost exposure under peak demand in §19, and whether this wait is competitive in §21) are addressed directly rather than defined away.

---

## 12. K Intelligence — Market Intelligence {#12-k-intelligence}

### Before creation

Most tools only help *after* the video is produced. Kreator accompanies the creator from the idea stage, with a continuously updated market-intelligence system.

### Market Intelligence Dashboard

Monitors public information from YouTube, Instagram, TikTok, Reddit, X, news, and search trends, presenting a consolidated view: growing niches, trending themes, best-performing formats, competitive average duration, publishing frequency, thumbnail types, title patterns, growing categories, and underexplored opportunities.

Answers high-value questions:

- Which niches are growing fastest this week?
- Which formats are saturated?
- Which opportunities have little competition?
- Which video type best matches my channel's history?
- If I record this video today, what is the estimated potential?

Generated continuously by K Strategy with browser-use and Crawl4AI, scanning public sources asynchronously.

Trend collection respects the legal and technical limits of platforms. Kreator prioritizes **official APIs** wherever they exist (YouTube Data API, public trend data) and treats scraping as a low-frequency complement, respecting robots.txt and terms of use. This is a source that requires continuous maintenance — not a set-and-forget component.

### Regional Intelligence System

All intelligence can be regionalized (specific country, global market, or multiple simultaneously). Recommendations reflect the reality of the creator's target market — not irrelevant global averages.

**Example:** long programming videos may grow in Brazil and fall in the US at the same time. Recommendations to a Brazilian creator reflect Brazil.

### Market Simulator

Before recording, the creator tests the viability of an idea:

> *"I want to record 2h learning Python for a Brazilian audience."*

```
Demand potential:        High
Competition level:       Medium
Niche growth (30d):      +18%
Most competitive format: Long videos (90–180 min)
Recommended time:        7pm–9pm (Brasília)
Estimated opportunity:   High
```

It does not guarantee success — it turns the decision into a data-informed choice, not just intuition. The final call always belongs to the creator.

### The full cycle

```
K Intelligence → Human Creation → Operation by K Agents
   → Publishing → Continuous Learning → K Intelligence (updated)
```

---

## 13. Editing Profile

### The style problem

Saying "my style is cinematic" teaches a system nothing. The challenge is turning **art into measurable data.**

### How the profile is extracted

The system **does not infer artistic intent** — that would be infeasible. It only **measures** an editor's real work and extracts objective parameters from edited videos, original projects, and timeline files (Premiere, DaVinci, Final Cut). It is statistics, not magic:

```
zoom_intensity:      0.35
cut_average_time:    2.8s
caption_style:       centered, animated
shake_level:         low
humor_density:       high
sound_fx_frequency:  1 every 18s
meme_frequency:      1 every 50s
music_volume:        0.18
```

**The extraction is not trivial, and the document does not treat it as such.** NLE project formats (XML/AAF/FCPXML) differ across versions and differ substantially from each other; mapping consistent, comparable editing parameters across three distinct tools is a non-trivial reverse-engineering effort with no reliable shortcut. It is a real engineering cost that must be scoped and estimated in Phase 2, not assumed. The pragmatic path is to start with a single format — or with Kreator-native edit logs — and expand coverage as demand justifies.

### The profile as an asset

This parameter set becomes the **Editing Profile** — the editor's digital creative identity, expressed as measurable data. If a creator wants videos "in Editor João's style," the system loads that editor's Editing Profile and executes editing following exactly that configuration.

**The fingerprint/fidelity conflict.** There is a hard, unresolved tension between two things this document promises — one of the project's three structural tensions. (1) The K Store sells the Editing Profile as a *precise, replicable* set of parameters — the buyer paid to reproduce a specific style, so the platform cannot secretly inject randomness into `zoom_intensity` or `cut_average_time` without adulterating the product. (2) YouTube's inauthentic-content enforcement flags channels whose *own uploads* are interchangeable with each other, and strict deterministic application of one Editing Profile makes a single channel's videos share the same editorial cadence across every upload. §21 carries the full analysis: why this is narrower than "1,000 channels get banned for buying the same profile" but is still a real per-channel risk, and where the mitigation actually lives — variation in layers *outside* the licensed profile (chiefly K SEO text and encoding metadata), never in the sold style parameters.

---

## 14. K Memory — Memory and Learning System {#14-k-memory}

### Channel Profile

All intelligence about a channel is centralized in a persistent file — `channel_profile.json`. Every agent consults it before deciding.

```json
{
  "preferred_short_length": 24,
  "best_upload_time": "19:00",
  "thumbnail_style": "high contrast",
  "favorite_intro": "explosion",
  "zoom_intensity": 0.35,
  "caption_style": "animated",
  "music_volume": 0.18,
  "peak_retention_topics": ["chase", "explosion", "humor"],
  "low_performance_topics": ["long missions", "tutorials"],
  "best_ctr_thumbnail": "face + text + red background"
}
```

This file is portable. Changed computers? Just copy it — and the channel "remembers" everything again.

### Each agent's architecture

```
Base Model (open source) + Prompt + Tools
  + Persistent memory + Channel Profile + Accumulated feedback
  = Specialized agent
```

There is no individual fine-tuning. What evolves is **knowledge about the channel** — not the models.

### Separating knowledge from behavior

K Voice does not need to learn Portuguese — it already knows it. It needs to learn speed, emotion, pauses, and tone. K Editor does not need to learn to cut videos — it needs to discover how much zoom to use, how long a meme lasts, when to place effects. This keeps the system light and efficient.

**A design requirement that follows from this.** Because every channel's `channel_profile.json` starts from the same niche defaults, channels that never customize would produce statistically similar output — which feeds the fingerprint concern in §21. Per-channel stochastic variation is therefore baked into the default profiles from day one: small randomized offsets in non-style-critical parameters, drawn per channel and fixed once so the cache is preserved. This is cheap, it does not touch a purchased Editing Profile's core parameters, and it reduces — without eliminating — the convergence-of-defaults surface.

---

## 15. The Cold Start Problem

Kreator's long-term differentiator is accumulated per-channel learning. That same differentiator creates an early-stage fragility the project acknowledges openly:

- A new channel has **few videos** → little statistical significance (as the K Scientist example shows, with `n=8` and low confidence).
- **Cross-channel** learning needs **scale** → which needs a working product → which needs the learning loop. The cycle feeds itself.

**Strategic conclusion:** per-channel learning **compounds over time** and cannot be the source of value on day 1. Initial value must come from elsewhere. The strategy has four levers:

**1. Niche priors (bootstrap).** Instead of starting "from zero," each new channel receives defaults derived from public heuristics and aggregated niche benchmarks (typical competitive duration, common posting times, thumbnail patterns). Not training on third-party content — just starting with an informed guess instead of a blank page.

**2. Marketplace Editing Profile.** A new creator can license an experienced editor's **Editing Profile** and get instant "good defaults" with no history of their own. This delivers immediate value and decouples the product from slow learning.

**3. Bayesian inference (PyMC).** Starts with the niche prior and updates per channel with each new video. With little data, the system is honest about uncertainty instead of faking certainty.

**4. Federated patterns with consent.** As the base grows (modestly), aggregated patterns across same-niche channels — with explicit consent — accelerate calibration of new channels.

In the first months, then, Kreator's value proposition is concrete and immediate: **time savings, good defaults, and marketplace workflows** — not "an AI that already knows your channel." Deep per-channel knowledge is a reward that arrives later, and it is precisely what makes the product hard to abandon long-term.

**The retention risk this creates.** The four levers above are the *supply* side — what the system offers a new channel. They do not by themselves neutralize the *demand*-side risk: that the cold-start rankings are simply not good enough to retain the user through the calibration period. For gameplay specifically (the MVP niche), the creator often remembers exactly where the standout moments were, and a mediocre ranking asks them to audit the system's guesses instead. Whether the review cost beats manual clipping is an empirical question (E1, §27) and the single most important thing the MVP must prove. The document does not treat it as already answered.

---

## 16. Responsible Learning

### Foundational principle

> **Consent before learning. Collaboration before collection.**

No third-party content is used to train agents without explicit authorization. The system does not depend on datasets obtained through indiscriminate scraping.

Default behavior:

> All content belongs to the creator and will be used exclusively to perform the requested service.

### Community Training Program

Fully optional contribution, always:

- **Explicit** — the creator decides consciously
- **Revocable** — can be withdrawn at any time
- **Transparent** — data use is clearly described
- **Granular** — the creator chooses exactly what to share (public videos, videos for research, metadata only, timelines only, statistics only, projects only, or nothing)

### Experts as teachers

Experienced creators can act as teachers: a professional editor shares editing projects; the agents learn patterns from examples voluntarily provided by real experts.

### Contributors Program

Those who share data may receive: early access to new agents, discounts, proportional compensation, and recognition. Intelligence grows through **voluntary collaboration**, not extraction.

---

## 17. K Store — Marketplace {#17-k-store}

### Editing Profile as a product

Every editor has their own style. Today that knowledge lives only in the editor's head and is sold as hours of work. In Kreator, it becomes a reusable, scalable digital asset: one editor can serve hundreds of creators. Instead of selling hours, **the editor sells their knowledge.**

### Phased launch strategy

The marketplace **does not exist at launch.** It is a consequence of the product's success — not the initial product.

- **Phase 1 — Personal tool:** prove the system works for a single creator.
- **Phase 2 — Partner editors:** invite 10–15 known editors to create the first Editing Profiles.
- **Phase 3 — Closed K Store:** by invitation, selected creators test the first styles.
- **Phase 4 — Public K Store:** open for any editor to register and any creator to choose.

### Philosophy — Processes, not People

The marketplace does not sell people, identities, or models trained to imitate them. It sells **K Workflows** — production methodologies and editorial processes of real professionals.

**What a K Workflow is:** editing rules, scene-selection logic, cut rhythm, caption placement, transitions, zoom intensity, timeline organization, meme criteria, sound-effect rules, thumbnail composition, SEO strategies, and licensed asset libraries.

**What is NEVER sold:** creators' synthesized voice, synthetic faces or avatars, videos generated to imitate someone, artificial personalities — any resource whose purpose is to reproduce an individual's identity.

> *Kreator believes a creator's identity should not become a product.*

### Compensation models

| Model | Description |
|---|---|
| Per processed video | Payment on each use of the K Workflow |
| Per hour of material | Based on the duration of edited content |
| Monthly subscription | Unlimited access to the K Workflow for a period |
| Corporate licensing | For high-volume teams and companies |
| Processing share | Percentage of the value generated |

### Two layers: Workflow and Custom Agent

The K Store operates in two complementary layers. In the **base layer**, what is licensed is the K Workflow — lightweight parameters and rules, executed by Kreator's standard agents, with no hosting required from the editor. In the **advanced layer**, editors who developed their own intelligence can offer **Custom Agents** hosted on their own infrastructure, federated by the Kreator Network. In both cases the knowledge stays with the author; only the level of sophistication and control changes. This hierarchy, along with the federation model and cryptographic verification of each item, is detailed in [§10](#10-editions-hosting-and-the-kreator-network).

**The marketplace's structural tension with platform detection.** A counterintuitive consequence deserves stating here and not only in §21: **the K Store's commercial success directly increases the platform-detection risk.** The product it sells is a precise, replicable editorial signature. The more channels license the same profile, the more channels share the same editorial cadence — and if they also share the same TTS voice and the same SEO-generation prompt, the shared surface grows. What narrows the risk (full analysis in §21): style-visual convergence across *unrelated* channels is not the documented detection vector — content/narrative repetition *within* a channel is, and licensed style parameters do not make unrelated channels' content identical. But the SEO-text vector is real and does not depend on content varying. The design consequence is already carried in §6 (K SEO) and §14: variation is introduced in layers the buyer did not purchase — SEO text, encoding metadata, small non-style offsets — never in the licensed style parameters. This mitigates; it does not fully resolve. It is an open risk under management, not a closed one.

---

## 18. MVP — Initial Product

The MVP is **intentionally small.** The goal is to prove the core concept — not build the full system before validating value.

### MVP scope

```
Gameplay recorded by the creator
  ↓ Video upload
  ↓ K Clipper ranks the best moments (human approves)
  ↓ K Editor edits with the user's assets
  ↓ K Subtitle adds captions
  ↓ K Thumbnail generates a thumbnail from real frames
  ↓ Upload to YouTube
```

### What the MVP explicitly excludes ("not now" list)

- K Store / editor marketplace
- K Scientist (A/B tests)
- K Strategy
- Voice cloning (K Voice mode 3)
- Automatic narration
- Automatic comment replies
- Multi-regional intelligence
- Knowledge graph (Neo4j/GraphRAG)
- Any generative image AI
- Live/interactive editing (requires the Projection Engine — Phase 2)

### MVP success criterion

> If a creator records a video, uploads it, and gets a Short **they would actually post** — with at most one candidate approval and zero manual editing — the MVP is a success.

The decisive test is not "the system ran." It is "**does the output pass the creator's editorial bar?**"

**The MVP wedge is thin, and the document is explicit about it.** This is one of the three structural tensions. The differentiation §21 leans on — accumulated per-channel memory, K Store, K Strategy — is *exactly* what the MVP excludes. Stripped of those, the Phase 1 product does structurally what an established auto-clipper (Opus Clip, Submagic) already does: ingest a long video, find moments, edit, produce Shorts — plus one human-approval step, and with an asynchronous wait that is at best comparable and plausibly worse, given per-segment VLM analysis. The only genuine Phase-1 difference is scheduled publishing (K Publisher), which the §21 table itself marks as merely "partial" even for competitors. **In Phase 1 the competitive wedge is thin, and the MVP's job is not to win on the wedge — it is to prove E1 (curation quality) and E2 (unit cost) cheaply, so Phase 2 can build the wedge on a validated foundation.** The wedge is a Phase 2/3 bet, not a Phase 1 fact; reading the MVP as already beating Opus Clip is a misreading.

All the MVP's value is in the **orchestration** — not in the individual models. The specific stack is in Appendix A.

---

## 19. Unit Economics — Cost per Video {#19-unit-economics}

The question that precedes any pricing strategy: **can a video be processed for less than it will be charged for?** No billing model makes sense without that answer, which is why unit economics is treated as a central part of the project.

### Cost model (main drivers)

Cost per video is dominated by **GPU-time.** Drivers, in order of weight:

1. **VLM (K Analyst)** — the most expensive; scales with video duration.
2. **ASR (WhisperX)** — moderate; scales with audio duration.
3. **Rendering (FFmpeg)** — CPU/GPU; scales with number of outputs and effects.
4. **TTS (K Voice)** — optional; only when there is narration.
5. **SEO/classification LLM** — cheap; short text.
6. **Storage + egress** — small per video, relevant at scale.

### Reference estimate

The estimates below constitute a reference model, to be replaced by real measurements during development. They orient the pricing decision, not as definitive numbers.

Scenario: **2h of gameplay → 5 Shorts + 1 highlight**, on rented community GPU (RTX 4090 / L4 ≈ US$ 0.40–0.80/h).

| Step | Estimated GPU-time | Estimated cost |
|---|---|---|
| K Analyst (VLM, frame sampling, overlapping windows) | ~0.4–0.8 h | US$ 0.20–0.60 |
| K Subtitle (WhisperX large-v2) | ~0.1–0.2 h | US$ 0.05–0.15 |
| K Editor + K Motion (FFmpeg, render of 6 outputs) | ~0.2–0.5 h | US$ 0.10–0.40 |
| K Thumbnail (programmatic, light) | ~0.02 h | < US$ 0.02 |
| K SEO / K Classifier (text LLM) | ~0.02 h | < US$ 0.02 |
| Storage + egress (per video) | — | US$ 0.05–0.20 |
| **Total (no narration)** | **~0.7–1.5 h GPU** | **≈ US$ 0.50–1.50** |

With retries, orchestration overhead, and a safety margin, a prudent initial ceiling is **US$ 2–4 per 2h video** on rented infrastructure. On owned hardware (amortized RTX 4090 + power), marginal cost falls, but fixed capital cost and idle time enter.

### Two cost items that must be priced explicitly

Two cost items are easy to omit and materially affect the model, so they are named here rather than left implicit:

**(a) Closed-GOP / segment-splitting storage overhead.** If the runtime moves to sub-clip re-encoding for faster incremental rendering, clean stream-copy concatenation requires cuts on I-frames, which means shorter, more frequent keyframes (closed GOP). This inflates bitrate and therefore storage and egress — the same trade-off every adaptive-streaming pipeline (HLS/DASH) already accepts. It is a *known, measurable* cost, not a blocker, and it belongs in the model. In the MVP it does not apply (approve/reject of whole pre-rendered clips), so it is a Phase 2 line item.

**(b) The compute-decoding surface of the VLM under real footage sampling.** The VLM cost range above (0.4–0.8h) is itself wide enough (a 2× spread) that any pricing decision built on it carries large error bars. The single largest cost lever remains intelligent frame sampling — not processing every frame — and measuring this on a real batch is the first engineering priority.

### The structural tension: GPU spot-price volatility under peak demand

This is one of the three structural tensions, and the model states it rather than assuming a static price.

Community/spot GPU markets do not run out of hardware under load — they respond by **raising the price**. Content production has strong daily seasonality (thousands of gameplay streamers finish and upload in the same evening window). At the scale that makes the platform sustainable, two things happen simultaneously at peak: demand for the platform spikes, and the spot price of the GPUs it depends on spikes. The §19 rule — "cost per video must sit comfortably below the price charged" — collides with this directly:

- If the platform pays the peak market rate to process immediately, margin can go negative at exactly the busiest hour.
- If it holds jobs in the queue until the spot price falls, the user waits — and the free-tier user (whose first video is a customer-acquisition cost) is the one most likely to be throttled at the moment they are evaluating the product.

**This is not a clean binary between "go bankrupt" and "make the user wait for days."** Neither extreme is the real operating point:

- The industry-standard answer is a **hybrid capacity model**: reserved/dedicated capacity sized to the baseline load, with spot/community GPU used only for peak overflow. This is how any production inference operation runs (reserved + on-demand + spot). It caps exposure to spot volatility at the margin instead of on the whole load.
- Free-tier expectations can be **explicitly tiered and communicated up front** ("your first video is ready within 24h") rather than promised as instant. Users tolerate asynchronous batch processing for compute-heavy free tiers when the expectation is set beforehand.
- The runtime's scheduler already carries `UserDemand` and `Deadline` priority factors (Part II, §8-RT), which give paying users priority over the queue under contention — a mechanism that exists in the design, though it is under-specified for the scale described here.

**The decision this document deliberately leaves open.** Whether Kreator Cloud's *base* runs on community GPU (lowest cost, highest volatility and privacy exposure), on hybrid reserved+spot (higher cost, realistic and stable), or on something in between is a business trade-off that should be made with real peak-load and real spot-price data, not asserted in advance. Both paths are viable; they price differently and carry different risk. The position the model takes: **the unit-economics table above assumes the low-cost community base, and that assumption is the single biggest source of optimism in it. If the base becomes hybrid, the per-video cost rises and the pricing floor rises with it.**

An additional, non-trivial risk of the community-GPU base, independent of price: sending gigabytes of a creator's original, unpublished footage to unaudited third-party nodes is a real IP-confidentiality exposure, and inter-node egress of raw multi-gigabyte video can itself exceed the compute cost. Both are reasons the hybrid or reserved path may be worth its higher sticker cost — a judgment left open here.

### The decision rule

> **Cost per video must sit comfortably below the price charged, with margin to support the "first video free."**

If the first video is free (§22), each new creator costs ~US$ 0.50–4.00 of acquisition in compute (more if the base is hybrid). This is sustainable **if** the conversion rate to paying is reasonable. Sanity check:

- Cost of free video: ~US$ 2 (community base) / higher on hybrid
- Conversion to paying: 20%
- Effective acquisition cost per paying user: ~US$ 10 in compute
- Price per paid video must cover this + margin + its own processing cost.

The ~US$ 10 figure above is *compute-only*. True customer-acquisition cost includes marketing, support, and amortized engineering, and is meaningfully higher — the compute figure is an acquisition floor, not the full cost. Calling it "CAC" without that qualifier understates the real number.

### Cost-reduction levers

- **Intelligent frame sampling** in the VLM (not processing every frame) — the single largest lever.
- **Quantization** (4-bit/8-bit models) to fit a smaller GPU.
- **Batching** queue tasks (Redis) to maximize GPU occupancy.
- **CPU for what fits** (Kokoro TTS, Pillow/OpenCV, databases).
- **Cache** of per-segment analysis (reuse across Shorts of the same video).

Measuring real end-to-end cost on a batch of videos is one of the first engineering priorities, and its results replace this section's estimates with actual numbers.

---

## 20. Platform Risks and API Dependencies

Kreator operates on third-party platforms, and a significant part of its operation depends on them. Mapping these dependencies and their mitigations is essential to the project's robustness.

### Risk 1 — YouTube Data API quota

The YouTube Data API v3 has a default quota (on the order of ~10,000 units/day per project) and **upload is expensive in units** — which sharply limits automated uploads.

The quota is allocated **per Google Cloud project** (per registered application), not per OAuth-authorized user. This distinction is critical and easy to get wrong: multiple creators authenticating into the same application **share the same project quota pool.** Per-creator OAuth correctly moves *authorization and consent* to each creator's own account — which is right and necessary — but it does **not** multiply the raw API quota. Any architecture that assumes per-user OAuth scales the upload ceiling is mistaken. Running many GCP projects to fragment quota is the kind of behavior that risks being treated as circumvention, and is not a path Kreator takes.

**Correct architecture (revised):**
- **OAuth per creator** for authorization/consent and per-account action attribution — kept, for the right reasons (the creator authorizes on their own account; actions are attributed to them).
- **Formal quota-increase request** via Google's official audit/compliance process (takes weeks, requires review; plan ahead). This — not per-user OAuth — is the actual lever for higher automated-upload volume.
- **Semi-assisted publishing** as a first-class fallback, not a footnote: the system prepares everything (video, thumbnail, metadata, scheduling) and the creator confirms the upload — reducing critical quota consumption and keeping the human in control.
- **Scheduling via `status.publishAt`**, no browser automation.

This is validated as E4 (§27) with a real measured quota cost per upload, because the whole automated-publishing story depends on it.

### Risk 2 — The inauthentic-content / coordinated-detection surface

This is the platform-side face of the determinism tension (§8, §21). YouTube's 2026 enforcement evaluates **whole channels** for content that is "template-driven," "mass-produced," or "easily replicable at scale," and there have been large enforcement waves against automation networks. The precise contours, from documented policy and enforcement:

- The primary documented trigger is **within-channel** repetition — a channel whose own uploads are interchangeable in structure and content.
- Networks of channels are flagged mainly around **engagement manipulation and coordinated deceptive content**, not around sharing an editing aesthetic.
- Shared *style* (LUTs, motion packages, editing templates) is used by tens of thousands of unrelated creators without mass bans, because their underlying content differs.

**What this means for Kreator:** the risk is real but narrower than "buying the same Editing Profile gets everyone banned." The concrete exposures are (a) a single channel applying a profile so rigidly that its own videos become interchangeable, and (b) the SEO-text and TTS-voice vectors that converge across channels *independently of content*. Mitigations are per-channel content variation (which gameplay naturally provides — each session differs physically), per-channel SEO prompt/temperature variation (a design requirement, §6), and voice variation where narration is used at scale. **None of these fully eliminates the surface, and the K Store makes it worse as it succeeds (§17). It is a risk under management — not a solved one.**

### Risk 3 — Other platforms

- **Instagram:** automated publishing requires Graph API with a Business/Creator account and has its own limits.
- **TikTok:** the Content Posting API requires approval and has usage restrictions.
- **Implication:** K Publisher's multi-platform support is phased — YouTube first, others as API approval permits.

### Risk 4 — Native platform competition

YouTube, TikTok, and Instagram already offer (or are building) native tools for Short generation, captions, and editing. This pressures the "clipping" layer. **Mitigation:** Kreator does not compete on the isolated feature — it competes on the **channel-operation layer** (memory, strategy, marketplace, multi-channel publishing), which platforms have no incentive to build. (This mitigation is real for Phase 2+; in Phase 1 the clipping layer *is* most of the product — see §18 and §21.)

### Risk 5 — Scraping for K Intelligence

Layout changes, rate limits, and ToS make scraping fragile. **Mitigation:** prioritize official APIs, treat scraping as a low-frequency complement, and budget continuous maintenance.

---

## 21. Competitive Analysis and the Differentiation Wedge {#21-competitive-analysis}

### The real competitors already exist

Tools like **Opus Clip, Vizard, Submagic, Klap, and Descript** already do, today, from real footage: moment detection, Short cutting, automatic reframing, animated captions, and even thumbnails. "Automatically cut real video" **is no longer a differentiator** — it is a commodity, and Opus Clip in particular does it very well.

| Dimension | Opus Clip / Vizard / Klap | Submagic | Descript | **Kreator** |
|---|---|---|---|---|
| Real-footage clipping | ✅ Strong | Partial | ✅ | ✅ (parity is the goal, not a win) |
| Animated captions | ✅ | ✅ Strong | ✅ | ✅ |
| Per-channel memory | ❌ | ❌ | ❌ | ✅ (accumulative, Phase 2+) |
| Channel strategy | ❌ | ❌ | ❌ | ✅ (K Strategy, Phase 2+) |
| Publishing + channel management | Partial | ❌ | ❌ | ✅ (K Publisher) |
| Editorial-process marketplace | ❌ | ❌ | ❌ | ✅ (K Store, Phase 2+) |
| Self-host / data control | ❌ (closed SaaS) | ❌ | ❌ | ✅ (open-source stack) |
| Zero generated images (compliance posture) | Varies | — | — | ✅ (policy, not a moat) |

Two things about this table are deliberate. First, the Kreator column does not imply day-1 superiority: the items that constitute the wedge are marked Phase 2+, because the MVP excludes them (§18). Second, real-footage clipping is marked "parity is the goal" rather than a win — the reasoning is developed at the end of this section.

### The specific wedge ("why not Opus Clip?")

The differentiation **cannot** be "we don't generate images" alone — it is too thin, because Opus also cuts real video, and the no-generation stance is a copyable policy (§4). The real wedge is the sum of four things no competitor delivers together:

1. **Operating system, not tool.** Opus Clip delivers clips. Kreator operates the channel: understanding → editing → publishing → analysis → strategy → memory. The difference between an app and a studio. **(Phase 2+; not present in the MVP.)**

2. **Accumulated per-channel learning (temporal moat).** Each video makes the next one better *for that specific channel*. SaaS competitors treat every client the same. **(Compounds over time; see §15 for why it is worthless on day 1.)**

3. **K Store — Editing Profile marketplace.** A business model that turns editors' knowledge into a licensable asset and creates a two-sided ecosystem. No competitor has this. **(Phase 2+.)**

4. **Data control and cost via open-source / self-host stack.** For creators and studios that will not hand footage to a closed SaaS, and for Kreator to control its own unit cost.

**The state of the wedge, precisely.** Points 1–3 are exactly what the MVP does not ship. Point 4 is real from day one but is a niche appeal, not a mass one. **So in Phase 1 the defensible wedge is genuinely thin.** The project is not "the MVP wins because it's an operating system" — the MVP is not yet an operating system. It is: the MVP exists to validate curation quality (E1) and unit cost (E2) cheaply, and the wedge is a deliberate Phase 2/3 build on top of a validated core. Presenting the wedge as a present-tense Phase-1 advantage would be an unsupported claim.

### The determinism ↔ detection tension, in full

This is the platform-facing consequence of the reproducibility the runtime requires (§8), and it deserves a complete statement because it connects three sections (§8, §14, §17) and the runtime's cache design (Part II).

**The mechanism.** The cache key is `hash(canonical_input, module_version, canonical_params)`. Canonicalization exists so that trivial parameter noise (`zoom=0.350001` vs `zoom=0.35`) does not destroy cache reuse *within a single video's edit lifecycle*. Two facts about this matter for the tension:

1. `canonical_input` is **per video** — every raw upload has a distinct content hash. The cache was never designed to share results *across* different videos or channels; a cache hit between Creator A and Creator B never happens, because their inputs are distinct hashes. So the cache does **not** force cross-channel output uniformity by itself.
2. What *does* converge across channels is (a) shared **defaults** in `channel_profile.json` for users who never customize, (b) a shared **TTS voice** where narration is used, and (c) shared **SEO-generation prompts** producing semantically similar text — this last one independent of the underlying gameplay.

**Why it is not the "inescapable paradox" a naive reading suggests.** Introducing entropy *between* channels (a per-channel or per-video random offset in style parameters, TTS seed, SEO temperature — drawn once, then fixed) does **not** break canonicalization, because canonicalization operates *within* a fixed video's edit lifecycle, not across videos. A drawn value of `zoom=0.37` is still canonicalized normally afterward; entropy enters at parameter *selection*, canonicalization guarantees stability of the *already-selected* parameter. They are different moments in the pipeline, not the same degree of freedom competing.

**Where the tension is genuinely unresolved.** The entropy that would most reduce fingerprint risk lives partly *inside* the space of parameters the K Store sells (cut cadence, zoom curve), and those cannot be randomized without adulterating a purchased Editing Profile (§13, §17). The boundary is therefore fixed: entropy can be freely added in layers *outside* the licensed product (SEO text, encoding metadata, non-style offsets, defaults for non-customizers) — a design requirement, and it helps — but it **cannot** be added to the licensed style parameters, which are exactly some of the behavioral signals a detector might key on. Whether the out-of-profile entropy is *sufficient* on its own is not something the document can assert; it depends on how platform detection weights style-cadence versus content versus text signals, which is not publicly documented. **It is an open risk under management, and the K Store's success makes it larger, not smaller (§17).**

The clipping quality is the entry ticket. Kreator must first *tie* the best auto-clippers on cut quality, then *win* on the operating-system layer — memory, strategy, marketplace, channel operation. An inferior cut would compromise the entire rest of the proposition; parity on cut quality is a non-negotiable goal of the first phase.

---

## 22. Creator Success Program

### Performance-based model

New creators should not take financial risk before knowing whether their content has potential. Therefore:

> **The first video processed by Kreator is always free.**

It works as a demonstration and lets them evaluate results with no commitment. The cost of this first video is a conscious customer-acquisition decision, sized in the [Unit Economics](#19-unit-economics) model — and, per §19, its true cost depends on the GPU infrastructure base, which is left open. Under the community base it is ~US$ 0.50–4.00 in compute; under a hybrid base it is higher, and the free-tier throttling policy under peak load (§19) is a real design decision, not an afterthought.

### Intelligent Benchmark

Success is not a fixed view count. Each niche has its own metrics. Before publishing, the agents build a reference model for that content type (niche, duration, format, platform, trends, audience behavior, recent similar-content performance). Each video is compared only with genuinely similar content.

### Creator Success Score

Before publishing, it generates a report with expected reach, likely view range, engagement potential, estimated retention, and niche competitiveness. Afterward, it compares real performance to the benchmark. The **Creator Success Score** is a proprietary metric of performance *relative to the niche market* — not absolute.

**An internal tension to keep in view.** The Score optimizes CTR and retention, while §4 accepts that programmatic thumbnails may under-perform generator-made ones on CTR. This is a genuine tension, not a resolved one: if the Zero-Generated-Images thumbnail hurts the very metric the Score optimizes, the trade-off must be measured (E3), and the principle held only if the CTR cost is acceptable in practice. The trade-off is not claimed to be already favorable — it is claimed to be testable.

### Billing model

The first video is free. If the Score indicates it hit/exceeded the niche expectation, the creator contracts services for future videos.

> *Kreator demonstrates its value before charging for it. It grows only when its creators grow too.*

---

## 23. Roadmap

### Phase 1 — Integrate, don't train
**Goal:** validate the orchestration of existing models — and, critically, validate curation quality (E1) and real unit cost (E2).
- MVP with gameplay and Shorts
- Basic analysis and editing pipeline
- Initial Channel Profile
- YouTube publishing (per-creator OAuth for consent; quota via official increase process, §20)
- **Real unit-cost measurement**

No training. Only integration. **No competitive wedge yet — this phase buys validated foundations, not market position (§21).**

### Phase 2 — Specialize, don't replace
**Goal:** deepen per-channel specialization — this is where the wedge is actually built.
- Full K Memory
- K Scientist with A/B tests
- Automatic Editing Profile extraction (scoped per §13 — non-trivial, start single-format)
- Closed K Store with partner editors
- Projection Engine (enables interactive/live editing)
- Other niches (vlog, education, podcast)

### Phase 3 — Train only where it creates unique value
**Goal:** proprietary models only where there is clear competitive advantage.
- K Strategy with deep history
- Public K Store
- Active Community Research Program
- Niche-specialized models

The recommended stack for each phase is in Appendix A.

---

## 24. Evolution Toward Proprietary Models

### Three-phase philosophy

> **Don't train what already exists. Specialize what already works. Build from scratch only where no alternative serves.**

This avoids the most common mistake in AI startups: burning scarce resources training models before validating the product. A multimodal model from scratch can cost tens of millions and require a dedicated research team. Integrating mature open-source models and concentrating innovation on orchestration is achievable with a small team.

One qualification: "achievable with a small team" applies to the *integration philosophy*, not to the full specified system. The full build — 17 coordinated agents, a custom incremental runtime, content-addressed provenance, a federated marketplace with cryptographic signing, a knowledge graph, Bayesian per-channel calibration, and a multi-platform intelligence scraper — is a large multi-year effort. The small-team claim holds only for the *MVP* (§18), which is deliberately a small slice. The rest is a staged build, not a small one.

### Phase 1 — Integrate (present)
Kreator uses only open-source models. Value is not in the models — it is in the architecture that coordinates them, the memory that learns, and the Channel Profile that preserves creator identity. If a 3× better VLM appears, you swap a component without rewriting the pipeline. Modular Intelligence in practice.

### Phase 2 — Specialize (medium term)
Specialization happens by configuration and memory — not training. `channel_profile.json` encodes preferences from hundreds of videos; feedback tunes parameters; K Scientist identifies winning combinations; Editing Profile extraction turns edit history into measurable parameters. No training GPU. The system learns by use.

### Phase 3 — Train (long term)
After years at scale, Kreator will have something no external lab replicates: **real production data authorized by the community.** With it, domain-specific models become possible:

- **Niche virality classifier**
- **Thumbnail CTR predictor** (over real impressions/clicks)
- **Title-based highlight detector** (clips annotated by creators themselves)
- **Channel-calibrated virality ranker**

### What is never built internally
General-purpose LLMs, generic VLMs, or general-purpose TTS. These categories have excellent open-source alternatives funded by billions. Proprietary development focuses on **domain-specific models** that generics do not solve well.

### Decision criterion
> A custom model only makes sense when the platform has enough data to train it with quality superior to the open-source alternative, and when that superiority generates measurable competitive advantage. Before that, integrating is always the right call.

---

## 25. Long-Term Vision

Kreator's goal is not to create videos automatically. It is to build the **infrastructure** that lets millions of creators produce authentic content with the efficiency of a large studio, without losing their identity.

The main asset stops being just the published videos. It becomes the **knowledge accumulated by the system**: persistent memory about audience, style, formats that work, ideal timing, retention patterns, and growth strategies. This knowledge makes each new video potentially better than the last.

### Three user profiles

- **Creators** — produce content and use the K Agents to automate channel operation.
- **Editors** — turn their style into reusable K Workflows, generating recurring revenue via K Store.
- **Developers** — build new agents, integrations, and plugins via the **K SDK**, expanding the platform.

### The scale of the future

Imagine the platform in five years: 50,000 active creators, 8 million videos processed, 5,000 editors in the K Store, 500 million edits. With that base, developing specialized models becomes possible with a unique advantage: all data volunteered by a community that believes in the project. **This is a vision, not a projection — every number here is illustrative and depends on the Phase 1 validations (§27) holding.**

---

## 26. Assumed Limitations

### What Kreator is not
- Not an AI video generator
- Not a "faceless" channel
- Not a replacement for human creators
- Not just another auto-editing tool
- Does not use generative AI to create images, thumbnails, or visual elements

### Assumed limitations

Kreator is explicit about what the automation does not do. The AI behind the K Agents is **probabilistic**: it errs, classifies with uncertainty, and does not understand artistic intent. So the system is deliberately **assistive, not autonomous** — the creator approves candidates, adjusts profiles, and keeps the final word, especially on subjective editorial decisions like choosing the best moment. An Editing Profile's parameters are measurable statistics, not an editor's "soul"; and prompts or methodologies are not, in isolation, protectable secrets — the defensible value is in execution, accumulated memory, and infrastructure, not in a prompt's text.

Four limitations are stated plainly rather than glossed:

1. **The MVP has a thin competitive wedge (§18, §21).** Its job is validation, not market victory.
2. **Automated publishing at scale is quota-constrained, and per-user OAuth does not by itself raise the ceiling (§20).** The real lever is an official quota increase plus semi-assisted publishing.
3. **Unit economics rests on a low-cost GPU base whose price is volatile under peak load (§19).** The infrastructure base is an open decision with a real cost/risk trade-off.
4. **The determinism the runtime needs for cache and audit is in tension with the output variation that platform-scale detection may require (§8, §21), and the K Store amplifies this as it succeeds (§17).** It is managed, not solved.

Stating these limits explicitly is what makes the rest of the document's promises credible.

### What Kreator is
An operating system for the creative economy, where AI works as a specialized team serving real creators and editors, preserving human authorship and turning creative knowledge into a scalable asset.

### Positioning

| Dimension | Generative AI | Channel automations | Kreator |
|---|---|---|---|
| Who creates the content | AI | AI | The human |
| Image origin | Diffusion | Generated or scraped | Real frames |
| Thumbnail | AI from scratch | AI creates/reuses | Programmatic edit of real frames |
| Authenticity | Synthetic | Partial | 100% authentic |
| YouTube compliance | Risk | Risk | Native (on the misleading-imagery rule) |
| Creator identity | Absent | Weak | Preserved |
| Per-channel learning | No | Generic | Specific and accumulative (Phase 2+) |
| Editor business model | Replaced | Ignored | Scaled and compensated |

### Why it is hard to copy
A competitor can use the same open-source models. What is **not** easily copied:
- A well-designed agent architecture
- Per-channel calibrated persistent memory
- Editing Profiles extracted from hundreds of real projects
- An ecosystem where creators and editors collaborate with consent
- Months or years of accumulated per-channel learning

The "zero generated images" decision is deliberately **not** on this list. It is a copyable policy (§4), not a moat. The genuine moats are the architecture, the accumulated memory, and the two-sided ecosystem — all of which take time to build, and none of which the MVP has yet.

> *Image agents = Photoshop editors. Not image generators.*

---

## 27. Critical Assumptions and Validation Plan {#27-critical-assumptions}

Kreator rests on assumptions that must be empirically proven before any investment in scale. This section lists them and the experiments that validate them, in priority order. The goal of the initial phase is to prove the core production loop works end-to-end — from recording to a publishable Short.

### E1 — Moment-curation quality
**Assumption:** K Clipper picks moments a creator would actually publish.
**Method:** process 10 real gameplays, generate the candidate ranking, and compare with a human editor's choices on the same material, measuring agreement rate.
**Success criterion:** majority agreement between the system's ranking and the human editor. This is the highest-impact assumption in the product and the first to be validated. **It is also the assumption the cold-start retention risk (§15) hangs on — if the ranking is poor, the review friction may exceed manual clipping, and the MVP fails its own success criterion (§18).**

### E2 — Real unit cost
**Assumption:** a video can be processed for less than it will be charged for.
**Method:** measure end-to-end cost of a batch of videos and fill the [Unit Economics](#19-unit-economics) model with real numbers — **including a peak-load run to observe spot-price behavior**, not just a happy-path single-job measurement.
**Success criterion:** cost per video comfortably below price, with slack for the first free video — under the chosen infrastructure base (§19).

### E3 — "Zero Generated Images" coherence
**Assumption:** the programmatic thumbnail pipeline delivers enough quality with no generative AI.
**Method:** generate programmatic thumbnails for 20 videos and compare CTR and perceived quality with manually made thumbnails.
**Success criterion:** acceptable quality that sustains the principle in practice. **This directly tests the §4/§22 tension: if CTR craters, the principle is costing more than it protects, and the trade-off must be revisited — not defended on philosophy.**

### E4 — API quota reality
**Assumption:** automated publishing is possible within YouTube's terms.
**Method:** validate the per-creator OAuth flow and **measure real quota consumption per upload against the per-project pool** (§20).
**Success criterion:** sufficient quota for the planned operation via the official increase process; otherwise, adopt semi-assisted publishing as the standing model.

### E5 — Wedge against direct competitors
**Assumption:** there is a clear reason for a creator to choose Kreator over an established auto-clipper.
**Method:** articulate and validate with real creators the differentiation described in [§21](#21-competitive-analysis) — **and be explicit that in Phase 1 this reason is largely a promise of the operating-system layer, not a present feature.**
**Success criterion:** creators recognize and value the platform layer as a reason to choose — knowing it arrives in Phase 2+.

The three highest-weight assumptions for the project's future are curation quality (E1), unit cost (E2), and the competitive wedge (E5). These concentrate validation priority in the first phase.

---

## 28. Brand Identity

Naming follows a consistent pattern:

| Concept | Name |
|---|---|
| Platform | **Kreator** |
| Agents | **K Agents** |
| Marketplace | **K Store** (or K Marketplace) |
| Memory | **K Memory** |
| Market Intelligence | **K Intelligence** |
| Analytics | **K Analytics** |
| Flows / Methodologies | **K Workflows** |
| Asset libraries | **K Library** |
| Development | **K SDK** |

### The identity idea (GPTs style)

Like OpenAI did with GPTs, the agents are treated as **team members**, not software features. People don't say "open the editor" — they say:

> *"Call K Editor."*
> *"Ask K Analyst to analyze this video."*
> *"K Strategy recommended I record a video about programming."*

### Slogan and philosophy

- **Philosophy:** *Human Creativity. AI Operations.*
- **Brand slogan:** *Kreator — The Operating System for Human Creativity.*
- **Variant (operation emphasis):** *Kreator — The Operating System for Content Creators.*

In the end, Kreator is not just an editor nor just an AI platform. It is the operational infrastructure connecting human creators to a team of **K Agents**, each specialized in a step of the creative process.

---
---

# PART II — RUNTIME

Internal architecture specification. This part describes *how* the system coordinates, executes, and versions the work of the media-processing modules. Part I described *what* the user gets; this describes the mechanism. It is a technical reference, not marketing material.

## Table of Contents — Part II

1. [Purpose and Principles](#1-rt-purpose)
2. [Layered View](#2-rt-layers)
3. [Signal Layer](#3-rt-signal)
4. [Evidence Layer](#4-rt-evidence)
5. [Planner — Deterministic Decision](#5-rt-planner)
6. [Execution Contracts](#6-rt-contracts)
7. [Incremental Execution](#7-rt-incremental)
8. [Scheduler and Resource Budget](#8-rt-scheduler)
9. [Versioning and Provenance](#9-rt-provenance)
10. [Marketplace Runtime](#10-rt-marketplace)
11. [K Agents → Modules Mapping](#11-rt-mapping)
12. [Runtime Scope in the MVP](#12-rt-mvp)
13. [Future Work](#13-rt-future)
14. [The Rendering and Preview Layer](#14-rt-rendering)
15. [The Determinism/Entropy Tension — Runtime View](#15-rt-tension)
16. [Technical Validation Plan](#16-rt-validation)

---

## 1. Purpose and Principles {#1-rt-purpose}

This part specifies Kreator's **runtime** — the layer that coordinates, executes, and versions the media-processing modules.

The engineering thesis is direct: **models are commodity; infrastructure is not.** Kreator's durable value is not in owning the best vision or language model — those are superseded in months — but in an architecture that treats models as interchangeable components and delivers lower cost, higher speed, and stability. When a better model appears, you swap the component without rewriting the pipeline.

Four principles govern every decision in this runtime:

1. **The AI classifies; the Planner decides.** Models provide probabilistic properties (labels, scores, transcriptions). No model decides what goes into the final video. The decision belongs to a deterministic Planner that receives evidence and applies explicit rules.
2. **Everything is a contract.** Each module receives an input contract and produces an output contract, with declared version and dependencies. No hidden side effects.
3. **Re-execute only what changed.** Full render on every edit is the behavior Kreator refuses to have. The runtime is incremental by construction. This applies fully to the analysis and decision layers; the final-render layer carries a physical re-encode cost that §14-RT specifies precisely.
4. **Nothing is overwritten.** Every change creates a new revision. History is immutable and auditable.

The bar for any addition to this runtime: does it reduce execution cost, reduce system complexity, improve user experience, or increase core reliability? If the answer is "no" to all, it does not go in.

---

## 2. Layered View {#2-rt-layers}

Video processing flows through layers with strict responsibilities. Deterministic signals are born first; probabilistic inference enters later, always over already-extracted signals; the decision comes last.

```
Raw Video / Audio
        │
        ▼
   Signal Layer        deterministic signals (VAD, OCR, scenes, optical flow, DSP)
        │
        ▼
   Evidence Layer      structured evidence (signals + model classifications)
        │
        ▼
     Planner           decides the execution plan from evidence
        │
        ▼
 Execution Runtime     executes the plan under contract, with incremental cache
   ├── Scheduler       orders work by priority, respecting resources
   └── Cache           reuses valid artifacts; materializes what is missing
        │
        ▼
  Provenance           versions and records the origin of each artifact
        │
        ▼
   Rendering / Preview  projects the final result (lazy) — see §14-RT
```

The Scheduler is not a parallel layer: it lives **inside** the Execution Runtime. The Planner produces the plan; the Runtime executes it, and the Scheduler is the Runtime component that decides order and resource use.

The central inversion versus the common market pattern is deliberate. Instead of `Video → LLM → Response`, Kreator does `Video → Signal Layer → Evidence → AI classifies → Planner decides`. This is cheaper (most work is deterministic and runs on CPU), more stable (inference operates over normalized features), and more auditable.

---

## 3. Signal Layer {#3-rt-signal}

The Signal Layer is the deterministic foundation of the whole system. All later inference is born here, and nothing in it depends on probabilistic models: the same input bits always produce the same signals.

Main components:

- **VAD (Voice Activity Detection)** — segments speech and silence; the basis for silence cuts and for triggering transcription only where there is voice.
- **Scene Detection** — detects scene cuts and transitions by frame difference (PySceneDetect).
- **OCR** — extracts on-screen text (HUDs, scoreboards, embedded captions).
- **Optical Flow** — measures motion intensity and direction; identifies action peaks.
- **Histograms and DSP** — per-frame color/luminance distribution and audio amplitude/energy analysis; detect abrupt changes, sound peaks, and visual variation.

The Signal Layer's output is a set of time series aligned to the video timecode. Being deterministic and cheap, it is computed once and heavily cached — every subsequent step consumes it instead of reprocessing the video.

---

## 4. Evidence Layer {#4-rt-evidence}

The Evidence Layer turns raw signals into **structured evidence** the Planner can consume. It is the boundary where probabilistic inference enters — but in a contained way.

An evidence's flow:

1. The Signal Layer delivers deterministic features (e.g., optical-flow peak at `00:07:15`, audio-amplitude peak at the same instant).
2. The models (VLM, ASR, classifiers) receive **only the relevant slice** pointed to by the signals — not the whole video — and produce labels with a confidence score (e.g., `event=explosion, conf=0.82`).
3. Signal + classification are reconciled into a single, normalized, versioned evidence:

```
Evidence {
  t_start: 00:07:10
  t_end:   00:07:22
  signals: { optical_flow_peak: 0.91, audio_peak: 0.88 }
  labels:  { event: "explosion", conf: 0.82, source: "qwen2.5-vl@<hash>" }
  evidence_id: <hash>
}
```

Normalization is what isolates the system from model non-determinism: continuous scores are reduced to stable ranges (*buckets*) and small changes do not flip the decision (*hysteresis*). So an irrelevant variation in a model's confidence between two runs does not change the plan — keeping behavior predictable even with probabilistic inference underneath.

There is a rule the Evidence Layer never violates: **evidence is always appended to Signal Layer observations and never redefines the physical limits of the signal.** A model may label what happens between `00:07:10` and `00:07:22`, but it cannot move, stretch, or invent those limits — they come from the deterministic signals. This prevents inference from "creating" segments that do not exist in the material.

**Connection to the intra-channel fingerprint concern (Part I §21).** Because the Evidence Layer normalizes events into stable buckets, the *editorial cadence* a given Editing Profile produces is highly consistent across a channel's videos. This is exactly what makes per-channel output uniform — desirable for style fidelity, problematic for platform detection. The runtime does not resolve this; §15-RT states where entropy can and cannot be injected without breaking the cache.

---

## 5. Planner — Deterministic Decision {#5-rt-planner}

The Planner is where decisions happen, and none of them is made by a model. It receives the evidence set and produces an **execution plan**: the ordered list of steps, with their modules, dependencies, and parameters.

The separation is strict:

- **The AI provides properties.** "This slice has 0.82 confidence of being an explosion." "This line is quotable." "This frame has a centered face."
- **The Planner decides.** "Promote this slice to a Short candidate." "Apply thumbnail template X." "Cut here."

The Planner's rules are explicit and versioned — not a prompt. Given the same evidence set and the same rules version, the plan is identical. This makes behavior testable: you can feed the Planner fixed evidence and verify exactly which plan comes out.

The Planner operates through an explicit cycle, not a direct jump from evidence to decision:

```
Evidence
   ↓ generate candidates    (from evidence and rules)
   ↓ score candidates       (per-signal score: hook, conflict, energy…)
   ↓ order                  (deterministic ranking)
   ↓ return ranking
   ↓ human chooses          (in subjective editorial cases)
```

Subjective editorial decisions (choosing the "best moment") are not resolved as a single truth: the Planner produces a **ranking** of candidates with per-signal rationale, and the human stays in the loop until the channel's memory calibrates the criterion. (The product rationale is in Part I, K Clipper — including the honest cold-start retention risk.)

---

## 6. Execution Contracts {#6-rt-contracts}

Every runtime module operates under a **contract.** The contract is what replaces prompt chaining with a verifiable service network.

A contract declares:

```
Contract {
  input:        input references (by hash)
  output:       type and schema of the produced artifact
  version:      module version + rules/parameters version
  dependencies: contracts this one depends on
  invariants:   conditions the output must satisfy
}
```

Properties contracts guarantee:

- **Boundary determinism.** A module reads no hidden state and writes nothing outside its declared artifact.
- **Safe composition.** The orchestrator (K Orchestrator, in product vocabulary) validates that a module's output satisfies the next module's input contract before chaining them.
- **Testability.** Each module can be tested in isolation against its contract, without bringing up the whole pipeline.

Contracts are the basis of incremental execution: because input, version, and dependencies are explicit, the runtime knows exactly when a prior result remains valid.

---

## 7. Incremental Execution {#7-rt-incremental}

This is the piece that most differentiates Kreator, and the hardest to copy. The industry pattern is `edit → render everything`. Kreator does `edit → identify dependencies → re-execute only what is needed`.

**Boundary of the guarantee, up front.** This section's guarantees are strongest for the *analysis and decision* layers and for *reuse of prior artifacts*. The one place they are weaker — final-render re-encoding of burned-in visual changes — is specified in §14-RT. The value of the cache is not diminished by that boundary, because the expensive work (VLM/ASR over the whole video) is exactly what the cache protects.

### Dependency graph

Each artifact is a node; each contract declares which nodes it depends on. The result is a DAG describing the entire production of a video. When something changes, the runtime walks the graph from the change point and marks as invalid only the nodes reachable downstream.

### Cache: hit, miss, materialization

An artifact's cache key **cannot** be derived from raw parameters — floats and irrelevant formatting would destroy reuse and contradict the stability principle itself. The key derives from a **canonical** form:

```
cache_key = hash(
  canonical_input,     // inputs referenced by hash, in canonical order
  module_version,      // module version + rules version
  canonical_params     // normalized parameters (floats in stable ranges)
)
```

Canonicalizing before hashing is what guarantees `zoom=0.350001` and `zoom=0.35` produce the same key. When executing a step:

- **Cache hit** — an artifact with the same key exists: reuse, zero cost.
- **Cache miss** — the key does not exist: execute the module and materialize the new artifact.

Because the key includes the module version, updating a model automatically invalidates only what depended on it.

**Critical clarification for the determinism tension.** `canonical_input` is **per video** — every raw upload has a distinct content hash. A cache hit between two *different* videos, or between two different creators, **never occurs**; the cache exists to reuse work *within a single video's edit lifecycle* (changing a caption should not re-run the VLM for that video). This is the fact that dissolves the naive "determinism makes entropy impossible" objection: entropy introduced *between* channels/videos at parameter-selection time does not touch canonicalization, which operates *within* a fixed video. See §15-RT.

### Invalidation

Changed the caption? Only the caption nodes and downstream render invalidate; video analysis, transcription, and thumbnail stay valid and come from cache. Swapped the transcription model? Transcription and everything depending on it invalidate, but the deterministic Signal Layer signals are preserved.

### Why it matters

The practical effect is economic and perceptible: reprocessing an adjustment costs **seconds and cents** of the *analysis* work instead of minutes and dollars of GPU. The re-encode cost of the *final render* for a visual change is separate and bounded — §14-RT. The core defensible advantage is that the whole video's *understanding* is never recomputed on an edit.

---

## 8. Scheduler and Resource Budget {#8-rt-scheduler}

The Scheduler orders work. It **does not try to be artistically smart** — that intelligence lives in the modules. It only schedules execution respecting resources and priority, and is an internal component of the Execution Runtime, not a separate layer.

Priority does not depend on "benefit" alone: it combines the factors that actually determine what to run first, over the estimated cost:

```
priority = ( UserDemand
           × DependencyCriticality
           × CacheImpact
           × Deadline )
           / EstimatedCost
```

Where:

- **UserDemand** — is the user waiting for this artifact now? (open timeline, thumbnail visible on screen)
- **DependencyCriticality** — how many other steps are blocked waiting on this?
- **CacheImpact** — will the result be reused by many other artifacts?
- **Deadline** — is there a deadline (e.g., scheduled publication)?
- **EstimatedCost** — estimated GPU/CPU/time cost of the task.

The benefit is always **operational**, never artistic.

The Resource Budget ensures scheduling respects the machine's physical limits: task queue, CPU, GPU, RAM, and VRAM. Heavy GPU tasks (VLM, TTS) are serialized or batched to maximize occupancy; CPU tasks (DSP, programmatic editing, databases) run in parallel. In the MVP, this is a priority queue with resource limits — not a universal planner nor a predictive VRAM budget (see §13-RT).

**Behavior under peak load (connects to Part I §19).** The `UserDemand` and `Deadline` factors give paying users priority over the queue under contention — the mechanism that lets a free tier be throttled to off-peak batch windows while paying users are served first. But the scheduler assumes a resource pool it can schedule *against*; it does not by itself solve the case where the *pool itself* becomes expensive at peak (spot-price spikes). That is an infrastructure-provisioning decision (hybrid reserved+spot vs. pure community), left open in Part I §19. The scheduler prioritizes within whatever pool exists; it does not create capacity.

---

## 9. Versioning and Provenance {#9-rt-provenance}

Nothing in the runtime is overwritten. Every change creates a new revision, and each artifact carries its full provenance. The philosophy is **append-only**: records are only added, never edited or removed — the same model behind Git, Kafka, and event sourcing, which makes all history naturally auditable.

### Provenance Database

Each inference and each artifact records:

```
Provenance {
  artifact_id: <content hash>
  model:       model name + version
  params:      parameters and seed
  contract:    contract version
  inputs:      input hashes
  evidence:    evidence that supported the decision
  timestamp
}
```

This guarantees **total auditability**: for any frame, caption, or cut in the final result, you can answer "which model, which version, which parameters, and which evidence produced this?"

**This is where the strong authenticity guarantee comes from.** As stated for K Validator (Part I §6), robust detection of *synthetic* content is unreliable, so the trustworthy guarantee is not "we detect fakes" but "every artifact provably traces, through this provenance chain, to a registered real frame and a signed component." Provenance plus content-addressing is the deterministic backbone; the synthetic-content classifier is best-effort on top. The "100% authentic" claim is defensible via provenance, not via a fake-detector.

### Content versioning

Each component's identifier is the **hash of its own content.** A single mechanism resolves, at once, versioning, deduplication, integrity verification, and rollback: if content changes, the id changes; if two artifacts share a hash, they are the same artifact. References are always by id and checksum — never by name.

In the MVP, versioning is an append-only table in PostgreSQL (revisions never overwritten). Full MVCC and large-scale content-addressed storage are treated in §13-RT.

---

## 10. Marketplace Runtime {#10-rt-marketplace}

The marketplace distributes **executable components** — not prompts, not copyable text. A marketplace item (an Editing Profile or a module) is packaged, versioned, and **digitally signed.**

At contract time:

1. The buyer receives the component by content id.
2. The runtime verifies signature and checksum **before** executing — even when the component runs on the creator's own infrastructure (federated model described in Part I §10).
3. Trust does not depend on inspecting the content, but on cryptographic verification that the component is intact and authentic.

The design consequence: because what is sold is a compiled, signed component and not a prompt, the asset is harder to copy and easier to license and revoke.

**What signing cannot fix.** Signing and verifying a component guarantees *integrity* — it is the real profile, unmodified. It does nothing about the *distribution* problem in Part I §17/§21: the more channels run the same signed profile, the more they share an editorial cadence. The runtime guarantees the buyer gets exactly what they paid for — which is precisely why it *cannot* silently vary the sold style parameters to reduce fingerprint. The only entropy the runtime can add is in unsold layers (§15-RT).

---

## 11. K Agents → Modules Mapping {#11-rt-mapping}

In the product, the user talks to a **team of K Agents.** In the runtime, each agent is a **deterministic module under contract.** The duality is intentional and follows the pattern of any mature platform: internally, components; externally, experiences.

| Product (experience) | Runtime (module) |
|---|---|
| K Analyst | Signal + Evidence Modules |
| K Clipper | Candidate Ranking Module |
| K Classifier | Semantic Classification Module |
| K Editor | Timeline/Edit Module |
| K Subtitle | Subtitle Module |
| K Voice | TTS Module |
| K Motion | Motion/FX Module |
| K Thumbnail | Thumbnail Composition Module |
| K SEO | Metadata Module |
| K Publisher | Publish Module |
| K Validator | Content Authenticity Module |
| K Security | Integrity/Signature Module |
| K Orchestrator | Scheduler + Contract Validator |

No module has autonomy: all receive contracts and produce contracts. The "team personality" exists in the product layer to make the system legible and memorable; underneath, behavior is deterministic and testable.

Four of the seventeen K Agents — K Analytics, K Memory, K Scientist, and K Strategy — do not appear in this table because they are not media-processing modules under an execution contract. They are the observation and learning layer: they read the outputs and metrics of the pipeline and write to persistent stores, but they do not transform media artifacts. They are specified on the product side (Part I §6, §14) rather than as runtime execution modules.

---

## 12. Runtime Scope in the MVP {#12-rt-mvp}

The MVP runtime is deliberately minimal. The goal is to prove the core — signal pipeline, Planner decision, and incremental execution — over few modules.

In the MVP:

- Signal Layer (VAD, scene detection, DSP; OCR and optical flow per niche).
- Evidence Layer with basic normalization (buckets + hysteresis).
- Deterministic Planner with explicit rules and candidate ranking.
- Execution Contracts between the Shorts-pipeline modules.
- Incremental execution with canonical-key cache (`canonical_input + module_version + canonical_params`) and graph invalidation.
- Priority queue scheduler with resource limits.
- Append-only provenance in PostgreSQL.

Not in the MVP (see next section): full MVCC, sophisticated CAS, high-performance IPC, complex Projection Engine, Time Chunk Architecture, and any general-purpose inference runtime.

**What this means for the interaction model.** Because the Projection Engine (§14-RT) is not in the MVP, the MVP interaction is **approve/reject of pre-rendered candidates**, not live editing of captions/overlays. The top-N candidates are rendered in batch at upload time, so the *rejection* loop has near-zero machine latency — the next candidate is already materialized. The wait that remains is the *initial* batch generation (VLM over the whole video + render), which is asynchronous (Part I §11/§19). The MVP does not promise, and does not need, instant interactive editing.

---

## 13. Future Work {#13-rt-future}

The items below are architecturally legitimate but belong to scaling phases — not the MVP. Adding them early would be the same overengineering the project avoids. Each enters only when real volume justifies it.

- **Full MVCC** over the timeline (today, simple append-only suffices).
- **Sophisticated Content-Addressable Storage** with block-level chunking and deduplication (today, per-artifact hash suffices).
- **High-performance IPC** (shared memory, Apache Arrow/Plasma) for tensor exchange between modules without serialization.
- **Projection Engine** with formal separation between *projection metadata* and *projection pixels* and advanced lazy materialization. This is the mechanism that enables instant interactive editing (Part I §7). It is Phase 2, and its absence is why the MVP is approve/reject rather than live-edit — it is what turns Kreator from a batch clipper into an interactive studio.
- **Time Chunk Architecture** — dividing video by structural blocks (not by frame or by silence) for fine-grained invalidation granularity.
- **Scheduler with predictive VRAM budget** and per-task deadlines.
- **Multi-node distributed execution** as the default (today, single-node with Docker Compose).

The admission bar stays the same: does it reduce cost, reduce complexity, improve experience, or increase core reliability? Without that, it stays out.

---

## 14. The Rendering and Preview Layer {#14-rt-rendering}

This section specifies the single most UX-relevant technical detail: how a visual change actually reaches the user's eyes, and what it costs.

### The physical constraint

Burned-in captions and overlays must be fused into the pixel matrix. Modern codecs (H.264/HEVC) compress most frames as inter-frames (P/B-frames) that depend on neighbors; a frame does not exist in isolation. Two consequences follow:

1. **FFmpeg cannot alter an encoded stream without decoding and re-encoding the affected frames.** Changing one word of a burned-in caption forces a re-encode of the affected span.
2. **Clean stream-copy concatenation requires cuts on I-frames (keyframes).** You cannot losslessly splice at an arbitrary 2-second boundary; cutting off a keyframe produces macroblock glitches and audio desync at the seams.

### Why "sub-chunk re-encode" is not a free lunch

A tempting optimization is to split a clip into short sub-chunks, re-encode only the affected one, and stream-copy the rest. This works *only* if the sub-chunk boundaries are keyframes. Forcing keyframes every ~2s (closed GOP) makes that possible — but it inflates bitrate, storage, and egress (the cost item added to Part I §19). This is the same trade-off adaptive streaming (HLS/DASH) already accepts for 2–6s segments; it is a *known, measurable* cost, not a novel breakthrough and not a blocker. It is Phase 2, because the MVP does not do interactive re-editing at all.

### The correct architecture for interactive editing: don't re-encode during editing

The right answer to "make caption editing feel instant" is not "re-encode faster." It is **don't burn pixels during editing at all**:

- During editing, captions/overlays live as a **client-side vector layer** (text + timestamp rendered over the video via canvas/CSS), exactly as Premiere, CapCut, and every NLE do. Changing a word is instant because no pixels are re-encoded — the change is a metadata edit rendered locally.
- Pixel burn-in happens **once**, asynchronously, only at **final export**.

This is the **Projection Engine** (§13-RT): a formal separation between *projection metadata* (the editable overlay description) and *projection pixels* (the final burned frames). It is Phase 2 work. Its absence is precisely why the MVP's interaction model is approve/reject of pre-rendered candidates rather than live editing.

### Honest statement of the MVP position

- The MVP does **not** offer live interactive editing, and does not need to — its interaction is candidate approval.
- Live editing is a **Phase 2** capability gated on the Projection Engine.
- When it arrives, caption/overlay edits are instant (metadata, client-side); only export re-encodes.
- The batch/candidate model means the machine latency of *rejecting* a candidate is near-zero (next candidate pre-rendered); the latency that remains is *initial* asynchronous batch generation (Part I §11/§19).

This is the technical detail that Part I §7's "cents and seconds" framing depends on being stated precisely: the analysis cache saves the expensive work; the render cost is real but bounded and, in the interactive case, deferred to export via the Projection Engine rather than paid on every keystroke.

---

## 15. The Determinism/Entropy Tension — Runtime View {#15-rt-tension}

The product-side statement of this tension is in Part I §21; what follows is the mechanism-level version, because the tension lives in the cache-key design specified in §7-RT.

### The two forces

- **Determinism is required by the cache.** The cache key `hash(canonical_input, module_version, canonical_params)` only reuses work if parameters are canonicalized to stable values and module versions are fixed. This is what makes incremental execution and audit possible.
- **Output variation may be required by platform-scale detection.** Part I §20/§21: platforms flag content that is template-driven and "easily replicable at scale." Identical editorial cadence, identical TTS voice, and identical SEO-text patterns across many channels form a detectable surface.

### Why the naive paradox is false

The claim "you need entropy to avoid detection, but entropy breaks the cache, so it's impossible" rests on a scope confusion. Canonicalization operates **within a single video's edit lifecycle** (`canonical_input` is per-video; cross-video/cross-channel cache hits never occur — §7-RT). Therefore:

- Entropy can be introduced at **parameter-selection time, per channel or per video** — a random offset in a style parameter, a TTS seed, an SEO temperature — **drawn once and then fixed** for that channel/video.
- Once drawn, the value is canonicalized normally. `zoom=0.37` (drawn) is cached identically to `zoom=0.370001` on re-edits of *that* video. Entropy enters at *selection*; canonicalization guarantees *stability of the selected value*. Different pipeline moments, not competing for the same degree of freedom.
- The cache is preserved because entropy is **not re-drawn on every re-render of the same video** — it is a fixed per-channel/per-video seed, not per-execution noise.

So entropy in the **defaults, TTS seed, SEO prompt/temperature, and encoding metadata** is free with respect to the cache.

### Where the tension is genuinely unresolved

The entropy that would most reduce the *behavioral* fingerprint (cut cadence, zoom curve) lives partly inside the **parameters the K Store sells.** Those cannot be randomized without adulterating a purchased Editing Profile (Part I §13/§17). The buyer paid for `cut_average_time: 2.8s`; the platform cannot secretly make it 2.6–3.0s jitter.

The boundary is therefore fixed as follows:

| Layer | Can inject entropy? | Cost |
|---|---|---|
| SEO text (prompt/temperature) | **Yes** | None to cache; this is the strongest lever and a stated requirement (Part I §6) |
| TTS seed/voice | **Yes** | None to cache; matters only where narration is used at scale |
| Encoding metadata / container flags | **Yes** | None to cache; weak signal but free |
| Default `channel_profile.json` (non-customizers) | **Yes** | None to cache; small per-channel offsets, fixed once (Part I §14) |
| **Licensed Editing-Profile style parameters** (cut cadence, zoom) | **No** | Would adulterate the sold product |

Whether the out-of-profile entropy is *sufficient* against real platform detection is **not determinable from public information** — it depends on how detection weights style-cadence vs. content vs. text signals. The runtime provides the *capability* to inject entropy cheaply in the unsold layers; it cannot guarantee sufficiency, and the K Store's success enlarges the behavioral-cadence surface it cannot touch. This is an open risk under management — the runtime's final position on it, matching Part I §21.

---

## 16. Technical Validation Plan {#16-rt-validation}

The runtime's technical premises are validated by their own experiments, complementary to the product experiments (Part I §27):

- **E1-RT — Signal Layer recall.** Do the deterministic signals capture the relevant events (does the Evidence Layer receive enough candidates)?
- **E2-RT — Cache efficiency.** What is the cache-hit rate in typical editing cycles?
- **E3-RT — Incremental latency.** How long does a small adjustment (caption, music) cost versus a full render — *measured separately for the analysis layer (should be near-zero) and the render layer (bounded re-encode, §14-RT)*?
- **E4-RT — Planner quality.** Given an evidence set, does the produced plan match a human editor's decision?
- **E5-RT — Cost per minute.** What is the GPU/CPU cost per minute of footage processed, end-to-end — *including a peak-load run per Part I §19*?
- **E6-RT — Recompilation time.** After swapping a model, how much of the pipeline must re-execute?
- **E7-RT — Stability.** Does normalization (buckets + hysteresis) keep the plan stable across runs with the same input? Until E7-RT runs, plan stability is a hypothesis, not a guaranteed property — and it is treated as such wherever the document relies on it.

The highest-weight experiments are E2-RT (cache efficiency) and E3-RT (incremental latency), because they directly sustain the cost-and-speed thesis that differentiates Kreator. Cost per minute (E5-RT) connects this part to Part I §19 — and its peak-load variant is what tests the unit-economics exposure that is the single biggest source of optimism in the model.

---

*Kreator — Human Creativity. AI Operations.*

*Unified Product + Runtime specification by Johnny Kestler (João Vitor Perazzolo).*

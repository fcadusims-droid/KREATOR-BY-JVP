# Using Kreator in GitHub Codespaces — step by step

This is the easy path: run Kreator's web app in the cloud from your browser,
upload a gameplay video, and download the edited result. No install on your own
computer, no GPU. You only need a GitHub account.

> The heavy lifting runs on the free Codespace machine (CPU). Editing is not
> instant — a long video takes minutes, and the optional "understand scenes"
> (VLM) option takes ~15 minutes. That's normal; the page shows live progress.

---

## 1. Open the repo in a Codespace

1. Go to the repository on GitHub.
2. Click the green **`< > Code`** button.
3. Open the **Codespaces** tab → **Create codespace on main**.

A browser editor (VS Code) opens. The first time, it runs a setup step that
installs ffmpeg and Kreator's dependencies — this takes **a few minutes**. Wait
until the terminal at the bottom stops working and shows a normal prompt.

*(If you don't see a terminal: menu **☰ → Terminal → New Terminal**.)*

## 2. Start Kreator

In that terminal, type this and press Enter:

```bash
python web/app.py
```

You'll see `Kreator web UI on http://0.0.0.0:5000`.

A small popup appears bottom-right: **"Open in Browser"** — click it. (If you
miss it, open the **Ports** tab next to the terminal, find port **5000**, and
click the 🌐 globe icon.)

## 3. Edit a video

The Kreator page opens in a new tab:

1. **Choose your gameplay video** (mp4/mov/mkv).
2. **Output quality** — pick 480p, 720p, or 1080p.
3. **How much to keep** — Balanced (~40%) is a good default; Aggressive makes a
   shorter, punchier cut.
4. **Understanding** (optional, slower):
   - *Keep dialogue moments* — transcribes speech so mission/story talk isn't
     cut. Adds a few minutes.
   - *Understand scenes (VLM)* — keeps scenic/briefing moments the motion+audio
     pass would drop. Much slower (~15 min).
5. Click **Edit my video →**.

A progress page shows each stage live (analyzing → [transcribing] →
[understanding scenes] → rendering). When it's done, click **⬇ Download edited
video**.

## 4. When you're finished

Stop the app with **Ctrl+C** in the terminal. To avoid using up your free
Codespace hours, **stop the Codespace** when done: on GitHub, open
**Codespaces** (top-left ☰ menu → *Codespaces*, or github.com/codespaces),
click the **⋯** next to yours, and choose **Stop codespace**.

---

## Optional: the VLM (scene understanding)

The "Understand scenes" checkbox needs an extra one-time install (it downloads a
~4.5 GB model). If you want it, run this once in the terminal before starting
the app:

```bash
pip install -r requirements-vlm.txt --extra-index-url https://download.pytorch.org/whl/cpu
```

Everything stays local to the Codespace — nothing is sent to any external
service.

## Prefer the command line?

You don't have to use the web UI. The same edit from the terminal:

```bash
python scripts/run_edit.py --video data/videos/yourclip.mp4 \
    --target-keep 0.40 --height 720 -o out/edited.mp4
# add --speech to keep dialogue, --vlm to understand scenes
```

## Troubleshooting

- **"ffmpeg: command not found"** — the setup step didn't finish; run
  `sudo apt-get update && sudo apt-get install -y ffmpeg`.
- **Missing Python package** — run `pip install -r requirements.txt -r requirements-web.txt`.
- **Port 5000 didn't open** — open the **Ports** tab, and make sure 5000 is
  listed; click the globe icon to open it.

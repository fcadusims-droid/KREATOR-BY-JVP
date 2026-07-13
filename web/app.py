#!/usr/bin/env python3
"""Kreator web frontend — upload a gameplay video, get an edited one back.

A small, self-contained Flask app: upload a video, pick the output quality
(480/720/1080p) and how much understanding to apply, and Kreator edits it
(cuts the boring parts, keeps the action, optionally keeps dialogue and
VLM-identified scenes) and hands back a finished MP4 to download.

Everything runs locally and offline — no GPU, no API. Start it with:

    python web/app.py            # then open the forwarded port (5000)

Processing is slow (especially the VLM), so each upload becomes a background
job with a live status page that polls until the download is ready.
"""

from __future__ import annotations

import sys
import threading
import time
import uuid
from pathlib import Path

from flask import (Flask, jsonify, redirect, render_template_string,
                   request, send_file, url_for)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from kreator.editor import Condenser, render_segments  # noqa: E402
from kreator.signal_layer import analyze_video  # noqa: E402
from kreator.speech import presence_series, transcribe  # noqa: E402
from kreator.types import format_tc  # noqa: E402
from kreator.vlm import (LocalVLMBackend, label_keyframes,  # noqa: E402
                         select_keyframes, visual_keep_series)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024 * 1024  # 4 GB uploads

WORK = ROOT / "web" / "_work"
WORK.mkdir(parents=True, exist_ok=True)

JOBS: dict[str, dict] = {}
_VLM = None  # loaded once, on first use


def _process(job_id: str, video_path: Path, opts: dict) -> None:
    job = JOBS[job_id]
    try:
        job["stage"] = "Analyzing video (motion, audio, scenes)…"
        bundle = analyze_video(str(video_path))
        has_audio = any(a > 0.0 for a in bundle.audio)

        speech = None
        if opts["speech"] and has_audio:
            job["stage"] = "Transcribing dialogue (Whisper)…"
            segs = transcribe(str(video_path))
            speech = presence_series(segs, bundle.times)
            job["dialogue_segments"] = len(segs)

        visual = None
        if opts["vlm"]:
            job["stage"] = "Understanding scenes with the local VLM (slow)…"
            global _VLM
            if _VLM is None:
                _VLM = LocalVLMBackend()
            kfs = select_keyframes(bundle, max_frames=opts["vlm_frames"])
            labels = label_keyframes(str(video_path), kfs, _VLM)
            visual = visual_keep_series(labels, bundle.times)
            job["scenes"] = [lab.to_dict() for lab in labels]

        job["stage"] = "Planning the edit…"
        plan = Condenser(target_keep=opts["target_keep"]).plan(
            bundle, speech=speech, visual_keep=visual)
        job["original"] = format_tc(plan.original_duration)
        job["edited"] = format_tc(plan.kept_duration)
        job["keep_pct"] = round(plan.keep_ratio * 100)
        job["segments"] = len(plan.segments)
        if not plan.segments:
            raise RuntimeError("nothing worth keeping was found — try a higher Keep %")

        job["stage"] = f"Rendering the edited video at {opts['height']}p…"
        out_path = WORK / f"{job_id}.edited.mp4"
        render_segments(str(video_path), plan, str(out_path),
                        has_audio=has_audio, height=opts["height"])

        job["out"] = str(out_path)
        job["stage"] = "done"
    except Exception as exc:  # surface any failure to the status page
        job["stage"] = "error"
        job["error"] = str(exc)
    finally:
        # The uploaded source is no longer needed once processing is over.
        video_path.unlink(missing_ok=True)


INDEX_HTML = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kreator — edit your gameplay</title>
<style>
 :root{color-scheme:dark}
 body{font-family:system-ui,sans-serif;background:#0e0f13;color:#e7e9ee;
      margin:0;padding:2rem 1rem;display:flex;justify-content:center}
 .card{width:100%;max-width:560px}
 h1{font-size:1.7rem;margin:.2rem 0}
 .tag{color:#8b93a7;font-size:.9rem;margin-bottom:1.6rem}
 form{background:#171922;border:1px solid #262a36;border-radius:14px;padding:1.4rem}
 label{display:block;font-weight:600;margin:1.1rem 0 .4rem}
 .hint{font-weight:400;color:#8b93a7;font-size:.82rem}
 input[type=file],select{width:100%;padding:.6rem;background:#0e0f13;
      color:#e7e9ee;border:1px solid #2b3040;border-radius:8px}
 .row{display:flex;gap:.6rem;align-items:flex-start;margin:.7rem 0}
 .row input{margin-top:.25rem}
 .seg{display:flex;gap:.5rem;margin-top:.3rem}
 .seg button{flex:1;padding:.55rem;border:1px solid #2b3040;background:#0e0f13;
      color:#e7e9ee;border-radius:8px;cursor:pointer}
 .seg button.on{background:#3b82f6;border-color:#3b82f6;color:#fff}
 button.go{margin-top:1.5rem;width:100%;padding:.8rem;font-size:1rem;font-weight:700;
      background:#3b82f6;color:#fff;border:0;border-radius:9px;cursor:pointer}
 button.go:hover{background:#2f6fe0}
</style></head><body><div class="card">
<h1>🎬 Kreator</h1>
<div class="tag">Upload a gameplay video. Kreator cuts the boring parts and keeps
the action — locally, offline, on CPU.</div>
<form method="post" action="/upload" enctype="multipart/form-data">
 <label>Your gameplay video <span class="hint">(mp4 / mov / mkv)</span></label>
 <input type="file" name="video" accept="video/*" required>

 <label>Output quality</label>
 <div class="seg" id="qseg">
   <button type="button" data-v="480" class="on">480p</button>
   <button type="button" data-v="720">720p</button>
   <button type="button" data-v="1080">1080p</button>
 </div>
 <input type="hidden" name="height" id="height" value="480">

 <label>How much to keep <span class="hint">(lower = shorter, punchier)</span></label>
 <select name="target_keep">
   <option value="0.25">Aggressive — keep ~25%</option>
   <option value="0.40" selected>Balanced — keep ~40%</option>
   <option value="0.60">Light — keep ~60%</option>
 </select>

 <label>Understanding</label>
 <div class="row"><input type="checkbox" name="speech" id="speech">
   <label for="speech" style="margin:0;font-weight:400">Keep dialogue moments
   <span class="hint">— transcribes speech, +a few minutes</span></label></div>
 <div class="row"><input type="checkbox" name="vlm" id="vlm">
   <label for="vlm" style="margin:0;font-weight:400">Understand scenes (VLM)
   <span class="hint">— keeps scenic/briefing moments, much slower (~15 min)</span></label></div>

 <button class="go" type="submit">Edit my video →</button>
</form></div>
<script>
 const seg=document.getElementById('qseg'), h=document.getElementById('height');
 seg.querySelectorAll('button').forEach(b=>b.onclick=()=>{
   seg.querySelectorAll('button').forEach(x=>x.classList.remove('on'));
   b.classList.add('on'); h.value=b.dataset.v;});
</script></body></html>"""


JOB_HTML = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kreator — processing</title>
<style>
 :root{color-scheme:dark}
 body{font-family:system-ui,sans-serif;background:#0e0f13;color:#e7e9ee;margin:0;
      padding:2rem 1rem;display:flex;justify-content:center}
 .card{width:100%;max-width:560px;background:#171922;border:1px solid #262a36;
      border-radius:14px;padding:1.6rem}
 h1{font-size:1.4rem;margin:.2rem 0 1.2rem}
 .stage{font-size:1.05rem;margin:1rem 0}
 .spin{width:34px;height:34px;border:4px solid #2b3040;border-top-color:#3b82f6;
      border-radius:50%;animation:s 1s linear infinite;margin:1rem 0}
 @keyframes s{to{transform:rotate(360deg)}}
 .stat{color:#8b93a7;font-size:.92rem;margin:.3rem 0}
 a.dl{display:inline-block;margin-top:1.2rem;padding:.8rem 1.4rem;background:#22c55e;
      color:#06240f;font-weight:800;border-radius:9px;text-decoration:none}
 a.back{display:inline-block;margin-top:1rem;color:#8b93a7}
 .err{color:#f87171}
 code{background:#0e0f13;padding:.1rem .35rem;border-radius:5px}
</style></head><body><div class="card">
<h1>🎬 Editing your video…</h1>
<div id="body"><div class="spin"></div><div class="stage">Starting…</div></div>
<a class="back" href="/">← edit another</a></div>
<script>
 const id="{{job_id}}";
 async function poll(){
   const r=await fetch(`/job/${id}/status`); const j=await r.json();
   const b=document.getElementById('body');
   if(j.stage==='done'){
     b.innerHTML=`<div class="stage">✅ Done!</div>
       <div class="stat">Original ${j.original} → edited ${j.edited}
       (${j.keep_pct}% kept, ${j.segments} segments)</div>
       ${j.dialogue_segments!=null?`<div class="stat">${j.dialogue_segments} dialogue segments kept</div>`:''}
       ${j.scenes!=null?`<div class="stat">${j.scenes.length} scenes analyzed by the VLM</div>`:''}
       <a class="dl" href="/job/${id}/download">⬇ Download edited video</a>`;
     return;
   }
   if(j.stage==='error'){
     b.innerHTML=`<div class="stage err">⚠ Something went wrong</div>
       <div class="stat">${j.error||''}</div>`; return;
   }
   b.innerHTML=`<div class="spin"></div><div class="stage">${j.stage}</div>
     ${j.original?`<div class="stat">Original length: ${j.original}</div>`:''}`;
   setTimeout(poll,1500);
 }
 poll();
</script></body></html>"""


@app.route("/")
def index():
    return render_template_string(INDEX_HTML)


@app.route("/upload", methods=["POST"])
def upload():
    f = request.files.get("video")
    if not f or not f.filename:
        return redirect(url_for("index"))
    job_id = uuid.uuid4().hex[:12]
    suffix = Path(f.filename).suffix or ".mp4"
    src = WORK / f"{job_id}{suffix}"
    f.save(src)

    opts = {
        "height": int(request.form.get("height", 480)),
        "target_keep": float(request.form.get("target_keep", 0.40)),
        "speech": request.form.get("speech") == "on",
        "vlm": request.form.get("vlm") == "on",
        "vlm_frames": 20,
    }
    JOBS[job_id] = {"stage": "queued", "created": time.time()}
    threading.Thread(target=_process, args=(job_id, src, opts), daemon=True).start()
    return redirect(url_for("job_page", job_id=job_id))


@app.route("/job/<job_id>")
def job_page(job_id):
    if job_id not in JOBS:
        return redirect(url_for("index"))
    return render_template_string(JOB_HTML, job_id=job_id)


@app.route("/job/<job_id>/status")
def job_status(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"stage": "error", "error": "unknown job"}), 404
    return jsonify({k: v for k, v in job.items() if k != "out"})


@app.route("/job/<job_id>/download")
def job_download(job_id):
    job = JOBS.get(job_id)
    if not job or job.get("stage") != "done" or not job.get("out"):
        return redirect(url_for("job_page", job_id=job_id))
    return send_file(job["out"], as_attachment=True,
                     download_name="kreator_edited.mp4")


if __name__ == "__main__":
    print("Kreator web UI on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, threaded=True)

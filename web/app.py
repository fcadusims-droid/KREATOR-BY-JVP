#!/usr/bin/env python3
"""Kreator web frontend — autonomous edit.

Upload a gameplay video and Kreator does the rest with **no options**: it looks
at the footage, works out what kind of game it is, picks an editing style for
that genre, and hands back a finished MP4 to download. Everything runs locally
and offline — no GPU, no API.

    python web/app.py            # then open the forwarded port (5000)

Processing is slow (the scene-understanding VLM especially), so each upload is a
background job with a live status page that polls until the download is ready.
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

from kreator.director import autonomous_edit  # noqa: E402
from kreator.types import format_tc  # noqa: E402
from kreator.vlm.backends import LocalVLMBackend  # noqa: E402

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024 * 1024  # 4 GB uploads

WORK = ROOT / "web" / "_work"
WORK.mkdir(parents=True, exist_ok=True)

JOBS: dict[str, dict] = {}
_VLM = None  # the VLM model, loaded once and reused across jobs


def _process(job_id: str, video_path: Path) -> None:
    job = JOBS[job_id]
    try:
        global _VLM
        if _VLM is None:
            _VLM = LocalVLMBackend()
        out_path = WORK / f"{job_id}.edited.mp4"

        def progress(stage: str) -> None:
            job["stage"] = stage

        result = autonomous_edit(str(video_path), str(out_path),
                                 progress=progress, vlm_backend=_VLM)
        job["result"] = {
            "label": result["label"],
            "preset_note": result["preset_note"],
            "original": format_tc(result["original_duration"]),
            "edited": format_tc(result["kept_duration"]),
            "keep_pct": round(result["keep_ratio"] * 100),
            "segments": result["segments"],
            "subtitles": result.get("subtitles", 0),
            "zooms": result.get("zooms", 0),
            "rationale": result.get("rationale", []),
            "scenes": len(result["scenes"]),
        }
        job["out"] = result["out"]
        job["stage"] = "done"
    except Exception as exc:
        job["stage"] = "error"
        job["error"] = str(exc)
    finally:
        video_path.unlink(missing_ok=True)


INDEX_HTML = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kreator — edit your gameplay</title>
<style>
 :root{color-scheme:dark}
 body{font-family:system-ui,sans-serif;background:#0e0f13;color:#e7e9ee;margin:0;
      padding:2.5rem 1rem;display:flex;justify-content:center}
 .card{width:100%;max-width:520px;text-align:center}
 h1{font-size:1.9rem;margin:.2rem 0}
 .tag{color:#8b93a7;margin:.6rem 0 2rem;line-height:1.5}
 form{background:#171922;border:1px solid #262a36;border-radius:14px;padding:1.8rem}
 input[type=file]{width:100%;padding:.9rem;background:#0e0f13;color:#e7e9ee;
      border:1px dashed #394054;border-radius:10px;margin-bottom:1.2rem}
 button{width:100%;padding:.95rem;font-size:1.05rem;font-weight:800;background:#3b82f6;
      color:#fff;border:0;border-radius:10px;cursor:pointer}
 button:hover{background:#2f6fe0}
 .steps{margin-top:1.4rem;color:#6b7280;font-size:.85rem;line-height:1.7;text-align:left}
 .steps b{color:#9aa3b2}
</style></head><body><div class="card">
<h1>🎬 Kreator</h1>
<div class="tag">Upload your gameplay. Kreator watches it, understands what game
it is, and edits it on its own — cutting the boring parts, keeping the action.
No settings. Local &amp; offline.</div>
<form method="post" action="/upload" enctype="multipart/form-data">
 <input type="file" name="video" accept="video/*" required>
 <button type="submit">Edit my video →</button>
 <div class="steps">
   <b>What it does, on its own:</b><br>
   1. Analyzes motion, audio and scenes<br>
   2. Recognizes the game/genre from what it sees<br>
   3. Picks an editing style that fits<br>
   4. Cuts the boring parts, keeps the action &amp; dialogue<br>
   5. Hands you the finished video to download
 </div>
</form>
<div class="tag" style="margin-top:1.4rem;font-size:.8rem">Kreator only uses
your own footage — it never generates or adds anything from outside.</div>
</div></body></html>"""


JOB_HTML = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kreator — working…</title>
<style>
 :root{color-scheme:dark}
 body{font-family:system-ui,sans-serif;background:#0e0f13;color:#e7e9ee;margin:0;
      padding:2.5rem 1rem;display:flex;justify-content:center}
 .card{width:100%;max-width:520px;background:#171922;border:1px solid #262a36;
      border-radius:14px;padding:1.8rem}
 h1{font-size:1.4rem;margin:.2rem 0 1.2rem}
 .stage{font-size:1.08rem;margin:1rem 0}
 .spin{width:34px;height:34px;border:4px solid #2b3040;border-top-color:#3b82f6;
      border-radius:50%;animation:s 1s linear infinite;margin:1rem 0}
 @keyframes s{to{transform:rotate(360deg)}}
 .stat{color:#8b93a7;font-size:.92rem;margin:.3rem 0}
 .note{color:#9aa3b2;font-size:.88rem;margin:.4rem 0 0}
 ul.why{text-align:left;color:#9aa3b2;font-size:.86rem;margin:.6rem 0;padding-left:1.1rem;line-height:1.5}
 a.dl{display:inline-block;margin-top:1.3rem;padding:.85rem 1.5rem;background:#22c55e;
      color:#06240f;font-weight:800;border-radius:10px;text-decoration:none}
 a.back{display:inline-block;margin-top:1rem;color:#8b93a7}
 .err{color:#f87171}
 .warn{color:#6b7280;font-size:.8rem;margin-top:1rem}
</style></head><body><div class="card">
<h1>🎬 Editing your video…</h1>
<div id="body"><div class="spin"></div><div class="stage">Starting…</div></div>
<div class="warn">Understanding the scenes takes several minutes — this page
updates itself, you can leave it open.</div>
<a class="back" href="/">← edit another</a></div>
<script>
 const id="{{job_id}}";
 async function poll(){
   const r=await fetch(`/job/${id}/status`); const j=await r.json();
   const b=document.getElementById('body');
   if(j.stage==='done'){
     const s=j.result||{};
     const why=(s.rationale||[]).map(r=>`<li>${r}</li>`).join('');
     b.innerHTML=`<div class="stage">✅ Done!</div>
       <div class="note">Kreator saw: <b>${s.label||''}</b></div>
       ${why?`<ul class="why">${why}</ul>`:''}
       <div class="stat" style="margin-top:.7rem">Original ${s.original} → edited ${s.edited}
       (${s.keep_pct}% kept, ${s.segments} segments, ${s.scenes} scenes analyzed)</div>
       ${s.subtitles?`<div class="stat">${s.subtitles} subtitles burned from the dialogue</div>`:''}
       ${s.zooms?`<div class="stat">${s.zooms} punch-in zoom(s) on the action</div>`:''}
       <a class="dl" href="/job/${id}/download">⬇ Download edited video</a>`;
     return;
   }
   if(j.stage==='error'){
     b.innerHTML=`<div class="stage err">⚠ Something went wrong</div>
       <div class="stat">${j.error||''}</div>`; return;
   }
   b.innerHTML=`<div class="spin"></div><div class="stage">${j.stage}</div>`;
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
    src = WORK / f"{job_id}{Path(f.filename).suffix or '.mp4'}"
    f.save(src)
    JOBS[job_id] = {"stage": "queued", "created": time.time()}
    threading.Thread(target=_process, args=(job_id, src), daemon=True).start()
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

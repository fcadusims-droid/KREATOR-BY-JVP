#!/usr/bin/env python3
"""Kreator web frontend — autonomous by default, guided when you want it.

Upload a video and Kreator edits it on its own (recognizes the content, picks
a style, cuts, captions). Optionally, guide it: ask for vertical Shorts, set
the cut intensity, choose the caption style — or just *type what you want* in
plain language and the deterministic parser fills the same form. One upload can
produce several deliverables (the full edit + N Shorts) from a single analysis.
Everything runs locally and offline — no GPU, no API.

    python web/app.py            # then open the forwarded port (5000)
"""

from __future__ import annotations

import os
import sys
import threading
import time
import uuid
from pathlib import Path

from flask import (Flask, jsonify, redirect, render_template_string,
                   request, send_file, url_for)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from kreator.director import JobRequest, parse_instruction, run_job  # noqa: E402
from kreator.vlm.backends import LocalVLMBackend  # noqa: E402

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024 * 1024  # 4 GB uploads

WORK = ROOT / "web" / "_work"
WORK.mkdir(parents=True, exist_ok=True)
CACHE = WORK / "_cache"       # analysis cache shared across jobs
DATASET = WORK / "_dataset"   # the creator's verdicts + the taste model
LABELS = DATASET / "labels.jsonl"
TASTE_MODEL = DATASET / "model.json"

# Optional K Library directory (real, free-to-use assets the user dropped in).
LIBRARY_ROOT = os.environ.get("KREATOR_LIBRARY") or None

JOBS: dict[str, dict] = {}
_VLM = None  # the VLM model, loaded once and reused across jobs


def _request_from_form(form) -> JobRequest:
    """The guided form → a JobRequest. A typed instruction is parsed first and
    the explicit controls override it."""
    text = (form.get("instruction") or "").strip()
    req = parse_instruction(text) if text else JobRequest()

    if form.get("outputs") == "long":
        req.long_edit, req.shorts = True, req.shorts if text else 0
    elif form.get("outputs") == "shorts":
        req.long_edit = False
        req.shorts = req.shorts or 3
    elif form.get("outputs") == "both":
        req.long_edit = True
        req.shorts = req.shorts or 3

    n = form.get("shorts_count")
    if n and n.isdigit() and int(n) > 0:
        req.shorts = int(n)
    if form.get("intensity") in ("light", "medium", "heavy"):
        req.intensity = form["intensity"]
    if form.get("captions") in ("auto", "none", "plain", "karaoke"):
        req.captions = form["captions"]
    if form.get("aspect") in ("9:16", "1:1"):
        req.aspect = form["aspect"]
    if form.get("language"):
        req.language = form["language"]
    return req


def _process(job_id: str, video_path: Path, req: JobRequest) -> None:
    job = JOBS[job_id]
    try:
        global _VLM
        if _VLM is None:
            _VLM = LocalVLMBackend()
        out_dir = WORK / job_id

        def progress(stage: str) -> None:
            job["stage"] = stage

        manifest = run_job(str(video_path), str(out_dir), req,
                           library_root=LIBRARY_ROOT, vlm_backend=_VLM,
                           cache_dir=str(CACHE),
                           taste_model_path=str(TASTE_MODEL),
                           progress=progress)
        job["result"] = manifest
        job["dir"] = str(out_dir)
        job["stage"] = "done"
    except Exception as exc:
        job["stage"] = "error"
        job["error"] = str(exc)
    finally:
        video_path.unlink(missing_ok=True)


INDEX_HTML = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kreator — edit your video</title>
<style>
 :root{color-scheme:dark}
 body{font-family:system-ui,sans-serif;background:#0e0f13;color:#e7e9ee;margin:0;
      padding:2.5rem 1rem;display:flex;justify-content:center}
 .card{width:100%;max-width:560px;text-align:center}
 h1{font-size:1.9rem;margin:.2rem 0}
 .tag{color:#8b93a7;margin:.6rem 0 1.6rem;line-height:1.5}
 form{background:#171922;border:1px solid #262a36;border-radius:14px;padding:1.6rem;text-align:left}
 input[type=file]{width:100%;padding:.9rem;background:#0e0f13;color:#e7e9ee;
      border:1px dashed #394054;border-radius:10px;margin-bottom:1rem;box-sizing:border-box}
 textarea{width:100%;min-height:52px;background:#0e0f13;color:#e7e9ee;border:1px solid #394054;
      border-radius:10px;padding:.7rem;box-sizing:border-box;font-family:inherit}
 label{font-size:.82rem;color:#9aa3b2;display:block;margin:.7rem 0 .25rem}
 select,input[type=number]{width:100%;padding:.55rem;background:#0e0f13;color:#e7e9ee;
      border:1px solid #394054;border-radius:8px;box-sizing:border-box}
 .row{display:grid;grid-template-columns:1fr 1fr;gap:.8rem}
 button{width:100%;padding:.95rem;font-size:1.05rem;font-weight:800;background:#3b82f6;
      color:#fff;border:0;border-radius:10px;cursor:pointer;margin-top:1.1rem}
 button:hover{background:#2f6fe0}
 details{margin-top:.9rem;color:#9aa3b2}
 summary{cursor:pointer;font-size:.9rem}
</style></head><body><div class="card">
<h1>🎬 Kreator</h1>
<div class="tag">Upload your video. Kreator understands it and edits it on its
own — or tell it what you want. Local &amp; offline.</div>
<form method="post" action="/upload" enctype="multipart/form-data">
 <input type="file" name="video" accept="video/*" required>
 <label>Tell Kreator what you want (optional — plain language, en/pt)</label>
 <textarea name="instruction" placeholder='e.g. "make 3 shorts of ~30 seconds with animated captions, no music"'></textarea>
 <details><summary>Guided options</summary>
  <div class="row">
   <div><label>Deliverables</label>
    <select name="outputs">
     <option value="">Auto</option>
     <option value="long">Full edit</option>
     <option value="shorts">Shorts only</option>
     <option value="both">Full edit + Shorts</option>
    </select></div>
   <div><label>How many Shorts</label>
    <input type="number" name="shorts_count" min="0" max="10" placeholder="auto"></div>
   <div><label>Cut intensity</label>
    <select name="intensity">
     <option value="">Auto (by content)</option>
     <option value="light">Light — keep more</option>
     <option value="medium">Medium</option>
     <option value="heavy">Heavy — tight cut</option>
    </select></div>
   <div><label>Captions</label>
    <select name="captions">
     <option value="">Auto</option>
     <option value="karaoke">Animated (word-by-word)</option>
     <option value="plain">Plain</option>
     <option value="none">None</option>
    </select></div>
   <div><label>Full-edit aspect</label>
    <select name="aspect">
     <option value="">Keep source</option>
     <option value="9:16">Vertical 9:16</option>
     <option value="1:1">Square 1:1</option>
    </select></div>
   <div><label>Spoken language</label>
    <select name="language">
     <option value="">Auto-detect</option>
     <option value="en">English</option>
     <option value="pt">Português</option>
     <option value="es">Español</option>
     <option value="fr">Français</option>
     <option value="de">Deutsch</option>
     <option value="it">Italiano</option>
     <option value="ja">日本語</option>
     <option value="ko">한국어</option>
    </select></div>
  </div>
 </details>
 <button type="submit">Edit my video →</button>
</form>
<div class="tag" style="margin-top:1.4rem;font-size:.8rem">Kreator never
generates anything: every deliverable is 100% your own footage, plus at most a
free-to-use music bed from your own K Library.</div>
</div></body></html>"""


JOB_HTML = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kreator — working…</title>
<style>
 :root{color-scheme:dark}
 body{font-family:system-ui,sans-serif;background:#0e0f13;color:#e7e9ee;margin:0;
      padding:2.5rem 1rem;display:flex;justify-content:center}
 .card{width:100%;max-width:560px;background:#171922;border:1px solid #262a36;
      border-radius:14px;padding:1.8rem}
 h1{font-size:1.4rem;margin:.2rem 0 1.2rem}
 .stage{font-size:1.08rem;margin:1rem 0}
 .spin{width:34px;height:34px;border:4px solid #2b3040;border-top-color:#3b82f6;
      border-radius:50%;animation:s 1s linear infinite;margin:1rem 0}
 @keyframes s{to{transform:rotate(360deg)}}
 .stat{color:#8b93a7;font-size:.92rem;margin:.3rem 0}
 .note{color:#9aa3b2;font-size:.88rem;margin:.4rem 0 0}
 ul.why{text-align:left;color:#9aa3b2;font-size:.86rem;margin:.6rem 0;padding-left:1.1rem;line-height:1.5}
 .dl{display:block;margin-top:.6rem;padding:.75rem 1rem;background:#22c55e;
      color:#06240f;font-weight:800;border-radius:10px;text-decoration:none}
 .dl.short{background:#3b82f6;color:#fff}
 a.back{display:inline-block;margin-top:1rem;color:#8b93a7}
 .err{color:#f87171}
 .warn{color:#6b7280;font-size:.8rem;margin-top:1rem}
 button.fb{background:#262a36;color:#e7e9ee;border:1px solid #394054;
      border-radius:8px;padding:.35rem .7rem;margin:.2rem .3rem 0 0;cursor:pointer}
 button.fb.on{background:#3b82f6;border-color:#3b82f6}
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
     const m=j.result||{}; const u=m.understanding||{};
     let html=`<div class="stage">✅ Done!</div>
       <div class="note">Kreator saw: <b>${u.label||''}</b> — ${u.preset_note||''}</div>`;
     const reqNotes=(m.request&&m.request.notes)||[];
     if(reqNotes.length) html+=`<ul class="why">${reqNotes.map(n=>`<li>${n}</li>`).join('')}</ul>`;
     const agents=m.agents||[];
     if(agents.length) html+=`<div class="stat" style="margin-top:.6rem"><b>The K Agents' chain:</b></div>
       <ul class="why">${agents.map(a=>`<li><b>${a.agent}</b>: ${a.decision}${a.detail?` — <i>${a.detail}</i>`:''}</li>`).join('')}</ul>`;
     for(const d of (m.deliverables||[])){
       if(d.kind==='long_edit'){
         const why=(d.rationale||[]).map(r=>`<li>${r}</li>`).join('');
         html+=`<div class="stat" style="margin-top:.8rem"><b>Full edit</b> —
           ${Math.round((d.keep_ratio||0)*100)}% kept, ${d.segments} segments`+
           (d.captions?`, ${d.captions} karaoke captions`:'')+
           (d.subtitles?`, ${d.subtitles} subtitles`:'')+`</div>`+
           (why?`<ul class="why">${why}</ul>`:'')+
           `<a class="dl" href="/job/${id}/file/${d.file}">⬇ Download full edit</a>`;
       } else if(d.kind==='thumbnail'){
         html+=`<div class="stat" style="margin-top:.8rem"><b>Thumbnail</b>
           (real frame at ${d.time}s)</div>
           <img src="/job/${id}/file/${d.file}" style="max-width:100%;border-radius:10px;margin-top:.4rem">
           <a class="dl short" href="/job/${id}/file/${d.file}">⬇ ${d.file}</a>`;
       } else {
         html+=`<div class="stat" style="margin-top:.8rem"><b>Short #${d.rank}</b>
           (${d.duration}s${d.aspect?', '+d.aspect:''}) — ${d.rationale||''}</div>
           <a class="dl short" href="/job/${id}/file/${d.file}">⬇ ${d.file}</a>
           <div class="stat">Teach Kreator your taste:
             <button class="fb" onclick="verdict('${d.file}',1,this)">👍 would post</button>
             <button class="fb" onclick="verdict('${d.file}',0,this)">👎 not this</button>
           </div>`;
       }
     }
     b.innerHTML=html; return;
   }
   if(j.stage==='error'){
     b.innerHTML=`<div class="stage err">⚠ Something went wrong</div>
       <div class="stat">${j.error||''}</div>`; return;
   }
   b.innerHTML=`<div class="spin"></div><div class="stage">${j.stage}</div>`;
   setTimeout(poll,1500);
 }
 async function verdict(file,label,btn){
   await fetch(`/job/${id}/feedback`,{method:'POST',
     headers:{'Content-Type':'application/json'},
     body:JSON.stringify({file,label})});
   for(const b of btn.parentElement.querySelectorAll('.fb')) b.classList.remove('on');
   btn.classList.add('on');
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
    req = _request_from_form(request.form)
    job_id = uuid.uuid4().hex[:12]
    src = WORK / f"{job_id}{Path(f.filename).suffix or '.mp4'}"
    f.save(src)
    JOBS[job_id] = {"stage": "queued", "created": time.time()}
    threading.Thread(target=_process, args=(job_id, src, req),
                     daemon=True).start()
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
    return jsonify({k: v for k, v in job.items() if k != "dir"})


@app.route("/job/<job_id>/feedback", methods=["POST"])
def job_feedback(job_id):
    """A 👍/👎 on a Short becomes a labeled example, and the taste model
    retrains right away (sub-second at this scale) so the *next* job already
    ranks with the creator's updated taste."""
    from kreator.learn import (feature_vector, load_dataset, record_verdict,
                               save_model, train)

    job = JOBS.get(job_id)
    body = request.get_json(silent=True) or {}
    name, label = body.get("file"), body.get("label")
    if not job or job.get("stage") != "done" or name is None or label not in (0, 1):
        return jsonify({"error": "bad feedback"}), 400
    short = next((d for d in job["result"].get("deliverables", [])
                  if d.get("kind") == "short" and d.get("file") == name), None)
    if short is None:
        return jsonify({"error": "unknown short"}), 404

    record_verdict(LABELS,
                   feature_vector(short.get("signals", {}),
                                  short.get("game_events", [])),
                   int(label), meta={"job": job_id, "file": name})
    X, y = load_dataset(LABELS)
    model = train(X, y)
    if model:
        save_model(model, TASTE_MODEL)
    return jsonify({"recorded": True, "examples": len(y),
                    "model_trained": bool(model)})


@app.route("/job/<job_id>/file/<name>")
def job_file(job_id, name):
    job = JOBS.get(job_id)
    if not job or job.get("stage") != "done" or not job.get("dir"):
        return redirect(url_for("job_page", job_id=job_id))
    # Only files inside this job's own directory are served.
    path = (Path(job["dir"]) / name).resolve()
    if path.parent != Path(job["dir"]).resolve() or not path.exists():
        return jsonify({"error": "unknown file"}), 404
    return send_file(path, as_attachment=True, download_name=name)


if __name__ == "__main__":
    print("Kreator web UI on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, threaded=True)

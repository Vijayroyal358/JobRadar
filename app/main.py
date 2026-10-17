"""JobRadar local server: API + dashboard."""
import csv
import io
from pathlib import Path
from typing import Optional

from fastapi import Body, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import ai, db, engine, tailor
from .apply import runner as apply_runner
from .resume_parser import parse_resume
from .skills import ALL_SKILLS, ROLE_HINTS, canonicalize, suggest_roles
from .textutil import days_ago, iso, now_utc

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
UPLOADS = db.DATA_DIR / "uploads"
UPLOADS.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="JobRadar", docs_url="/api/docs")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-store"})


# ---------------------------------------------------------------- meta & profile
@app.get("/api/meta")
def meta():
    return {"sources": engine.source_catalog(), "skills": sorted(ALL_SKILLS, key=str.lower), "roles": sorted(ROLE_HINTS)}


def _get_user_id(request: Request) -> str:
    raw = (request.headers.get("x-user-id") or "").strip() if request else ""
    clean = "".join(c for c in raw if c.isalnum() or c in "-_")[:64]
    return clean or "default"


def _public_profile(p):
    out = dict(p)
    out["has_resume"] = bool(out.pop("resume_text", ""))
    out["queries"] = engine.build_queries(p)
    return out


@app.get("/api/profile")
def get_profile(request: Request):
    user_id = _get_user_id(request)
    return _public_profile(db.get_profile(user_id=user_id))


@app.put("/api/profile")
def put_profile(request: Request, data: dict = Body(...)):
    user_id = _get_user_id(request)
    if "skills" in data:
        seen, skills = set(), []
        for s in data["skills"] or []:
            c = canonicalize(str(s))
            if c and c.lower() not in seen:
                seen.add(c.lower())
                skills.append(c)
        data["skills"] = skills
        data["suggested_roles"] = suggest_roles(skills)
    if "years_experience" in data:
        try:
            v = data["years_experience"]
            data["years_experience"] = None if v in (None, "") else max(0.0, min(50.0, float(v)))
        except (TypeError, ValueError):
            raise HTTPException(400, "Years of experience must be a number")
    for k in ("target_roles", "search_locations"):
        if k in data:
            data[k] = [str(x).strip() for x in data[k] or [] if str(x).strip()]
    p = db.save_profile(data, user_id=user_id)
    return _public_profile(p)


@app.post("/api/resume")
async def upload_resume(request: Request, file: UploadFile = File(...)):
    user_id = _get_user_id(request)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "File is larger than 10 MB")
    try:
        parsed = parse_resume(file.filename or "resume", content)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(400, f"Could not read this file: {e}")
    safe = "".join(c for c in (file.filename or "resume") if c.isalnum() or c in "._- ") or "resume"
    user_filename = f"{user_id}_{safe}"
    (UPLOADS / user_filename).write_bytes(content)
    current = db.get_profile(user_id=user_id)
    update = {
        "name": parsed["name"] or current.get("name"),
        "current_title": parsed["current_title"] or current.get("current_title"),
        "years_experience": parsed["years_experience"] if parsed["years_experience"] is not None else current.get("years_experience"),
        "years_method": parsed["years_method"],
        "skills": parsed["skills"],
        "suggested_roles": parsed["suggested_roles"],
        "resume_filename": user_filename,
        "resume_text": parsed["text"],
        "resume_uploaded_at": iso(now_utc()),
    }
    if not current.get("target_roles"):
        roles = ([parsed["current_title"]] if parsed["current_title"] else []) + parsed["suggested_roles"][:3]
        update["target_roles"] = list(dict.fromkeys(roles))
    p = db.save_profile(update, user_id=user_id)
    return {"profile": _public_profile(p), "parsed": {k: v for k, v in parsed.items() if k != "text"}}


# ---------------------------------------------------------------- AI settings and resume tailoring
@app.get("/api/ai/settings")
def ai_settings():
    return ai.public_settings()


@app.put("/api/ai/settings")
def put_ai_settings(data: dict = Body(...)):
    try:
        return ai.save_settings(data)
    except ai.AIError as e:
        raise HTTPException(400, str(e))


@app.post("/api/ai/test")
def ai_test(data: dict = Body(default={})):
    try:
        return ai.test_connection(data.get("provider"), client_ai=data)
    except ai.AIError as e:
        raise HTTPException(400, str(e))


@app.post("/api/ai/models")
def ai_models(data: dict = Body(default={})):
    try:
        return ai.fetch_models(data.get("provider"), client_ai=data)
    except ai.AIError as e:
        raise HTTPException(400, str(e))


@app.post("/api/jobs/{job_id}/tailor")
def tailor_resume(job_id: int, request: Request, data: dict = Body(default={})):
    user_id = _get_user_id(request)
    try:
        return tailor.tailor_job(job_id, data.get("provider"), client_ai=data, user_id=user_id)
    except (tailor.TailorError, ai.AIError) as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Tailoring failed: {e}")


@app.get("/api/jobs/{job_id}/tailored")
def tailored_list(job_id: int, request: Request):
    user_id = _get_user_id(request)
    return {"items": db.tailored_for_job(job_id, user_id=user_id)}


@app.get("/api/tailored/{tid}")
def tailored_detail(tid: int, request: Request):
    user_id = _get_user_id(request)
    rec = db.get_tailored(tid, user_id=user_id)
    if not rec:
        raise HTTPException(404, "Not found")
    rec["note"] = tailor._format_note(rec.get("source_format"))
    return rec


@app.get("/api/tailored/{tid}/download")
def tailored_download(tid: int, variant: str = ""):
    path = tailor.tailored_path(tid, variant)
    if not path:
        raise HTTPException(404, "File not found. It may have been deleted from the data folder.")
    media = ("application/vnd.openxmlformats-officedocument.wordprocessingml.document"
             if path.suffix.lower() == ".docx" else "text/plain")
    return FileResponse(path, media_type=media, filename=path.name)


@app.delete("/api/tailored/{tid}")
def tailored_delete(tid: int, request: Request):
    user_id = _get_user_id(request)
    paths = [tailor.tailored_path(tid), tailor.tailored_path(tid, "ats")]
    db.delete_tailored(tid, user_id=user_id)
    for path in paths:
        if path:
            try:
                path.unlink()
            except OSError:
                pass
    return {"ok": True}


# ---------------------------------------------------------------- apply assistant
@app.get("/api/apply/profile")
def apply_profile(request: Request):
    user_id = _get_user_id(request)
    p = apply_runner.get_apply_profile(user_id=user_id)
    ok, missing = apply_runner.profile_ready(p)
    return {"profile": p, "ready": ok, "missing": missing}


@app.put("/api/apply/profile")
def put_apply_profile(request: Request, data: dict = Body(...)):
    user_id = _get_user_id(request)
    p = apply_runner.save_apply_profile(data, user_id=user_id)
    ok, missing = apply_runner.profile_ready(p)
    return {"profile": p, "ready": ok, "missing": missing}


@app.get("/api/apply/answers")
def apply_answers(request: Request):
    user_id = _get_user_id(request)
    return {"items": db.list_answers(user_id=user_id)}


@app.post("/api/apply/answers")
def add_apply_answer(request: Request, data: dict = Body(...)):
    user_id = _get_user_id(request)
    aid = db.save_answer(str(data.get("question") or ""), str(data.get("answer") or ""), "user", user_id=user_id)
    if not aid:
        raise HTTPException(400, "Question and answer are both required")
    return {"ok": True, "id": aid}


@app.delete("/api/apply/answers/{aid}")
def delete_apply_answer(aid: int, request: Request):
    user_id = _get_user_id(request)
    db.delete_answer(aid, user_id=user_id)
    return {"ok": True}


@app.post("/api/apply/start")
def apply_start(data: dict = Body(...)):
    ids = [int(x) for x in (data.get("job_ids") or []) if str(x).isdigit()]
    if not ids:
        raise HTTPException(400, "Select at least one job")
    try:
        added = apply_runner.start(ids)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "queued": added, **apply_runner.status()}


@app.post("/api/apply/stop")
def apply_stop():
    apply_runner.stop()
    return apply_runner.status()


@app.post("/api/apply/command")
def apply_command(data: dict = Body(...)):
    action = data.get("action")
    if action not in ("submitted", "skip", "continue", "answer", "close_login"):
        raise HTTPException(400, "Unknown action")
    apply_runner.command(action, data)
    return {"ok": True}


@app.post("/api/apply/login")
def apply_login(data: dict = Body(default={})):
    apply_runner.open_login(data.get("site") or "linkedin")
    return apply_runner.status()


@app.get("/api/apply/status")
def apply_status():
    return apply_runner.status()


@app.delete("/api/apply/history")
def apply_clear_history():
    db.clear_finished_applications()
    return {"ok": True}


@app.get("/api/apply/screenshot/{name}")
def apply_screenshot(name: str):
    safe = "".join(c for c in name if c.isalnum() or c in "._-")
    path = apply_runner.SHOTS_DIR / safe
    if not path.exists():
        raise HTTPException(404, "No screenshot")
    return FileResponse(path, media_type="image/png")


# ---------------------------------------------------------------- scraping
@app.post("/api/scrape")
def scrape(request: Request, data: dict = Body(default={})):
    user_id = _get_user_id(request)
    profile = db.get_profile(user_id=user_id)
    if data.get("profile") and isinstance(data["profile"], dict):
        profile.update({k: v for k, v in data["profile"].items() if v is not None})
    try:
        ok = engine.start_scrape(data.get("sources"), user_id=user_id, profile=profile)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not ok:
        raise HTTPException(409, "A search is already running")
    return engine.status()


@app.post("/api/scrape/stop")
def scrape_stop():
    engine.stop_scrape()
    return engine.status()


@app.get("/api/scrape/status")
def scrape_status():
    s = engine.status()
    s["last_run"] = db.last_run()
    return s


@app.post("/api/rescore")
def rescore(request: Request):
    user_id = _get_user_id(request)
    return {"rescored": engine.rescore_all(user_id=user_id)}


# ---------------------------------------------------------------- jobs
LIST_FIELDS = ("id", "source", "title", "company", "company_logo", "location", "remote", "salary", "posted_at", "url",
               "apply_url", "status", "match_score", "chance_score", "chance_label", "matched_skills", "missing_skills",
               "breakdown", "excluded", "exclude_reason", "applicants", "job_type", "first_seen", "run_id", "dedupe_key")


def _filtered(q="", sources="", chance="", min_score=0.0, remote="all", days=0, status="active", sort="chance",
              show_excluded=False, user_id="default"):
    user_id = str(user_id or "default").strip() or "default"
    rows = db.q("SELECT " + ", ".join(LIST_FIELDS) +
                ", (SELECT COUNT(*) FROM tailored t WHERE t.job_id = jobs.id AND (t.user_id = ? OR t.user_id = 'default')) AS tailored_count FROM jobs", (user_id,))
    jobs = [db.row_to_dict(r) for r in rows]
    user_statuses = db.get_user_job_statuses(user_id)
    profile = db.get_profile(user_id)

    # Calculate user-specific match and chance scores dynamically
    if profile.get("skills") or profile.get("target_roles") or profile.get("years_experience") is not None:
        from .matcher import ScoringContext, score_job
        ctx = ScoringContext(profile)
        for j in jobs:
            j.update(score_job(j, ctx))

    for j in jobs:
        if j["id"] in user_statuses:
            j["status"] = user_statuses[j["id"]]
        else:
            j["status"] = "new"

    latest = db.last_run()
    latest_id = (engine.STATE.get("run_id") if engine.STATE.get("running") else None) or (latest or {}).get("id")
    apply_states = {r["job_id"]: r["status"] for r in db.q(
        "SELECT job_id, status FROM applications WHERE status IN ('queued', 'running', 'needs_you') "
        "OR id IN (SELECT MAX(id) FROM applications GROUP BY job_id)")}

    # Merge duplicates posted on several portals; keep the best scored copy.
    groups = {}
    for j in jobs:
        key = j["dedupe_key"] or f"id{j['id']}"
        groups.setdefault(key, []).append(j)
    # Within a company+title group, pair the i-th best posting of each portal together. Two postings from the
    # same portal are always different jobs (e.g. different cities or experience bands) and stay separate.
    clusters = []
    for g in groups.values():
        by_src = {}
        for x in sorted(g, key=lambda x: x["chance_score"], reverse=True):
            by_src.setdefault(x["source"], []).append(x)
        for i in range(max(len(v) for v in by_src.values())):
            clusters.append([v[i] for v in by_src.values() if i < len(v)])
    merged = []
    for g in clusters:
        # The copy carrying a user status (saved/applied/hidden) represents the cluster, so toggles act on it.
        g.sort(key=lambda x: ({"applied": 3, "saved": 2, "hidden": 1}.get(x["status"], 0), x["chance_score"]), reverse=True)
        best = dict(g[0])
        best["also_on"] = [{"source": x["source"], "url": x["apply_url"] or x["url"]} for x in g[1:]
                           if x["source"] != best["source"]]
        best["is_new"] = best["run_id"] == latest_id and best["status"] == "new"
        best["apply_state"] = apply_states.get(best["id"])
        best["days_ago"] = days_ago(best["posted_at"])
        merged.append(best)

    src = set(filter(None, sources.split(","))) if sources else None
    ch = set(filter(None, chance.split(","))) if chance else None
    terms = [t for t in q.lower().split() if t]
    out = []
    for j in merged:
        if src and j["source"] not in src:
            continue
        if ch and j["chance_label"] not in ch:
            continue
        if status == "active" and j["status"] == "hidden":
            continue
        if status not in ("active", "all") and j["status"] != status:
            continue
        if status in ("active", "new") and (j["excluded"] and not show_excluded):
            continue
        if status in ("active", "new") and j["match_score"] < min_score:
            continue
        if remote == "remote" and not j["remote"]:
            continue
        if remote == "onsite" and j["remote"]:
            continue
        if days and (j["days_ago"] is None or j["days_ago"] > days):
            continue
        if terms:
            hay = " ".join([j["title"] or "", j["company"] or "", j["location"] or "", " ".join(j["matched_skills"])]).lower()
            if not all(t in hay for t in terms):
                continue
        out.append(j)

    keyf = {
        "chance": lambda j: (j["chance_score"], j["match_score"]),
        "match": lambda j: (j["match_score"], j["chance_score"]),
        "newest": lambda j: (-(j["days_ago"] if j["days_ago"] is not None else 999), j["chance_score"]),
        "company": lambda j: (j["company"] or "").lower(),
    }.get(sort, lambda j: j["chance_score"])
    out.sort(key=keyf, reverse=sort != "company")
    return out, merged


@app.get("/api/jobs")
def list_jobs(request: Request, q: str = "", sources: str = "", chance: str = "", min_score: float = 0, remote: str = "all",
              days: int = 0, status: str = "active", sort: str = "chance", show_excluded: bool = False,
              page: int = 1, page_size: int = 30):
    user_id = _get_user_id(request)
    items, merged = _filtered(q, sources, chance, min_score, remote, days, status, sort, show_excluded, user_id=user_id)
    visible = [j for j in merged if not j["excluded"] and j["status"] != "hidden" and j["match_score"] >= min_score]
    facets = {"sources": {}, "chance": {"High": 0, "Medium": 0, "Low": 0}}
    for j in visible:
        facets["sources"][j["source"]] = facets["sources"].get(j["source"], 0) + 1
        facets["chance"][j["chance_label"]] = facets["chance"].get(j["chance_label"], 0) + 1
    stats = {
        "matched": len(visible),
        "high": facets["chance"]["High"],
        "new": sum(1 for j in visible if j["is_new"]),
        "saved": sum(1 for j in merged if j["status"] == "saved"),
        "applied": sum(1 for j in merged if j["status"] == "applied"),
        "excluded": sum(1 for j in merged if j["excluded"]),
        "total_stored": len(merged),
    }
    start = max(0, (page - 1) * page_size)
    return {"items": items[start:start + page_size], "total": len(items), "page": page, "page_size": page_size,
            "facets": facets, "stats": stats}


@app.get("/api/jobs/export.csv")
def export_csv(request: Request, q: str = "", sources: str = "", chance: str = "", min_score: float = 0, remote: str = "all",
               days: int = 0, status: str = "active", sort: str = "chance", show_excluded: bool = False):
    user_id = _get_user_id(request)
    items, _ = _filtered(q, sources, chance, min_score, remote, days, status, sort, show_excluded, user_id=user_id)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Chance", "Chance %", "Match %", "Title", "Company", "Location", "Remote", "Source", "Posted (days ago)",
                "Experience", "Matched skills", "Missing skills", "Status", "Apply link"])
    for j in items:
        b = j["breakdown"] or {}
        w.writerow([j["chance_label"], j["chance_score"], j["match_score"], j["title"], j["company"], j["location"],
                    "yes" if j["remote"] else "", j["source"], "" if j["days_ago"] is None else int(j["days_ago"]),
                    b.get("exp_note", ""), ", ".join(j["matched_skills"]), ", ".join(j["missing_skills"]), j["status"],
                    j["apply_url"] or j["url"]])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=matched_jobs.csv"})


@app.get("/api/jobs/{job_id}")
def job_detail(job_id: int, request: Request):
    user_id = _get_user_id(request)
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if not job.get("detail_fetched") or not job.get("description_html"):
        job = engine.refresh_job_detail(job)
    user_statuses = db.get_user_job_statuses(user_id)
    job["status"] = user_statuses.get(job_id, "new")
    profile = db.get_profile(user_id)
    if profile.get("skills") or profile.get("target_roles") or profile.get("years_experience") is not None:
        from .matcher import ScoringContext, score_job
        ctx = ScoringContext(profile)
        job.update(score_job(job, ctx))
    others = db.q("SELECT source, url, apply_url FROM jobs WHERE dedupe_key = ? AND id != ?", (job["dedupe_key"], job_id))
    job["also_on"] = [{"source": r["source"], "url": r["apply_url"] or r["url"]} for r in others if r["source"] != job["source"]]
    job["days_ago"] = days_ago(job["posted_at"])
    job.pop("description_text", None)
    return job


@app.post("/api/jobs/{job_id}/status")
def set_status(job_id: int, request: Request, data: dict = Body(...)):
    user_id = _get_user_id(request)
    st = data.get("status")
    if st not in ("new", "saved", "applied", "hidden"):
        raise HTTPException(400, "Invalid status")
    if not db.q("SELECT id FROM jobs WHERE id = ?", (job_id,), one=True):
        raise HTTPException(404, "Job not found")
    db.set_user_job_status(job_id, st, user_id=user_id)
    return {"ok": True, "status": st}


@app.delete("/api/jobs")
def clear(keep_tracked: bool = True):
    db.clear_jobs(keep_tracked)
    return {"ok": True}

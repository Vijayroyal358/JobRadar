"""Scrape orchestration, relevance filtering and (re)scoring."""
import re
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

from . import db
from .matcher import ScoringContext, analyze_job, role_similarity, score_job
from .scrapers import BY_KEY, SCRAPERS
from .scrapers.base import Blocked, RunContext
from .skills import extract_skills
from .textutil import iso, norm_key, now_utc

_state_lock = threading.Lock()
_stop = threading.Event()
STATE = {"running": False, "run_id": None, "started_at": None, "finished_at": None, "sources": {}, "log": [],
         "queries": []}


def build_queries(profile):
    roles = [r for r in profile.get("target_roles") or [] if r.strip()]
    if not roles:
        roles = ([profile["current_title"]] if profile.get("current_title") else []) + list(profile.get("suggested_roles") or [])
    out, seen = [], set()
    for r in roles:
        r = re.sub(r"\s+", " ", r).strip()
        k = r.lower()
        if r and k not in seen:
            seen.add(k)
            out.append(r)
    return out[: int(profile.get("max_queries") or 6)]


def _log(msg):
    with _state_lock:
        STATE["log"].append({"t": iso(now_utc()), "msg": msg})
        STATE["log"] = STATE["log"][-80:]


def _set_source(key, **kw):
    with _state_lock:
        STATE["sources"].setdefault(key, {}).update(kw)


def status():
    with _state_lock:
        s = {k: (dict(v) if isinstance(v, dict) else list(v) if isinstance(v, list) else v) for k, v in STATE.items()}
        s["sources"] = {k: dict(v) for k, v in STATE["sources"].items()}
    return s


def _prioritizer(sctx):
    def prioritize(title, text=""):
        sim, _ = role_similarity(title, sctx.roles) if sctx.roles else (0.0, "")
        hits = extract_skills(title, strict=False) & sctx.user_skills
        return min(1.0, sim + (0.5 if hits else 0))
    return prioritize


def _prepare(job):
    job.update(analyze_job(job))
    job["dedupe_key"] = norm_key(job.get("company"), job.get("title"))
    return job


def _is_relevant(score, sctx):
    if not sctx.user_skills:
        return True
    b = score["breakdown"]
    if b["location"] == "no":
        return False
    n = len(score["matched_skills"])
    return n >= 2 or (n == 1 and b["role"] >= 45) or (not score["matched_skills"] and b["role"] >= 70)


def start_scrape(sources=None):
    with _state_lock:
        if STATE["running"]:
            return False
    profile = db.get_profile()
    keys = [k for k in (sources or profile.get("sources") or []) if k in BY_KEY]
    queries = build_queries(profile)
    if not queries:
        raise ValueError("Add at least one target role (or upload your resume) before searching.")
    if not keys:
        raise ValueError("Enable at least one job source.")
    _stop.clear()
    run_id = db.start_run()
    with _state_lock:
        STATE.update(running=True, run_id=run_id, started_at=iso(now_utc()), finished_at=None, log=[], queries=queries,
                     sources={k: {"label": BY_KEY[k].label, "state": "queued", "scanned": 0, "relevant": 0, "new": 0,
                                  "progress": 0.0, "message": ""} for k in keys})
    threading.Thread(target=_run_all, args=(profile, keys, queries, run_id), daemon=True).start()
    return True


def stop_scrape():
    _stop.set()
    _log("Stop requested. Finishing current requests...")


def _run_all(profile, keys, queries, run_id):
    _log(f"Searching for: {', '.join(queries)}")
    sctx = ScoringContext(profile)
    prioritize = _prioritizer(sctx)

    def run_one(key):
        scraper = BY_KEY[key]()
        counters = {"scanned": 0, "relevant": 0, "new": 0}
        _set_source(key, state="running", message="")

        def emit(job):
            counters["scanned"] += 1
            try:
                _prepare(job)
                s = score_job(job, sctx)
                if not _is_relevant(s, sctx):
                    if counters["scanned"] % 10 == 0:
                        _set_source(key, **counters)
                    return False
                jid, is_new = db.upsert_job(job, run_id)
                db.save_scores([(jid, s)])
                counters["relevant"] += 1
                counters["new"] += int(is_new)
                _set_source(key, **counters)
                return True
            except Exception as e:  # never kill a run because of one bad posting
                _log(f"{scraper.label}: skipped a posting ({e})")
                return False

        def progress(done, total):
            _set_source(key, progress=round(min(1.0, done / max(total, 1)), 3))

        ctx = RunContext(profile, queries, emit, _log, progress, _stop, prioritize)
        t0 = time.time()
        try:
            scraper.run(ctx)
            _set_source(key, state="stopped" if _stop.is_set() else "done", progress=1.0, **counters,
                        message=f"{counters['relevant']} relevant of {counters['scanned']} scanned in {time.time() - t0:.0f}s")
        except Blocked as e:
            _set_source(key, state="blocked", **counters, message=str(e))
            _log(f"{scraper.label} blocked: {e}")
        except Exception as e:
            _set_source(key, state="error", **counters, message=str(e)[:200])
            _log(f"{scraper.label} failed: {e}")
            traceback.print_exc()

    try:
        with ThreadPoolExecutor(max_workers=len(keys)) as ex:
            list(ex.map(run_one, keys))
        db.purge_old()
        rescore_all()
    finally:
        st = status()
        summary = {k: {kk: v.get(kk) for kk in ("state", "scanned", "relevant", "new", "message")}
                   for k, v in st["sources"].items()}
        db.finish_run(run_id, summary)
        with _state_lock:
            STATE["running"] = False
            STATE["finished_at"] = iso(now_utc())
        _log("Search finished.")


def rescore_all():
    profile = db.get_profile()
    sctx = ScoringContext(profile)
    jobs = db.all_jobs_for_scoring()
    db.save_scores((j["id"], score_job(j, sctx)) for j in jobs)
    return len(jobs)


def refresh_job_detail(job):
    """Load the full description for a LinkedIn job that was not detail-fetched during the run."""
    if job.get("detail_fetched") or job["source"] != "linkedin":
        return job
    from .scrapers.linkedin import LinkedIn
    try:
        d = LinkedIn().fetch_detail(job["source_id"])
    except Exception:
        return job
    job.update(d)
    job.update(analyze_job(job))
    fields = {k: job.get(k) for k in ("description_html", "description_text", "applicants", "seniority", "apply_url",
                                      "job_type", "exp_min", "exp_max", "exp_source", "job_skills") if job.get(k) is not None}
    fields["detail_fetched"] = 1
    db.update_job(job["id"], **fields)
    s = score_job(job, ScoringContext(db.get_profile()))
    db.save_scores([(job["id"], s)])
    return db.get_job(job["id"])


def source_catalog():
    return [{"key": c.key, "label": c.label, "region": c.region, "description": c.description,
             "needs_browser": c.needs_browser} for c in SCRAPERS]

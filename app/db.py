"""SQLite storage for profile, jobs and scrape runs."""
import json
import os
import sqlite3
import threading
from pathlib import Path

from .textutil import iso, now_utc

# JOBRADAR_DATA_DIR lets tests and secondary copies use their own data folder instead of the real one.
DATA_DIR = Path(os.environ.get("JOBRADAR_DATA_DIR") or Path(__file__).resolve().parent.parent / "data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "jobs.db"

_lock = threading.RLock()
_conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
_conn.row_factory = sqlite3.Row
_conn.execute("PRAGMA journal_mode=WAL")

SCHEMA = """
CREATE TABLE IF NOT EXISTS profile (id INTEGER PRIMARY KEY CHECK (id = 1), data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS profiles (
    user_id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS job_user_status (
    user_id TEXT NOT NULL,
    job_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    status_at TEXT,
    PRIMARY KEY (user_id, job_id)
);
CREATE TABLE IF NOT EXISTS apply_profiles (
    user_id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    source_id TEXT NOT NULL,
    url TEXT, apply_url TEXT,
    title TEXT, company TEXT, company_logo TEXT, location TEXT,
    remote INTEGER DEFAULT 0, job_type TEXT, salary TEXT,
    posted_at TEXT,
    description_html TEXT, description_text TEXT,
    tags TEXT DEFAULT '[]', job_skills TEXT DEFAULT '{}',
    exp_min REAL, exp_max REAL, exp_source TEXT,
    applicants TEXT, location_restriction TEXT, seniority TEXT,
    query TEXT,
    dedupe_key TEXT,
    detail_fetched INTEGER DEFAULT 0,
    first_seen TEXT, last_seen TEXT, run_id INTEGER,
    match_score REAL DEFAULT 0, chance_score REAL DEFAULT 0, chance_label TEXT,
    matched_skills TEXT DEFAULT '[]', missing_skills TEXT DEFAULT '[]', breakdown TEXT DEFAULT '{}',
    excluded INTEGER DEFAULT 0, exclude_reason TEXT,
    status TEXT DEFAULT 'new', status_at TEXT,
    UNIQUE (source, source_id)
);
CREATE INDEX IF NOT EXISTS idx_jobs_score ON jobs (chance_score DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_dedupe ON jobs (dedupe_key);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, started_at TEXT, finished_at TEXT, summary TEXT
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tailored (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    provider TEXT, model TEXT,
    source_format TEXT, output_format TEXT,
    filename TEXT, path TEXT,
    summary TEXT, keywords TEXT DEFAULT '[]', changes TEXT DEFAULT '[]',
    created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_tailored_job ON tailored (job_id);
CREATE TABLE IF NOT EXISTS answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL, norm TEXT NOT NULL UNIQUE, answer TEXT NOT NULL,
    source TEXT, created_at TEXT, used INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    status TEXT DEFAULT 'queued', message TEXT, portal TEXT, url TEXT,
    resume_path TEXT, answers TEXT DEFAULT '[]', screenshot TEXT,
    created_at TEXT, started_at TEXT, finished_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_applications_job ON applications (job_id);
"""

with _lock:
    _conn.executescript(SCHEMA)
    _conn.commit()
    # Columns added after the first release; ALTER is a no-op on fresh databases.
    _have = {r["name"] for r in _conn.execute("PRAGMA table_info(tailored)").fetchall()}
    for _col, _ddl in (("ats_filename", "TEXT"), ("ats_path", "TEXT"), ("ats", "TEXT DEFAULT '{}'"), ("user_id", "TEXT DEFAULT 'default'")):
        if _col not in _have:
            _conn.execute(f"ALTER TABLE tailored ADD COLUMN {_col} {_ddl}")
    _have_ans = {r["name"] for r in _conn.execute("PRAGMA table_info(answers)").fetchall()}
    if "user_id" not in _have_ans:
        _conn.execute("ALTER TABLE answers ADD COLUMN user_id TEXT DEFAULT 'default'")
    _conn.commit()
    # Migrate legacy single profile row to profiles table if present
    try:
        old_prof = _conn.execute("SELECT data FROM profile WHERE id = 1").fetchone()
        if old_prof and old_prof[0]:
            _conn.execute("INSERT OR IGNORE INTO profiles (user_id, data, updated_at) VALUES ('default', ?, ?)",
                          (old_prof[0], iso(now_utc())))
            _conn.commit()
    except Exception:
        pass

JOB_FIELDS = ["url", "apply_url", "title", "company", "company_logo", "location", "remote", "job_type", "salary",
              "posted_at", "description_html", "description_text", "tags", "exp_min", "exp_max", "exp_source",
              "applicants", "location_restriction", "seniority", "query", "dedupe_key", "detail_fetched", "job_skills"]
JSON_FIELDS = {"tags", "job_skills", "matched_skills", "missing_skills", "breakdown"}
DICT_FIELDS = {"job_skills", "breakdown"}

DEFAULT_PROFILE = {
    "name": "",
    "current_title": "",
    "years_experience": None,
    "years_method": "",
    "skills": [],
    "target_roles": [],
    "suggested_roles": [],
    "search_locations": ["India"],
    "country": "India",
    "remote_ok": True,
    "posted_within_days": 14,
    "max_queries": 6,
    "linkedin_pages": 3,
    "linkedin_details": 150,
    "naukri_pages": 2,
    "sources": ["linkedin", "naukri", "remotive", "remoteok", "himalayas", "jobicy", "weworkremotely", "arbeitnow", "themuse"],
    "naukri_headless": True,
    "min_match_to_show": 35,
    "resume_filename": "",
    "resume_text": "",
    "resume_uploaded_at": None,
}


def q(sql, params=(), one=False):
    with _lock:
        cur = _conn.execute(sql, params)
        rows = cur.fetchall()
    return (rows[0] if rows else None) if one else rows


def execute(sql, params=()):
    with _lock:
        cur = _conn.execute(sql, params)
        _conn.commit()
        return cur


def row_to_dict(row, include_desc=False):
    d = dict(row)
    for f in JSON_FIELDS:
        if f in d:
            try:
                d[f] = json.loads(d[f] or ("{}" if f in DICT_FIELDS else "[]"))
            except (TypeError, ValueError):
                d[f] = {} if f in DICT_FIELDS else []
    if not include_desc:
        d.pop("description_html", None)
        d.pop("description_text", None)
    return d


# ---------------------------------------------------------------- profile (per user)
def get_profile(user_id="default"):
    user_id = str(user_id or "default").strip() or "default"
    row = q("SELECT data FROM profiles WHERE user_id = ?", (user_id,), one=True)
    if not row and user_id == "default":
        row = q("SELECT data FROM profile WHERE id = 1", one=True)
    data = dict(DEFAULT_PROFILE)
    if row:
        try:
            data.update(json.loads(row["data"]))
        except ValueError:
            pass
    return data


def save_profile(data, user_id="default"):
    user_id = str(user_id or "default").strip() or "default"
    merged = get_profile(user_id)
    merged.update({k: v for k, v in data.items() if k in DEFAULT_PROFILE})
    execute("INSERT INTO profiles (user_id, data, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET data = excluded.data, updated_at = excluded.updated_at",
            (user_id, json.dumps(merged), iso(now_utc())))
    if user_id == "default":
        execute("INSERT INTO profile (id, data) VALUES (1, ?) ON CONFLICT(id) DO UPDATE SET data = excluded.data",
                (json.dumps(merged),))
    return merged


# ---------------------------------------------------------------- user job status (saved / applied / hidden)
def get_user_job_statuses(user_id="default"):
    user_id = str(user_id or "default").strip() or "default"
    rows = q("SELECT job_id, status FROM job_user_status WHERE user_id = ?", (user_id,))
    return {r["job_id"]: r["status"] for r in rows}


def set_user_job_status(job_id, status, user_id="default"):
    user_id = str(user_id or "default").strip() or "default"
    execute("INSERT INTO job_user_status (user_id, job_id, status, status_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(user_id, job_id) DO UPDATE SET status = excluded.status, status_at = excluded.status_at",
            (user_id, job_id, status, iso(now_utc())))



# ---------------------------------------------------------------- jobs
def upsert_job(job: dict, run_id=None):
    """Insert or refresh a job. Returns (job_id, is_new)."""
    now = iso(now_utc())
    vals = {f: job.get(f) for f in JOB_FIELDS}
    vals["tags"] = json.dumps(job.get("tags") or [])
    vals["job_skills"] = json.dumps(job.get("job_skills") or {})
    vals["remote"] = 1 if job.get("remote") else 0
    with _lock:
        existing = _conn.execute("SELECT id, description_html, detail_fetched FROM jobs WHERE source = ? AND source_id = ?",
                                 (job["source"], str(job["source_id"]))).fetchone()
        if existing:
            # Never replace a full description with an empty/short one.
            if existing["detail_fetched"] and not vals.get("detail_fetched"):
                for f in ("description_html", "description_text", "applicants", "seniority", "apply_url",
                          "exp_min", "exp_max", "exp_source", "detail_fetched", "job_skills"):
                    vals.pop(f, None)
            sets = ", ".join(f"{k} = ?" for k in vals if vals[k] is not None)
            params = [v for v in vals.values() if v is not None]
            _conn.execute(f"UPDATE jobs SET {sets}, last_seen = ? WHERE id = ?", params + [now, existing["id"]])
            _conn.commit()
            return existing["id"], False
        cols = ["source", "source_id"] + list(vals) + ["first_seen", "last_seen", "run_id"]
        params = [job["source"], str(job["source_id"])] + list(vals.values()) + [now, now, run_id]
        cur = _conn.execute(f"INSERT INTO jobs ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})", params)
        _conn.commit()
        return cur.lastrowid, True


def update_job(job_id, **fields):
    if not fields:
        return
    for f in JSON_FIELDS & set(fields):
        fields[f] = json.dumps(fields[f])
    sets = ", ".join(f"{k} = ?" for k in fields)
    execute(f"UPDATE jobs SET {sets} WHERE id = ?", list(fields.values()) + [job_id])


def save_scores(rows):
    """rows: iterable of (job_id, score dict)."""
    with _lock:
        for job_id, s in rows:
            _conn.execute(
                "UPDATE jobs SET match_score=?, chance_score=?, chance_label=?, matched_skills=?, missing_skills=?, "
                "breakdown=?, excluded=?, exclude_reason=? WHERE id=?",
                (s["match_score"], s["chance_score"], s["chance_label"], json.dumps(s["matched_skills"]),
                 json.dumps(s["missing_skills"]), json.dumps(s["breakdown"]), 1 if s["excluded"] else 0,
                 s["exclude_reason"], job_id))
        _conn.commit()


def get_job(job_id):
    row = q("SELECT * FROM jobs WHERE id = ?", (job_id,), one=True)
    return row_to_dict(row, include_desc=True) if row else None


def all_jobs_for_scoring():
    return [row_to_dict(r, include_desc=True) for r in q("SELECT * FROM jobs")]


def purge_old(days=45):
    execute("DELETE FROM jobs WHERE status IN ('new', 'hidden') AND last_seen < datetime('now', ?)", (f"-{days} days",))


def clear_jobs(keep_tracked=True):
    if keep_tracked:
        execute("DELETE FROM jobs WHERE status NOT IN ('saved', 'applied')")
    else:
        execute("DELETE FROM jobs")


# ---------------------------------------------------------------- runs
def start_run():
    return execute("INSERT INTO runs (started_at) VALUES (?)", (iso(now_utc()),)).lastrowid


def finish_run(run_id, summary):
    execute("UPDATE runs SET finished_at = ?, summary = ? WHERE id = ?", (iso(now_utc()), json.dumps(summary), run_id))


def last_run():
    row = q("SELECT * FROM runs WHERE finished_at IS NOT NULL ORDER BY id DESC LIMIT 1", one=True)
    if not row:
        return None
    d = dict(row)
    d["summary"] = json.loads(d["summary"] or "{}")
    return d


# ---------------------------------------------------------------- settings (API keys and AI options)
def get_setting(key, default=None):
    row = q("SELECT value FROM settings WHERE key = ?", (key,), one=True)
    if not row:
        return default
    try:
        return json.loads(row["value"])
    except ValueError:
        return default


def set_setting(key, value):
    execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, json.dumps(value)))


def all_settings(prefix=""):
    rows = q("SELECT key, value FROM settings WHERE key LIKE ?", (prefix + "%",))
    out = {}
    for r in rows:
        try:
            out[r["key"]] = json.loads(r["value"])
        except ValueError:
            pass
    return out


# ---------------------------------------------------------------- tailored resumes
def add_tailored(rec, user_id="default"):
    user_id = str(rec.get("user_id") or user_id or "default").strip() or "default"
    cur = execute(
        "INSERT INTO tailored (job_id, provider, model, source_format, output_format, filename, path, summary, "
        "keywords, changes, created_at, ats_filename, ats_path, ats, user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (rec["job_id"], rec.get("provider"), rec.get("model"), rec.get("source_format"), rec.get("output_format"),
         rec.get("filename"), rec.get("path"), rec.get("summary"), json.dumps(rec.get("keywords") or []),
         json.dumps(rec.get("changes") or []), iso(now_utc()), rec.get("ats_filename"), rec.get("ats_path"),
         json.dumps(rec.get("ats") or {}), user_id))
    return cur.lastrowid


def _tailored_row(r, with_changes=True):
    d = dict(r)
    d["keywords"] = json.loads(d.get("keywords") or "[]")
    try:
        d["ats"] = json.loads(d.get("ats") or "{}")
    except ValueError:
        d["ats"] = {}
    if with_changes:
        d["changes"] = json.loads(d.get("changes") or "[]")
    else:
        d.pop("changes", None)
        best = d["ats"].get("ats_copy") or d["ats"].get("formatted") or {}
        d["ats"] = {"score": best.get("score")} if best else {}
    d.pop("path", None)
    d.pop("ats_path", None)
    return d


def get_tailored(tid, user_id="default"):
    user_id = str(user_id or "default").strip() or "default"
    row = q("SELECT * FROM tailored WHERE id = ? AND (user_id = ? OR user_id = 'default')", (tid, user_id), one=True)
    return _tailored_row(row) if row else None


def tailored_path(tid, variant=""):
    row = q("SELECT path, ats_path FROM tailored WHERE id = ?", (tid,), one=True)
    if not row:
        return None
    return row["ats_path"] if variant == "ats" else row["path"]


def tailored_for_job(job_id, user_id="default"):
    user_id = str(user_id or "default").strip() or "default"
    return [_tailored_row(r, with_changes=False)
            for r in q("SELECT * FROM tailored WHERE job_id = ? AND (user_id = ? OR user_id = 'default') ORDER BY id DESC", (job_id, user_id))]


def delete_tailored(tid, user_id="default"):
    user_id = str(user_id or "default").strip() or "default"
    execute("DELETE FROM tailored WHERE id = ? AND (user_id = ? OR user_id = 'default')", (tid, user_id))


# ---------------------------------------------------------------- answer bank (auto-apply)
def norm_question(q):
    import re as _re
    q = _re.sub(r"[^a-z0-9 ]+", " ", (q or "").lower())
    q = _re.sub(r"\b(please|kindly|the|a|an|your|you|are|do|is|of|to|in|for|this|that|optional|required)\b", " ", q)
    return _re.sub(r"\s+", " ", q).strip()


def list_answers(user_id="default"):
    user_id = str(user_id or "default").strip() or "default"
    return [dict(r) for r in q("SELECT * FROM answers WHERE user_id = ? OR user_id = 'default' ORDER BY used DESC, id DESC", (user_id,))]


def save_answer(question, answer, source="user", user_id="default"):
    user_id = str(user_id or "default").strip() or "default"
    n = norm_question(question)
    if not n or not str(answer).strip():
        return None
    existing = q("SELECT id FROM answers WHERE norm = ? AND user_id = ?", (n, user_id), one=True)
    if existing:
        execute("UPDATE answers SET answer = ?, source = ? WHERE id = ?", (str(answer).strip(), source, existing["id"]))
        return existing["id"]
    cur = execute("INSERT INTO answers (question, norm, answer, source, created_at, user_id) VALUES (?, ?, ?, ?, ?, ?)",
                  (question.strip(), n, str(answer).strip(), source, iso(now_utc()), user_id))
    return cur.lastrowid


def delete_answer(aid, user_id="default"):
    user_id = str(user_id or "default").strip() or "default"
    execute("DELETE FROM answers WHERE id = ? AND (user_id = ? OR user_id = 'default')", (aid, user_id))


def bump_answer(aid):
    execute("UPDATE answers SET used = used + 1 WHERE id = ?", (aid,))


# ---------------------------------------------------------------- applications (auto-apply queue)
def add_application(job_id):
    return execute("INSERT INTO applications (job_id, status, created_at) VALUES (?, 'queued', ?)",
                   (job_id, iso(now_utc()))).lastrowid


def update_application(aid, **fields):
    if "answers" in fields:
        fields["answers"] = json.dumps(fields["answers"])
    sets = ", ".join(f"{k} = ?" for k in fields)
    execute(f"UPDATE applications SET {sets} WHERE id = ?", list(fields.values()) + [aid])


def _app_row(r):
    d = dict(r)
    try:
        d["answers"] = json.loads(d.get("answers") or "[]")
    except ValueError:
        d["answers"] = []
    return d


def next_queued_application():
    row = q("SELECT * FROM applications WHERE status = 'queued' ORDER BY id LIMIT 1", one=True)
    return _app_row(row) if row else None


def get_application(aid):
    row = q("SELECT * FROM applications WHERE id = ?", (aid,), one=True)
    return _app_row(row) if row else None


def applications(limit=60):
    rows = q("SELECT a.*, j.title, j.company, j.source FROM applications a LEFT JOIN jobs j ON j.id = a.job_id "
             "ORDER BY CASE a.status WHEN 'running' THEN 0 WHEN 'needs_you' THEN 0 WHEN 'queued' THEN 1 ELSE 2 END, "
             "a.id DESC LIMIT ?", (limit,))
    return [_app_row(r) for r in rows]


def queued_job_ids():
    return {r["job_id"] for r in q("SELECT job_id FROM applications WHERE status IN ('queued', 'running', 'needs_you')")}


def cancel_queued():
    execute("UPDATE applications SET status = 'skipped', message = 'Cancelled', finished_at = ? WHERE status = 'queued'",
            (iso(now_utc()),))


def clear_finished_applications():
    execute("DELETE FROM applications WHERE status NOT IN ('queued', 'running', 'needs_you')")

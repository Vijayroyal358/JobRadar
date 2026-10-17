"""Tailor the uploaded resume to one job with an AI provider while keeping the original layout.

DOCX resumes are edited in place: each paragraph keeps its style, font and bullets and only its
text changes. PDF and TXT resumes cannot be edited in place, so the result is rebuilt as a
DOCX (or TXT) that follows the original line structure.
"""
import re
import threading
from pathlib import Path

from . import ai, ats, db, engine
from .resume_parser import EDU_LINE, OTHER_HEAD, RANGE
from .textutil import now_utc

TAILORED_DIR = db.DATA_DIR / "tailored"
TAILORED_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS = db.DATA_DIR / "uploads"

MAX_JD_CHARS = 14000
MAX_SEGMENTS = 400

# Segments that must never change: contact details, date ranges, education lines, section headings.
PROTECTED = re.compile(r"@|https?://|www\.|linkedin\.com|github\.com|\+?\d[\d\s\-()]{8,}\d", re.I)
BULLET = re.compile(r"^\s*([•▪◦●‣■⁃\-\*·–])\s+")

SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "description": "One or two sentences on what was changed and why."},
        "keywords_added": {"type": "array", "items": {"type": "string"},
                           "description": "Job keywords that now appear in the resume."},
        "jd_keywords": {"type": "array", "items": {"type": "string"},
                        "description": "The 10 to 25 most important hard skills, tools, certifications and qualifications an ATS would be configured to search for in this job description, exactly as the job writes them."},
        "changes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "i": {"type": "integer", "description": "Segment number being replaced."},
                    "text": {"type": "string", "description": "Full replacement text for that segment."},
                    "reason": {"type": "string", "description": "Short reason for the change."},
                },
                "required": ["i", "text", "reason"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["summary", "keywords_added", "jd_keywords", "changes"],
    "additionalProperties": False,
}

SYSTEM = """You are an expert resume writer and applicant-tracking-system (ATS) specialist.
You rewrite parts of a candidate's existing resume so it matches one specific job description better.

Hard rules:
1. Never invent anything. Do not add employers, job titles, dates, degrees, certifications, projects, tools or
   achievements that are not already supported by the resume. You may rephrase, reorder and emphasise what is there.
2. The resume is given as numbered segments. Return only the segments you change. Each replacement text replaces
   that segment completely. Never merge or split segments, never add new ones, never use line breaks inside a segment.
3. Keep each replacement close to the original length (within about 25 percent) so the page layout still fits.
4. Do not change the candidate's name, contact details, section headings, company names, job titles held, dates,
   education or certifications. Those segments are listed as protected and will be ignored if changed.
5. Focus on: the professional summary or objective, the skills list (reorder so the job's key skills come first,
   add a skill from the job only when the resume shows evidence of it elsewhere), and experience bullets
   (mirror the job's terminology, lead with strong verbs, keep numbers and results).
6. Write in the same person, tense and tone as the original. Keep spelling conventions (US or UK) as in the resume.
7. Be selective. Typically 5 to 20 segments change. Unchanged segments must not be returned.

ATS rules (applicant tracking systems rank resumes by exact keyword matches, so follow these strictly):
8. Use the job's exact wording for skills, tools and qualifications, including its casing and spelling
   (for example "PostgreSQL" not "Postgres" if the job says PostgreSQL). Where the job uses an acronym, write the
   long form and the acronym together the first time it appears, such as "Amazon Web Services (AWS)".
9. Put the job's most important skills first in the skills list and in the first bullet of the most recent role.
   Each hard skill the candidate genuinely has should appear at least once in the skills list and once in context.
10. Start experience bullets with a strong past-tense (or present-tense for the current role) action verb, keep
    them to one or two lines, and keep numbers and measurable results. No first-person pronouns.
11. Plain text only: no emoji, icons, symbols, tables, columns or decorative characters. Standard bullets are fine.
12. Never stuff keywords: every term you add must read naturally inside a sentence or a skills list.
13. In jd_keywords, list the terms an ATS would be configured to search for in this job (hard skills, tools,
    platforms, certifications, methodologies, degree requirements), exactly as the job description writes them."""


class TailorError(Exception):
    pass


_inflight = set()
_inflight_lock = threading.Lock()


# ---------------------------------------------------------------- resume segments
def _docx_paragraphs(doc):
    """All paragraphs in body order, including table cells and text boxes."""
    from docx.oxml.ns import qn
    from docx.text.paragraph import Paragraph
    return [Paragraph(p, doc) for p in doc.element.body.iter(qn("w:p"))]


def _para_text(p):
    return "".join(r.text for r in p.runs)


def _set_para_text(p, text):
    """Replace the paragraph text while keeping the first run's formatting (font, size, bold, colour)."""
    runs = p.runs
    if not runs:
        return False
    runs[0].text = text
    for r in runs[1:]:
        r.text = ""
    return True


def _is_protected(text, is_heading=False):
    t = text.strip()
    if not t or len(t) < 3:
        return True
    if PROTECTED.search(t):
        return True
    if OTHER_HEAD.match(t) or is_heading:
        return True
    if RANGE.search(t) and len(t) < 140:
        return True
    if EDU_LINE.search(t) and len(t) < 140:
        return True
    return False


def load_segments(profile):
    """Return (kind, segments, handle). kind is docx, pdf or txt. segments: [{i, text, protected}]."""
    fname = profile.get("resume_filename") or ""
    path = UPLOADS / fname if fname else None
    if path and path.exists() and fname.lower().endswith(".docx"):
        import docx
        doc = docx.Document(str(path))
        paras = _docx_paragraphs(doc)
        segs, handle = [], {"doc": doc, "paras": {}}
        for p in paras:
            text = _para_text(p)
            if not text.strip():
                continue
            if len(segs) >= MAX_SEGMENTS:
                break
            style = (p.style.name if p.style is not None else "") or ""
            heading = style.lower().startswith(("heading", "title"))
            i = len(segs)
            segs.append({"i": i, "text": text, "protected": _is_protected(text, heading)})
            handle["paras"][i] = p
        if not segs:
            raise TailorError("The DOCX resume has no readable text paragraphs.")
        return "docx", segs, handle
    text = profile.get("resume_text") or ""
    if not text.strip():
        raise TailorError("Upload your resume first, then tailor it to a job.")
    kind = "txt" if fname.lower().endswith((".txt", ".md")) else "pdf"
    segs = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if len(segs) >= MAX_SEGMENTS:
            break
        segs.append({"i": len(segs), "text": s, "protected": _is_protected(s)})
    return kind, segs, {"lines": text.splitlines()}


# ---------------------------------------------------------------- prompt
def _job_text(job):
    text = (job.get("description_text") or "").strip()
    if not text and job.get("description_html"):
        from .textutil import html_to_text
        text = html_to_text(job["description_html"])
    if len(text) > MAX_JD_CHARS:
        text = text[:MAX_JD_CHARS] + "\n[description truncated]"
    return text


def build_prompt(job, segs, profile):
    jd = _job_text(job)
    if len(jd) < 80:
        raise TailorError("This job has no usable description. Open it on the portal and tailor from a job with a full JD.")
    lines = [f"[{s['i']}]{' (protected)' if s['protected'] else ''} {s['text']}" for s in segs]
    matched = ", ".join(job.get("matched_skills") or []) or "none detected"
    missing = ", ".join(job.get("missing_skills") or []) or "none"
    user = f"""JOB
Title: {job.get('title') or ''}
Company: {job.get('company') or ''}
Location: {job.get('location') or ''}

JOB DESCRIPTION
{jd}

MATCHING NOTES
Skills from the job already in the candidate's profile: {matched}
Skills the job mentions that the profile does not list (add only if the resume shows real evidence): {missing}
Candidate's current title: {profile.get('current_title') or ''}
Candidate's total experience: {profile.get('years_experience') or 'unknown'} years

RESUME SEGMENTS (number, then text; protected segments must not be changed)
{chr(10).join(lines)}

Return the JSON object with summary, keywords_added and changes."""
    return SYSTEM, user


# ---------------------------------------------------------------- apply
def _clean_text(t):
    t = re.sub(r"\s*\n\s*", " ", str(t or "")).strip()
    return re.sub(r"[ \t]{2,}", " ", t)


def _filter_changes(raw, segs):
    by_i = {s["i"]: s for s in segs}
    out, seen = [], set()
    for c in raw.get("changes") or []:
        try:
            i = int(c.get("i"))
        except (TypeError, ValueError, AttributeError):
            continue
        s = by_i.get(i)
        if not s or s["protected"] or i in seen:
            continue
        new = _clean_text(c.get("text"))
        if not new or new == s["text"].strip():
            continue
        # Keep bullets if the original had one and the model dropped it.
        m = BULLET.match(s["text"])
        if m and not BULLET.match(new):
            new = f"{m.group(1)} {new}"
        if len(new) > max(220, len(s["text"]) * 1.8):
            continue
        seen.add(i)
        out.append({"i": i, "before": s["text"], "after": new, "reason": _clean_text(c.get("reason"))[:200]})
    out.sort(key=lambda c: c["i"])
    return out


def _safe_name(s, n=40):
    s = re.sub(r"[^A-Za-z0-9 _\-]+", "", s or "").strip()
    return re.sub(r"\s+", " ", s)[:n].strip() or "job"


# ---------------------------------------------------------------- entry point
def tailor_job(job_id, provider=None, client_ai=None, user_id="default"):
    """Tailor the saved resume to job `job_id`. Returns the stored tailored record (with changes)."""
    with _inflight_lock:
        if job_id in _inflight:
            raise TailorError("This job is already being tailored. Give it a moment.")
        _inflight.add(job_id)
    try:
        return _tailor(job_id, provider, client_ai=client_ai, user_id=user_id)
    finally:
        with _inflight_lock:
            _inflight.discard(job_id)


def _tailor(job_id, provider, client_ai=None, user_id="default"):
    job = db.get_job(job_id)
    if not job:
        raise TailorError("Job not found")
    if not job.get("detail_fetched") or not job.get("description_text"):
        job = engine.refresh_job_detail(job)
    profile = db.get_profile(user_id=user_id)
    kind, segs, handle = load_segments(profile)
    system, user = build_prompt(job, segs, profile)
    raw, used_provider, model = ai.complete_json(system, user, SCHEMA, provider, client_ai=client_ai)
    if not isinstance(raw, dict):
        raise TailorError("The AI returned an unexpected response.")
    changes = _filter_changes(raw, segs)
    if not changes:
        raise TailorError("The AI did not suggest any usable changes for this job. Try again or try another model.")

    stamp = now_utc().strftime("%Y%m%d-%H%M%S")
    base = f"Resume - {_safe_name(job.get('company'))} - {_safe_name(job.get('title'))} - {stamp}"
    changes_by_i = {c["i"]: c["after"] for c in changes}
    if kind == "docx":
        out_path = TAILORED_DIR / f"{base}.docx"
        applied = []
        for c in changes:
            if _set_para_text(handle["paras"][c["i"]], c["after"]):
                applied.append(c)
        changes = applied
        handle["doc"].save(str(out_path))
        out_fmt = "docx"
    elif kind == "txt":
        out_path = TAILORED_DIR / f"{base}.txt"
        seg_i, out_lines = 0, []
        for raw_line in handle["lines"]:
            if raw_line.strip():
                if seg_i < len(segs) and seg_i in changes_by_i:
                    indent = raw_line[: len(raw_line) - len(raw_line.lstrip())]
                    out_lines.append(indent + changes_by_i[seg_i])
                else:
                    out_lines.append(raw_line)
                seg_i += 1
            else:
                out_lines.append(raw_line)
        out_path.write_text("\n".join(out_lines), encoding="utf-8")
        out_fmt = "txt"
    else:
        out_path = TAILORED_DIR / f"{base}.docx"
        final_lines = []
        seg_i = 0
        for raw_line in handle["lines"]:
            if not raw_line.strip():
                continue
            final_lines.append(changes_by_i.get(seg_i, raw_line.strip()) if seg_i < len(segs) else raw_line.strip())
            seg_i += 1
        info = ats.inspect_text("\n".join(final_lines))
        ats.build_ats_docx(ats.classify_lines(info["lines"]), out_path)
        out_fmt = "docx"

    jd_keywords = _jd_keywords(raw, job)
    ats_path = None
    if kind == "docx":
        info = ats.inspect_docx(out_path)
        ats_path = TAILORED_DIR / f"{base} (ATS).docx"
        ats.build_ats_docx(ats.classify_lines(info["lines"], info["header_footer_text"]), ats_path)
    elif kind == "txt":
        info = ats.inspect_text(out_path.read_text(encoding="utf-8"))
        ats_path = TAILORED_DIR / f"{base} (ATS).docx"
        ats.build_ats_docx(ats.classify_lines(info["lines"]), ats_path)
    report = {
        "keywords": jd_keywords,
        "formatted": ats.analyze(out_path if out_fmt == "docx" else out_path.read_text(encoding="utf-8"), jd_keywords, out_fmt),
        "ats_copy": ats.analyze(ats_path, jd_keywords, "docx") if ats_path else None,
    }
    best = report["ats_copy"] or report["formatted"]
    tid = db.add_tailored({
        "job_id": job_id, "provider": used_provider, "model": model, "source_format": kind, "output_format": out_fmt,
        "filename": out_path.name, "path": str(out_path), "summary": _clean_text(raw.get("summary"))[:1000],
        "keywords": best["covered"], "changes": changes,
        "ats_filename": ats_path.name if ats_path else None, "ats_path": str(ats_path) if ats_path else None,
        "ats": report,
        "user_id": user_id,
    }, user_id=user_id)
    rec = db.get_tailored(tid, user_id=user_id)
    rec["note"] = _format_note(kind)
    return rec


def _jd_keywords(raw, job):
    """Keywords an ATS would search for: the model's list first, then skills the matcher found in the job title or tags."""
    out, seen = [], set()
    for k in list(raw.get("jd_keywords") or []) + list(raw.get("keywords_added") or []):
        k = _clean_text(k)
        if k and k.lower() not in seen and len(k) <= 60:
            seen.add(k.lower())
            out.append(k)
    for sk, w in sorted((job.get("job_skills") or {}).items(), key=lambda kv: -kv[1]):
        if w >= 2 and sk.lower() not in seen and len(out) < 30:
            seen.add(sk.lower())
            out.append(sk)
    return out[:30]


def _format_note(kind):
    if kind == "docx":
        return "Edited inside your original DOCX. Styles, fonts, bullets and tables are unchanged."
    if kind == "txt":
        return "Edited your original text file line by line."
    return ("Your resume was uploaded as a PDF, which cannot be edited in place. The tailored version is an ATS-safe "
            "single-column DOCX that follows the same line order. Upload a DOCX resume to keep your exact formatting.")


def tailored_path(tid, variant=""):
    p = db.tailored_path(tid, variant)
    if not p or not Path(p).exists():
        return None
    return Path(p)

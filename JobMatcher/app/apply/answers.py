"""Answers for application questions: the saved answer bank first, then an AI draft from the resume."""
import difflib
import json

from .. import ai, db

SYSTEM = """You help a job candidate fill application forms. You are given the candidate's profile and resume text,
the job, and a list of form questions. Write the answer the candidate would give.

Rules:
- Use only facts from the profile and resume. Never invent experience, qualifications, authorizations or numbers.
- For questions with options, answer with exactly one of the given options, copied verbatim.
- Yes/no questions: answer "Yes" or "No" based on the profile. If the profile does not say, choose the answer that
  keeps the application honest and mark uncertain=true.
- Salary, notice period, work authorization, relocation: take them from the profile. If missing, mark uncertain=true
  and give a sensible placeholder the candidate can edit.
- Free-text questions ("why do you want this role", "describe a project"): 2 to 5 sentences, first person, specific
  to this job, drawn from the resume. No fluff, no exclamation marks.
- Numeric questions: digits only, no units unless the question asks for them.
- Keep every answer concise and in the same language as the question."""

SCHEMA = {
    "type": "object",
    "properties": {
        "answers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "answer": {"type": "string"},
                    "uncertain": {"type": "boolean"},
                },
                "required": ["id", "answer", "uncertain"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["answers"],
    "additionalProperties": False,
}


def lookup(question):
    """Return (answer_row or None) from the bank using exact-normalised then fuzzy matching."""
    n = db.norm_question(question)
    if not n:
        return None
    rows = db.list_answers()
    for r in rows:
        if r["norm"] == n:
            return r
    best, score = None, 0.0
    for r in rows:
        s = difflib.SequenceMatcher(None, n, r["norm"]).ratio()
        if s > score:
            best, score = r, s
    return best if score >= 0.86 else None


def _profile_text(prof, user_profile):
    keep = ["first_name", "last_name", "email", "phone", "city", "state", "country", "linkedin_url", "github_url",
            "portfolio_url", "current_company", "current_title", "years_experience", "notice_period", "current_salary",
            "expected_salary", "salary_currency", "work_authorized", "needs_sponsorship", "willing_to_relocate",
            "remote_ok", "cover_letter"]
    lines = [f"{k}: {prof.get(k)}" for k in keep if prof.get(k) not in (None, "")]
    lines.append(f"skills: {', '.join(user_profile.get('skills') or [])}")
    if user_profile.get("years_experience") is not None and not prof.get("years_experience"):
        lines.append(f"years_experience: {user_profile['years_experience']}")
    return "\n".join(lines)


def draft(questions, prof, user_profile, job, provider=None):
    """Ask the AI for answers to `questions` (list of forms.describe dicts). Returns {id: {answer, uncertain}}."""
    if not questions:
        return {}
    resume = (user_profile.get("resume_text") or "")[:9000]
    jd = (job.get("description_text") or "")[:5000]
    qtext = []
    for q in questions:
        line = f"- id={q['id']} | {q['label']}"
        if q.get("options"):
            line += " | options: " + " / ".join(q["options"][:40])
        if q.get("required"):
            line += " | required"
        qtext.append(line)
    user = f"""CANDIDATE PROFILE
{_profile_text(prof, user_profile)}

RESUME
{resume}

JOB
{job.get('title') or ''} at {job.get('company') or ''}
{jd}

QUESTIONS
{chr(10).join(qtext)}

Return answers for every question id."""
    data, _, _ = ai.complete_json(SYSTEM, user, SCHEMA, provider, max_tokens=4000)
    out = {}
    for a in (data or {}).get("answers") or []:
        if isinstance(a, dict) and a.get("id"):
            out[str(a["id"])] = {"answer": str(a.get("answer") or "").strip(), "uncertain": bool(a.get("uncertain"))}
    return out


def resolve(questions, prof, user_profile, job, use_ai=True, log=None):
    """For each question pick a bank answer, else an AI draft. Returns list of dicts for the UI and the filler."""
    out, need_ai = [], []
    for q in questions:
        row = lookup(q["label"])
        if row:
            db.bump_answer(row["id"])
            out.append({**q, "answer": row["answer"], "source": "bank", "uncertain": False})
        else:
            need_ai.append(q)
    if need_ai and use_ai:
        try:
            drafted = draft(need_ai, prof, user_profile, job)
        except ai.AIError as e:
            if log:
                log(f"AI could not draft answers: {e}")
            drafted = {}
        for q in need_ai:
            d = drafted.get(q["id"])
            if d and d["answer"]:
                out.append({**q, "answer": d["answer"], "source": "ai", "uncertain": d["uncertain"]})
            else:
                out.append({**q, "answer": "", "source": "none", "uncertain": True})
    else:
        out.extend({**q, "answer": "", "source": "none", "uncertain": True} for q in need_ai)
    return out

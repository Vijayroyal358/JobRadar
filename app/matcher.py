"""Job analysis and scoring against the user's profile.

Match score (0-100)   = 55% skill fit + 30% experience fit + 15% role similarity
Interview chance      = 75% match score + 13% freshness + 12% low competition, minus location uncertainty

Hard exclusions: clearly outside your experience range, no overlapping skills, or a location you cannot work from.
"""
import re

from .skills import SKILL_CATEGORY, canonicalize, extract_skills, skills_from_tags, _custom_regex
from .textutil import days_ago, parse_experience_range, seniority_from_title

W_SKILL, W_EXP, W_ROLE = 0.55, 0.30, 0.15

# ---------------------------------------------------------------- job analysis (cached per job)


def analyze_job(job: dict) -> dict:
    """Skills with weights (title 3, tags 2, description 1) and parsed experience."""
    title = job.get("title") or ""
    desc = job.get("description_text") or ""
    weights = {}
    for s in extract_skills(desc):
        weights[s] = 1
    for s in skills_from_tags(job.get("tags") or []):
        weights[s] = max(weights.get(s, 0), 2)
    for s in extract_skills(title, strict=False) if title else ():
        weights[s] = 3
    out = {"job_skills": weights}
    if job.get("exp_min") is None and job.get("exp_max") is None:
        lo, hi = parse_experience_range(desc)
        if lo is not None:
            out.update(exp_min=lo, exp_max=hi, exp_source="description")
    return out


# ---------------------------------------------------------------- role similarity
_STOP = {"senior", "sr", "junior", "jr", "lead", "principal", "staff", "associate", "ii", "iii", "iv", "i", "and", "of",
         "the", "for", "in", "with", "a", "an", "to", "at", "remote", "hybrid", "contract", "full", "time", "fulltime",
         "part", "permanent", "level", "mid", "entry", "experienced", "urgent", "hiring", "opening", "f", "m", "d", "w",
         "india", "global", "team", "head", "chief", "intern", "trainee", "role", "position", "job", "years", "yrs"}
_SYN = {
    "developer": "eng", "engineer": "eng", "programmer": "eng", "sde": "eng", "swe": "eng", "dev": "eng",
    "engineering": "eng", "development": "eng",
    "administrator": "admin", "admin": "admin", "administration": "admin",
    "tester": "qa", "testing": "qa", "test": "qa", "qa": "qa", "quality": "qa", "sdet": "qa", "assurance": "qa",
    "analyst": "analyst", "analytics": "analyst", "analysis": "analyst",
    "devops": "devops", "sre": "devops", "reliability": "devops", "site": "devops", "platform": "devops",
    "infra": "infra", "infrastructure": "infra", "systems": "system", "system": "system", "sysadmin": "system",
    "frontend": "frontend", "front": "frontend", "ui": "frontend",
    "backend": "backend", "back": "backend", "server": "backend",
    "fullstack": "fullstack", "full-stack": "fullstack", "stack": "fullstack",
    "ml": "ml", "machine": "ml", "learning": "ml", "ai": "ml",
    "network": "network", "networking": "network", "networks": "network",
    "security": "security", "cybersecurity": "security", "cyber": "security", "infosec": "security",
    "support": "support", "helpdesk": "support", "desk": "support", "service": "support",
    "software": "software", "application": "software", "applications": "software", "app": "software",
    "telecom": "telecom", "telecommunications": "telecom", "wireless": "telecom", "ran": "telecom", "rf": "telecom",
    "embedded": "embedded", "firmware": "embedded",
    "manager": "manager", "management": "manager", "mgr": "manager",
    "consultant": "consultant", "consulting": "consultant", "specialist": "consultant",
    "architect": "architect", "architecture": "architect",
    "data": "data", "cloud": "cloud", "mobile": "mobile", "android": "mobile", "ios": "mobile",
    "automation": "automation", "technical": "technical", "tech": "technical", "it": "it",
}


def _role_tokens(title: str):
    words = re.findall(r"[a-z0-9+#.\-]+", (title or "").lower().replace("/", " "))
    toks = set()
    for w in words:
        w = w.strip(".-")
        if not w or w in _STOP or w.isdigit():
            continue
        toks.add(_SYN.get(w, w))
    return toks


def role_similarity(job_title: str, roles):
    jt = _role_tokens(job_title)
    if not jt:
        return 0.0, ""
    best, best_role = 0.0, ""
    for r in roles:
        rt = _role_tokens(r)
        if not rt:
            continue
        overlap = len(jt & rt)
        sim = overlap / len(rt) * 0.7 + overlap / len(jt) * 0.3
        if sim > best:
            best, best_role = sim, r
    return min(best, 1.0), best_role


# ---------------------------------------------------------------- location eligibility
_WORLDWIDE = re.compile(r"\b(worldwide|anywhere|global(ly)?|international|remote[- ]first|all countries|any location)\b", re.I)
COUNTRY_REGIONS = {
    "india": ["india", "asia", "apac", "asia pacific", "asia-pacific", "south asia", "bangalore", "bengaluru", "hyderabad",
              "pune", "chennai", "mumbai", "delhi", "new delhi", "ncr", "gurgaon", "gurugram", "noida", "kolkata",
              "ahmedabad", "kochi", "cochin", "trivandrum", "thiruvananthapuram", "coimbatore", "jaipur", "chandigarh",
              "indore", "mysore", "mysuru", "visakhapatnam", "vizag", "vijayawada", "nagpur", "bhubaneswar", "mohali",
              "lucknow", "kerala", "karnataka", "telangana", "tamil nadu", "maharashtra", "andhra pradesh", "ist"],
    "united states": ["usa", "united states", "u.s.", r"\bus\b", "america", "north america", "americas"],
    "canada": ["canada", "north america", "americas"],
    "united kingdom": ["uk", "united kingdom", "england", "britain", "london", "europe", "emea"],
    "germany": ["germany", "deutschland", "berlin", "munich", "europe", r"\beu\b", "emea", "dach"],
    "netherlands": ["netherlands", "amsterdam", "europe", r"\beu\b", "emea"],
    "ireland": ["ireland", "dublin", "europe", r"\beu\b", "emea"],
    "singapore": ["singapore", "asia", "apac", "asia pacific"],
    "united arab emirates": ["uae", "united arab emirates", "dubai", "abu dhabi", "middle east", "mena", "gcc", "emea"],
    "australia": ["australia", "sydney", "melbourne", "apac", "asia pacific", "oceania"],
}


def _country_patterns(profile):
    country = (profile.get("country") or "").strip().lower()
    pats = list(COUNTRY_REGIONS.get(country, [country] if country else []))
    for loc in profile.get("search_locations") or []:
        l = loc.strip().lower()
        if l and l not in ("remote", "worldwide", "anywhere"):
            pats.append(l)
    rx = []
    for p in pats:
        rx.append(re.compile(p if p.startswith("\\b") else r"(?<![a-z])" + re.escape(p) + r"(?![a-z])", re.I))
    return rx


def location_eligibility(job, profile, pats):
    """Returns ('yes'|'maybe'|'no', note)."""
    src = job.get("source")
    restriction = (job.get("location_restriction") or "").strip()
    location = (job.get("location") or "").strip()
    remote = bool(job.get("remote"))
    if src in ("linkedin", "naukri"):
        if remote and not profile.get("remote_ok", True):
            return "maybe", "Remote role"
        return "yes", location
    text = f"{restriction} {location}".strip()
    if not text:
        return ("maybe", "Location not stated") if remote else ("maybe", "Location unknown")
    if _WORLDWIDE.search(text):
        return "yes", "Open worldwide"
    if any(p.search(text) for p in pats):
        return "yes", text[:80]
    if remote and not restriction and re.fullmatch(r"(?i)\s*remote\s*", location or "remote"):
        return "maybe", "Remote, region not stated"
    return "no", f"Limited to {text[:80]}"


# ---------------------------------------------------------------- scoring helpers
def _applicant_count(text):
    if not text:
        return None
    t = text.lower()
    m = re.search(r"(\d[\d,]*)", t)
    if not m:
        return None
    n = int(m.group(1).replace(",", ""))
    if "first" in t:
        return min(n, 25)
    return n


def competition_score(applicants):
    n = _applicant_count(applicants)
    if n is None:
        return 0.6, "Applicant count unknown"
    if n <= 25:
        return 1.0, f"Only {n} applicants so far" if "first" not in (applicants or "").lower() else "Early applicant"
    if n <= 50:
        return 0.85, f"{n} applicants"
    if n <= 100:
        return 0.7, f"{n} applicants"
    if n <= 200:
        return 0.5, f"{n} applicants"
    return 0.35, f"{n}+ applicants, crowded"


def freshness_score(posted_at):
    d = days_ago(posted_at)
    if d is None:
        return 0.5, "Post date unknown"
    if d <= 1:
        return 1.0, "Posted today"
    if d <= 3:
        return 0.95, f"Posted {int(d)} days ago"
    if d <= 7:
        return 0.8, f"Posted {int(d)} days ago"
    if d <= 14:
        return 0.6, f"Posted {int(d)} days ago"
    if d <= 30:
        return 0.4, f"Posted {int(d)} days ago"
    return 0.2, f"Posted {int(d)} days ago"


def experience_fit(years, job):
    lo, hi, src = job.get("exp_min"), job.get("exp_max"), job.get("exp_source") or ""
    inferred = False
    if lo is None and hi is None:
        lo, hi = seniority_from_title(job.get("title"), job.get("seniority"))
        inferred = lo is not None
        src = "job title"
    if years is None:
        return 0.7, False, "Add your years of experience for accurate matching", lo, hi
    if lo is None:
        return 0.75, False, "Experience not specified", lo, hi
    if hi is None:
        hi = lo + 7
    rng = f"{lo:g}-{hi:g} yrs" if hi < lo + 7 or src != "description" else f"{lo:g}+ yrs"
    label = f"Needs {rng}" + (" (from title)" if inferred else "")
    if years < lo:
        d = lo - years
        excl = d > (4 if inferred else 2)
        return max(0.0, 1 - 0.3 * d), excl, f"{label}, you have {years:g}", lo, hi
    if years > hi:
        o = years - hi
        excl = o > (8 if inferred else 5)
        return max(0.3, 1 - 0.1 * o), excl, f"{label}, you may be overqualified", lo, hi
    return 1.0, False, f"{label}, you fit", lo, hi


# ---------------------------------------------------------------- main scoring
class ScoringContext:
    def __init__(self, profile):
        self.profile = profile
        self.user_skills = {canonicalize(s) for s in profile.get("skills") or [] if s}
        self.custom_skills = [s for s in self.user_skills if s not in SKILL_CATEGORY]
        roles = list(profile.get("target_roles") or [])
        if profile.get("current_title"):
            roles.append(profile["current_title"])
        if not roles:
            roles = list(profile.get("suggested_roles") or [])
        self.roles = roles
        self.years = profile.get("years_experience")
        try:
            self.years = float(self.years) if self.years not in (None, "") else None
        except (TypeError, ValueError):
            self.years = None
        self.pats = _country_patterns(profile)


def score_job(job: dict, ctx: ScoringContext) -> dict:
    js = dict(job.get("job_skills") or {})
    text = job.get("description_text") or ""
    title = job.get("title") or ""
    for cs in ctx.custom_skills:
        rx = _custom_regex(cs)
        if rx.search(title):
            js[cs] = 3
        elif rx.search(text) or any(rx.search(t) for t in job.get("tags") or [] if isinstance(t, str)):
            js.setdefault(cs, 1)

    notes = []
    matched = sorted([s for s in js if s in ctx.user_skills], key=lambda s: -js[s])
    missing = sorted([s for s in js if s not in ctx.user_skills], key=lambda s: (-js[s], s))

    # Skill fit
    if js:
        tot = max(sum(js.values()), 4)
        cov = sum(js[s] for s in matched) / tot
        depth = min(len(matched) / 5, 1.0)
        skill = 0.55 * cov + 0.45 * depth
        title_need = [s for s in js if js[s] == 3]
        if title_need and not any(s in ctx.user_skills for s in title_need):
            skill *= 0.6
            notes.append(f"Title asks for {', '.join(title_need[:3])}, which is not in your skills")
    else:
        skill = None

    # Role similarity
    role, role_match = role_similarity(title, ctx.roles) if ctx.roles else (0.5, "")
    if any(js.get(s) == 3 for s in matched):
        role = max(role, 0.6)

    # Experience
    exp, exp_excl, exp_note, lo, hi = experience_fit(ctx.years, job)

    if skill is None:
        skill_eff = role * 0.4
        notes.append("Job description had no recognisable skills, score is approximate")
    else:
        skill_eff = skill
    match = 100 * (W_SKILL * skill_eff + W_EXP * exp + W_ROLE * role)

    fresh, fresh_note = freshness_score(job.get("posted_at"))
    comp, comp_note = competition_score(job.get("applicants"))
    loc, loc_note = location_eligibility(job, ctx.profile, ctx.pats)
    chance = 0.75 * match + 100 * (0.13 * fresh + 0.12 * comp)
    if loc == "maybe":
        chance -= 6

    excluded, reason = False, None
    if not ctx.user_skills:
        excluded, reason = False, None
    elif exp_excl:
        excluded, reason = True, exp_note
    elif loc == "no":
        excluded, reason = True, loc_note
    elif js and not matched and role < 0.5:
        excluded, reason = True, "No overlapping skills"

    chance = max(0.0, min(100.0, chance))
    label = "High" if chance >= 68 else "Medium" if chance >= 50 else "Low"
    if label == "High" and (skill is None or len(matched) < 2):
        label = "Medium"
    return {
        "match_score": round(match, 1),
        "chance_score": round(chance, 1),
        "chance_label": label,
        "matched_skills": matched,
        "missing_skills": missing[:12],
        "excluded": excluded,
        "exclude_reason": reason,
        "breakdown": {
            "skills": round(100 * skill_eff), "experience": round(100 * exp), "role": round(100 * role),
            "freshness": round(100 * fresh), "competition": round(100 * comp),
            "exp_note": exp_note, "exp_min": lo, "exp_max": hi,
            "role_note": f"Closest to your target role \"{role_match}\"" if role_match and role >= 0.4 else
                         ("Different role title, matched on skills" if role_match else ""),
            "fresh_note": fresh_note, "comp_note": comp_note,
            "location": loc, "location_note": loc_note,
            "notes": notes,
        },
    }

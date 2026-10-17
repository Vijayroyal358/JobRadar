"""Text helpers: HTML cleanup, experience parsing, dates."""
import html as htmlmod
import re
from datetime import datetime, timedelta, timezone

from bs4 import BeautifulSoup

ALLOWED_TAGS = {"p", "br", "ul", "ol", "li", "strong", "b", "em", "i", "u", "h1", "h2", "h3", "h4", "h5", "h6",
                "a", "span", "div", "table", "thead", "tbody", "tr", "td", "th", "blockquote", "hr", "code", "pre"}


def sanitize_html(raw: str) -> str:
    """Keep a safe subset of HTML for the JD preview."""
    if not raw:
        return ""
    if "&lt;" in raw and "<" not in raw.replace("&lt;", ""):
        raw = htmlmod.unescape(raw)
    soup = BeautifulSoup(raw, "html.parser")
    for bad in soup(["script", "style", "iframe", "object", "embed", "form", "input", "button", "img", "svg", "noscript"]):
        bad.decompose()
    for tag in soup.find_all(True):
        if tag.name not in ALLOWED_TAGS:
            tag.unwrap()
            continue
        href = tag.get("href") if tag.name == "a" else None
        tag.attrs = {}
        if href and re.match(r"^https?://", href):
            tag.attrs = {"href": href, "target": "_blank", "rel": "noopener noreferrer"}
    out = str(soup)
    out = re.sub(r"(<br\s*/?>\s*){2,}", "<br>", out)
    out = re.sub(r"<p>\s*(<br\s*/?>)?\s*</p>", "", out)
    out = re.sub(r"(<br\s*/?>\s*)+(</?(?:ul|ol|li|p|h\d)>)", r"\2", out)
    return out.strip()


def html_to_text(raw: str) -> str:
    if not raw:
        return ""
    if "&lt;" in raw and "<" not in raw.replace("&lt;", ""):
        raw = htmlmod.unescape(raw)
    soup = BeautifulSoup(raw, "html.parser")
    for br in soup.find_all(["br", "p", "li", "div", "h1", "h2", "h3", "h4", "tr"]):
        br.append("\n")
    text = soup.get_text(" ")
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def text_to_html(text: str) -> str:
    if not text:
        return ""
    paras = [p.strip() for p in re.split(r"\n\s*\n|\n", text) if p.strip()]
    return "".join(f"<p>{htmlmod.escape(p)}</p>" for p in paras)


# ---------------------------------------------------------------- experience in job descriptions
_NUM = r"(\d{1,2}(?:\.\d)?)"
_YRS = r"(?:years?|yrs?)"
_RANGE = re.compile(_NUM + r"\s*\+?\s*(?:-|–|—|to)\s*" + _NUM + r"\s*\+?\s*" + _YRS, re.I)
_PLUS = re.compile(_NUM + r"\s*\+\s*" + _YRS, re.I)
_MIN = re.compile(r"(?:minimum|min\.?|at\s*least|atleast|over|more\s+than)\s*(?:of\s*)?" + _NUM + r"\s*\+?\s*" + _YRS, re.I)
_PLAIN = re.compile(_NUM + r"\s*" + _YRS + r"\s*(?:of\s+)?(?:(?!(?:years?|yrs?|ago)\b)[A-Za-z/\-&+.,]+\s+){0,5}?(?:experience|exp\b|hands)", re.I)
_EXPERIENCE_CTX = re.compile(r"experience|exp\b|hands[- ]on|background|working", re.I)
_NOT_EXPERIENCE = re.compile(r"old|age|warranty|contract|company|founded|history|in business|guarantee|tenure|degree|bachelor|master", re.I)


def parse_experience_range(text: str):
    """Return (min_years, max_years) required by a JD, or (None, None)."""
    if not text:
        return None, None
    cands = []
    for rx, kind in ((_RANGE, "range"), (_MIN, "min"), (_PLUS, "plus"), (_PLAIN, "plain")):
        for m in rx.finditer(text):
            ctx_after = text[m.end(): m.end() + 70]
            ctx_before = text[max(0, m.start() - 40): m.start()]
            near = m.group(0) + " " + ctx_after
            if _NOT_EXPERIENCE.search(ctx_before[-20:] + m.group(0) + ctx_after[:25]):
                continue
            if kind != "plain" and not _EXPERIENCE_CTX.search(near) and not _EXPERIENCE_CTX.search(ctx_before):
                continue
            lo = float(m.group(1))
            hi = float(m.group(2)) if kind == "range" else None
            if lo > 25 or (hi is not None and (hi > 30 or hi < lo)):
                continue
            cands.append((lo, hi, kind))
    if not cands:
        return None, None
    ranges = [c for c in cands if c[2] == "range"]
    if ranges:
        lo, hi, _ = max(ranges, key=lambda c: c[0])
        return lo, hi
    lo = max(c[0] for c in cands)
    return lo, None


def parse_label_experience(label: str):
    """Naukri style '2-5 Yrs', '10+ Yrs', 'Fresher'."""
    if not label:
        return None, None
    if re.search(r"fresher", label, re.I):
        return 0.0, 1.0
    m = re.search(r"(\d+)\s*-\s*(\d+)", label)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = re.search(r"(\d+)", label)
    if m:
        return float(m.group(1)), None
    return None, None


SENIORITY_HINTS = [
    (re.compile(r"\b(intern|internship|trainee|fresher|graduate|apprentice)\b", re.I), (0.0, 1.0)),
    (re.compile(r"\b(junior|jr\.?|entry[- ]level|associate)\b", re.I), (0.0, 3.0)),
    (re.compile(r"\b(principal|staff|distinguished|architect)\b", re.I), (8.0, 20.0)),
    (re.compile(r"\b(director|head of|vp|vice president|chief)\b", re.I), (10.0, 25.0)),
    (re.compile(r"\b(lead|manager)\b", re.I), (6.0, 15.0)),
    (re.compile(r"\b(senior|sr\.?)\b", re.I), (4.0, 12.0)),
    (re.compile(r"\b(mid[- ]level|intermediate)\b", re.I), (2.0, 6.0)),
]


def seniority_from_title(title: str, extra: str = ""):
    s = f"{title or ''} {extra or ''}"
    for rx, rng in SENIORITY_HINTS:
        if rx.search(s):
            return rng
    return None, None


# ---------------------------------------------------------------- dates
def now_utc():
    return datetime.now(timezone.utc)


def iso(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_date(value):
    """Accepts epoch seconds, ISO strings, 'YYYY-MM-DD', or relative strings like '3 days ago'."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        v = float(value)
        if v > 1e12:
            v /= 1000
        return datetime.fromtimestamp(v, tz=timezone.utc)
    s = str(value).strip()
    if s.isdigit():
        return parse_date(int(s))
    rel = parse_relative(s)
    if rel:
        return rel
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d", "%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            dt = datetime.strptime(s.replace("Z", "+0000") if "%z" in fmt else s, fmt)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def parse_relative(s: str):
    s = s.lower().strip()
    if s in ("today", "just now", "just posted", "few hours ago") or "hour" in s or "minute" in s or "second" in s:
        return now_utc()
    if s == "yesterday":
        return now_utc() - timedelta(days=1)
    m = re.search(r"(\d+)\+?\s*(day|week|month|year)s?\s*ago", s)
    if m:
        n = int(m.group(1))
        mult = {"day": 1, "week": 7, "month": 30, "year": 365}[m.group(2)]
        return now_utc() - timedelta(days=n * mult)
    return None


def days_ago(iso_str):
    dt = parse_date(iso_str)
    if not dt:
        return None
    return max(0, (now_utc() - dt).total_seconds() / 86400)


def norm_key(*parts):
    s = " ".join(p or "" for p in parts).lower()
    s = re.sub(r"\b(pvt|private|ltd|limited|inc|llc|gmbh|corp|corporation|technologies|technology|solutions|india)\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

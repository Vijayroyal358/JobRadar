"""Remote / international job boards with public APIs or feeds."""
import html as htmlmod
import re
import xml.etree.ElementTree as ET

from ..textutil import html_to_text, iso, parse_date, sanitize_html
from .base import Scraper


def _iso(v):
    return iso(parse_date(v)) if v not in (None, "") else None


def _salary(lo, hi, cur="", period=""):
    try:
        lo = int(float(lo or 0))
        hi = int(float(hi or 0))
    except (TypeError, ValueError):
        return None
    if not lo and not hi:
        return None
    fmt = lambda n: f"{n / 1000:.0f}k" if n >= 1000 else str(n)
    rng = f"{fmt(lo)}-{fmt(hi)}" if lo and hi else fmt(lo or hi)
    return f"{cur or ''} {rng}{(' / ' + period) if period else ''}".strip()


def _desc(raw):
    raw = raw or ""
    return sanitize_html(raw), html_to_text(raw)


class Remotive(Scraper):
    key = "remotive"
    label = "Remotive"
    region = "Remote"
    description = "Curated remote tech jobs."

    def run(self, ctx):
        terms = list(dict.fromkeys(ctx.queries + (ctx.profile.get("skills") or [])[:4]))
        seen = set()
        for i, q in enumerate(terms):
            if ctx.stopped:
                return
            try:
                data = self.get("https://remotive.com/api/remote-jobs", params={"search": q, "limit": 100}, as_json=True)
            except Exception as e:
                ctx.log(f"Remotive '{q}': {e}")
                continue
            for j in data.get("jobs", []):
                if j["id"] in seen:
                    continue
                seen.add(j["id"])
                h, t = _desc(j.get("description"))
                ctx.emit({
                    "source": self.key, "source_id": j["id"], "url": j.get("url"), "apply_url": j.get("url"),
                    "title": j.get("title"), "company": j.get("company_name"), "company_logo": j.get("company_logo"),
                    "location": j.get("candidate_required_location") or "Remote", "remote": True,
                    "location_restriction": j.get("candidate_required_location"),
                    "job_type": (j.get("job_type") or "").replace("_", " ").title(), "salary": j.get("salary") or None,
                    "posted_at": _iso(j.get("publication_date")), "description_html": h, "description_text": t,
                    "tags": j.get("tags") or [], "query": q, "detail_fetched": 1,
                })
            ctx.progress(i + 1, len(terms))
        ctx.log(f"Remotive: {len(seen)} postings")


class RemoteOK(Scraper):
    key = "remoteok"
    label = "RemoteOK"
    region = "Remote"
    description = "Large remote job feed, filtered locally by your skills."

    def run(self, ctx):
        data = self.get("https://remoteok.com/api", as_json=True, timeout=40)
        jobs = [j for j in data if isinstance(j, dict) and j.get("id") and j.get("position")]
        for i, j in enumerate(jobs):
            if ctx.stopped:
                return
            h, t = _desc(j.get("description"))
            ctx.emit({
                "source": self.key, "source_id": j["id"], "url": j.get("url"), "apply_url": j.get("apply_url") or j.get("url"),
                "title": htmlmod.unescape(j.get("position") or ""), "company": j.get("company"),
                "company_logo": j.get("company_logo") or j.get("logo") or None,
                "location": j.get("location") or "Remote", "remote": True, "location_restriction": j.get("location"),
                "salary": _salary(j.get("salary_min"), j.get("salary_max"), "USD", "yr"),
                "posted_at": _iso(j.get("epoch") or j.get("date")), "description_html": h, "description_text": t,
                "tags": j.get("tags") or [], "detail_fetched": 1,
            })
            if i % 20 == 0:
                ctx.progress(i + 1, len(jobs))
        ctx.progress(1, 1)
        ctx.log(f"RemoteOK: {len(jobs)} postings scanned")


class Himalayas(Scraper):
    key = "himalayas"
    label = "Himalayas"
    region = "Remote"
    description = "Remote jobs with clear country eligibility."

    def run(self, ctx):
        seen = set()
        terms = ctx.queries
        for i, q in enumerate(terms):
            if ctx.stopped:
                return
            for page in (1, 2):
                try:
                    data = self.get("https://himalayas.app/jobs/api/search",
                                    params={"q": q, "page": page, "sort": "recent"}, as_json=True)
                except Exception as e:
                    ctx.log(f"Himalayas '{q}': {e}")
                    break
                jobs = data.get("jobs") or []
                for j in jobs:
                    gid = j.get("guid") or j.get("applicationLink")
                    if not gid or gid in seen:
                        continue
                    seen.add(gid)
                    h, t = _desc(j.get("description"))
                    restr = ", ".join(j.get("locationRestrictions") or [])
                    sen = j.get("seniority") or []
                    ctx.emit({
                        "source": self.key, "source_id": gid, "url": j.get("applicationLink") or gid,
                        "apply_url": j.get("applicationLink") or gid, "title": j.get("title"),
                        "company": j.get("companyName"), "company_logo": j.get("companyLogo"),
                        "location": restr or "Remote (worldwide)", "remote": True,
                        "location_restriction": restr or "Worldwide",
                        "job_type": j.get("employmentType"),
                        "salary": _salary(j.get("minSalary"), j.get("maxSalary"), j.get("currency"), j.get("salaryPeriod")),
                        "posted_at": _iso(j.get("pubDate")), "description_html": h, "description_text": t,
                        "tags": (j.get("categories") or [])[:15], "seniority": ", ".join(sen) if isinstance(sen, list) else sen,
                        "query": q, "detail_fetched": 1,
                    })
                if len(jobs) < 10:
                    break
            ctx.progress(i + 1, len(terms))
        ctx.log(f"Himalayas: {len(seen)} postings")


class Jobicy(Scraper):
    key = "jobicy"
    label = "Jobicy"
    region = "Remote"
    description = "Remote jobs feed searchable by keyword."

    def run(self, ctx):
        seen = set()
        terms = list(dict.fromkeys(ctx.queries + (ctx.profile.get("skills") or [])[:3]))
        for i, q in enumerate(terms):
            if ctx.stopped:
                return
            try:
                data = self.get("https://jobicy.com/api/v2/remote-jobs", params={"count": 50, "tag": q}, as_json=True)
            except Exception as e:
                ctx.log(f"Jobicy '{q}': {e}")
                continue
            for j in data.get("jobs") or []:
                if j["id"] in seen:
                    continue
                seen.add(j["id"])
                h, t = _desc(j.get("jobDescription"))
                jt = j.get("jobType")
                ctx.emit({
                    "source": self.key, "source_id": j["id"], "url": j.get("url"), "apply_url": j.get("url"),
                    "title": htmlmod.unescape(j.get("jobTitle") or ""), "company": j.get("companyName"),
                    "company_logo": j.get("companyLogo"), "location": j.get("jobGeo") or "Remote", "remote": True,
                    "location_restriction": j.get("jobGeo"),
                    "job_type": ", ".join(jt) if isinstance(jt, list) else jt,
                    "salary": _salary(j.get("salaryMin"), j.get("salaryMax"), j.get("salaryCurrency"), j.get("salaryPeriod")),
                    "posted_at": _iso(j.get("pubDate")), "description_html": h, "description_text": t,
                    "tags": j.get("jobIndustry") or [], "seniority": j.get("jobLevel"), "query": q, "detail_fetched": 1,
                })
            ctx.progress(i + 1, len(terms))
        ctx.log(f"Jobicy: {len(seen)} postings")


class WeWorkRemotely(Scraper):
    key = "weworkremotely"
    label = "We Work Remotely"
    region = "Remote"
    description = "One of the biggest remote job boards (RSS feed)."

    def run(self, ctx):
        r = self.get("https://weworkremotely.com/remote-jobs.rss", timeout=40)
        root = ET.fromstring(r.content)
        items = root.findall("./channel/item")
        for i, it in enumerate(items):
            if ctx.stopped:
                return
            g = lambda tag: (it.findtext(tag) or "").strip()
            full = g("title")
            company, _, title = full.partition(":")
            if not title:
                company, title = "", full
            link = g("link") or g("guid")
            raw = g("description")
            h, t = _desc(raw)
            region = g("region")
            country = g("country")
            skills = [s.strip() for s in g("skills").split(",") if s.strip()]
            ctx.emit({
                "source": self.key, "source_id": g("guid") or link, "url": link, "apply_url": link,
                "title": title.strip(), "company": company.strip(), "location": ", ".join(x for x in (region, country) if x) or "Remote",
                "remote": True, "location_restriction": ", ".join(x for x in (region, country) if x),
                "job_type": g("type"), "posted_at": _iso(g("pubDate")), "description_html": h, "description_text": t,
                "tags": skills + ([g("category")] if g("category") else []), "detail_fetched": 1,
            })
            if i % 25 == 0:
                ctx.progress(i + 1, len(items))
        ctx.progress(1, 1)
        ctx.log(f"We Work Remotely: {len(items)} postings scanned")


class Arbeitnow(Scraper):
    key = "arbeitnow"
    label = "Arbeitnow"
    region = "Europe + remote"
    description = "European tech jobs and visa-sponsored roles."

    def run(self, ctx):
        n = 0
        pages = 2
        for page in range(1, pages + 1):
            if ctx.stopped:
                return
            try:
                data = self.get("https://www.arbeitnow.com/api/job-board-api", params={"page": page}, as_json=True, timeout=40)
            except Exception as e:
                ctx.log(f"Arbeitnow page {page}: {e}")
                break
            for j in data.get("data") or []:
                h, t = _desc(htmlmod.unescape(j.get("description") or ""))
                ctx.emit({
                    "source": self.key, "source_id": j["slug"], "url": j.get("url"), "apply_url": j.get("url"),
                    "title": j.get("title"), "company": j.get("company_name"), "location": j.get("location"),
                    "remote": bool(j.get("remote")), "location_restriction": j.get("location"),
                    "job_type": ", ".join(j.get("job_types") or []), "posted_at": _iso(j.get("created_at")),
                    "description_html": h, "description_text": t, "tags": j.get("tags") or [], "detail_fetched": 1,
                })
                n += 1
            ctx.progress(page, pages)
            if not (data.get("links") or {}).get("next"):
                break
        ctx.log(f"Arbeitnow: {n} postings scanned")


MUSE_CATEGORIES = ["Software Engineering", "Data and Analytics", "Data Science", "IT", "Computer and IT",
                   "Project Management", "Product Management", "Design and UX"]


class TheMuse(Scraper):
    key = "themuse"
    label = "The Muse"
    region = "US / remote"
    description = "Company-verified jobs, mostly US and flexible/remote."

    def run(self, ctx):
        country = (ctx.profile.get("country") or "").strip()
        locations = ["Flexible / Remote"]
        for l in ctx.locations:
            if l.lower() not in ("remote",):
                locations.append(l if "," in l or not country or l.lower() == country.lower() else f"{l}, {country}")
        params = [("category", c) for c in MUSE_CATEGORIES] + [("location", l) for l in locations]
        n = 0
        pages = 5
        for page in range(pages):
            if ctx.stopped:
                return
            try:
                data = self.get("https://www.themuse.com/api/public/jobs", params=params + [("page", page)], as_json=True)
            except Exception as e:
                ctx.log(f"The Muse page {page}: {e}")
                break
            for j in data.get("results") or []:
                h, t = _desc(j.get("contents"))
                locs = ", ".join(l.get("name", "") for l in j.get("locations") or [])
                link = (j.get("refs") or {}).get("landing_page")
                ctx.emit({
                    "source": self.key, "source_id": j["id"], "url": link, "apply_url": link,
                    "title": j.get("name"), "company": (j.get("company") or {}).get("name"),
                    "location": locs, "remote": "remote" in locs.lower() or "flexible" in locs.lower(),
                    "location_restriction": locs, "posted_at": _iso(j.get("publication_date")),
                    "description_html": h, "description_text": t,
                    "tags": [c.get("name") for c in j.get("categories") or []],
                    "seniority": ", ".join(l.get("name", "") for l in j.get("levels") or []), "detail_fetched": 1,
                })
                n += 1
            ctx.progress(page + 1, pages)
            if page + 1 >= (data.get("page_count") or 0):
                break
        ctx.log(f"The Muse: {n} postings scanned")

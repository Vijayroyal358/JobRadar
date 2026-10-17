"""Naukri.com via a real Chrome/Edge browser (Naukri blocks plain HTTP clients with a captcha).

The browser opens Naukri's normal search page and reads the JSON the page itself loads.
"""
import re
from urllib.parse import quote

from ..textutil import html_to_text, parse_date, parse_label_experience, sanitize_html
from .base import UA, Blocked, Scraper


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def _job_age(days):
    for v in (1, 3, 7, 15, 30):
        if days <= v:
            return v
    return 30


def _launch(p, headless):
    args = [
        "--disable-blink-features=AutomationControlled",
        "--no-first-run",
        "--no-default-browser-check",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
    ]
    last = None
    for channel in ("chrome", "msedge", None):
        try:
            kw = {"headless": headless, "args": args}
            if channel:
                kw["channel"] = channel
            return p.chromium.launch(**kw)
        except Exception as e:
            last = e
    raise RuntimeError(f"Could not start Chrome or Edge for Naukri: {last}")


class Naukri(Scraper):
    key = "naukri"
    label = "Naukri"
    region = "India"
    description = "India's largest job portal. Uses your installed Chrome/Edge in the background."
    needs_browser = True

    def normalize(self, d, query):
        ph = {x.get("type"): x.get("label") for x in d.get("placeholders") or []}
        lo, hi = parse_label_experience(ph.get("experience"))
        raw_desc = d.get("jobDescription") or ""
        url = "https://www.naukri.com" + d["jdURL"] if (d.get("jdURL") or "").startswith("/") else d.get("jdURL")
        created = d.get("createdDate")
        posted = parse_date(created) if created else parse_date(d.get("footerPlaceholderLabel"))
        tags = [t.strip() for t in (d.get("tagsAndSkills") or "").split(",") if t.strip()]
        return {
            "source": self.key, "source_id": str(d.get("jobId")), "url": url, "apply_url": url,
            "title": d.get("title") or "", "company": d.get("companyName") or "",
            "company_logo": d.get("logoPathV3") or d.get("logoPath"),
            "location": ph.get("location") or "", "remote": bool(re.search(r"remote|work from home|wfh",
                                                                             ph.get("location") or "", re.I)),
            "salary": ph.get("salary") if ph.get("salary") and "not disclosed" not in ph.get("salary", "").lower() else None,
            "posted_at": posted.strftime("%Y-%m-%dT%H:%M:%SZ") if posted else None,
            "description_html": sanitize_html(raw_desc), "description_text": html_to_text(raw_desc),
            "tags": tags, "exp_min": lo, "exp_max": hi, "exp_source": "naukri" if lo is not None else None,
            "query": query, "detail_fetched": 1,
        }

    def run(self, ctx):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise RuntimeError("Playwright is not installed. Run start.bat again to install it.")
        pages = int(ctx.profile.get("naukri_pages") or 2)
        years = ctx.profile.get("years_experience")
        headless = bool(ctx.profile.get("naukri_headless", True))
        country = (ctx.profile.get("country") or "india").lower()
        locs = [l for l in ctx.locations if l.lower() not in (country, "remote", "worldwide")] or [None]
        plan = [(q, l) for q in ctx.queries for l in locs]
        total = len(plan) * pages
        done = 0
        seen = set()
        captcha_hits = 0
        with sync_playwright() as p:
            browser = _launch(p, headless)
            context = browser.new_context(user_agent=UA, viewport={"width": 1366, "height": 900}, locale="en-IN")
            page = context.new_page()
            page.route(re.compile(r"\.(png|jpg|jpeg|gif|webp|woff2?|ttf|svg)(\?|$)"), lambda r: r.abort())
            try:
                for q, loc in plan:
                    for n in range(1, pages + 1):
                        if ctx.stopped:
                            return
                        base = f"{_slug(q)}-jobs" + (f"-in-{_slug(loc)}" if loc else "")
                        if n > 1:
                            base += f"-{n}"
                        url = f"https://www.naukri.com/{base}?k={quote(q)}&jobAge={_job_age(ctx.days)}"
                        if loc:
                            url += f"&l={quote(loc)}"
                        if years not in (None, ""):
                            url += f"&experience={int(float(years))}"
                        data = None
                        try:
                            with page.expect_response(lambda r: "jobapi/v3/search" in r.url, timeout=30000) as info:
                                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                            resp = info.value
                            if resp.status == 406:
                                captcha_hits += 1
                            else:
                                data = resp.json()
                        except Exception as e:
                            ctx.log(f"Naukri page timed out for '{q}' page {n}: {str(e)[:80]}")
                        done += 1
                        ctx.progress(done, total)
                        if captcha_hits >= 3:
                            raise Blocked("Naukri asked for a captcha. Turn off 'Naukri headless' in Settings and run again.")
                        if not data:
                            continue
                        jobs = data.get("jobDetails") or []
                        for d in jobs:
                            if not d.get("jobId") or d["jobId"] in seen:
                                continue
                            seen.add(d["jobId"])
                            ctx.emit(self.normalize(d, q))
                        if len(jobs) < 20:
                            done += pages - n
                            break
                        page.wait_for_timeout(1200)
            finally:
                browser.close()
        ctx.log(f"Naukri: {len(seen)} postings")

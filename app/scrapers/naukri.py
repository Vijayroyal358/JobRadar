"""Naukri.com job search.

Strategy: launch browser ONCE to capture nkparam + session cookies from the first
jobapi/v3/search XHR request, then use requests.Session for all remaining queries.
This is fast and immune to headless detection on subsequent calls.
"""
import re
import time
from urllib.parse import quote

import requests

from ..textutil import html_to_text, parse_date, parse_label_experience, sanitize_html
from .base import STEALTH_INIT_SCRIPT, UA, Blocked, Scraper, launch_browser


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def _job_age(days):
    for v in (1, 3, 7, 15, 30):
        if days <= v:
            return v
    return 30


class Naukri(Scraper):
    key = "naukri"
    label = "Naukri"
    region = "India"
    description = "India's largest job portal."
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

    def _bootstrap_session(self, first_url, headless):
        """Launch browser once, capture nkparam + cookies, return requests.Session."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise RuntimeError("Playwright is not installed.")

        nkparam_holder = {}
        cookies_holder = []

        def on_req(req):
            if "jobapi/v3/search" in req.url and "nkparam" not in nkparam_holder:
                h = req.headers
                nkparam_holder.update({
                    "nkparam": h.get("nkparam", ""),
                    "appid": h.get("appid", "109"),
                    "systemid": h.get("systemid", "Naukri"),
                    "clientid": h.get("clientid", "d3skt0p"),
                    "gid": h.get("gid", "LOCATION,INDUSTRY,EDUCATION,FAREA_ROLE"),
                })

        with sync_playwright() as p:
            browser = launch_browser(p, headless)
            ctx = browser.new_context(user_agent=UA, viewport={"width": 1366, "height": 900}, locale="en-IN")
            ctx.add_init_script(STEALTH_INIT_SCRIPT)
            page = ctx.new_page()
            page.route(re.compile(r"\.(png|jpg|jpeg|gif|webp)(\?|$)"), lambda r: r.abort())
            page.on("request", on_req)
            try:
                page.goto(first_url, wait_until="domcontentloaded", timeout=30000)
                # Wait for API request to fire (up to 6s)
                for _ in range(30):
                    if nkparam_holder:
                        break
                    page.wait_for_timeout(200)
            except Exception:
                pass
            finally:
                cookies_holder.extend(ctx.cookies())
                browser.close()

        if not nkparam_holder:
            return None, None

        s = requests.Session()
        s.headers.update({
            "User-Agent": UA,
            "Accept-Language": "en-IN,en-US;q=0.9,en;q=0.8",
            "Accept": "application/json",
            "content-type": "application/json",
            "appid": nkparam_holder["appid"],
            "systemid": nkparam_holder["systemid"],
            "clientid": nkparam_holder["clientid"],
            "gid": nkparam_holder["gid"],
            "nkparam": nkparam_holder["nkparam"],
        })
        for c in cookies_holder:
            s.cookies.set(c["name"], c["value"], domain=c.get("domain", ".naukri.com"))
        return s, nkparam_holder["nkparam"]

    def _api_search(self, session, query, loc, page_no, days, years):
        """Call Naukri jobapi directly with the bootstrapped session."""
        params = {
            "noOfResults": 20,
            "urlType": "search_by_keyword",
            "searchType": "adv",
            "keyword": query,
            "pageNo": page_no,
            "jobAge": _job_age(days),
        }
        if loc:
            params["location"] = loc
        if years not in (None, ""):
            params["experience"] = int(float(years))
        session.headers["Referer"] = f"https://www.naukri.com/{_slug(query)}-jobs?k={quote(query)}&jobAge={_job_age(days)}"
        r = session.get("https://www.naukri.com/jobapi/v3/search", params=params, timeout=20)
        if r.status_code == 406:
            return None, True   # captcha
        if r.status_code != 200:
            return None, False
        return r.json(), False

    def run(self, ctx):
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

        # Bootstrap: one browser page load to get nkparam + cookies
        first_q, first_loc = plan[0]
        first_url = f"https://www.naukri.com/{_slug(first_q)}-jobs?k={quote(first_q)}&jobAge={_job_age(ctx.days)}"
        if first_loc:
            first_url += f"&l={quote(first_loc)}"

        ctx.log("Naukri: initializing browser session...")
        session, nkparam = self._bootstrap_session(first_url, headless)

        if not session:
            ctx.log("Naukri: could not capture API token. Skipping Naukri search.")
            return

        ctx.log("Naukri: session ready, querying API...")

        for q, loc in plan:
            for n in range(1, pages + 1):
                if ctx.stopped:
                    return
                try:
                    data, is_captcha = self._api_search(session, q, loc, n, ctx.days, years)
                    if is_captcha:
                        captcha_hits += 1
                        ctx.log(f"Naukri captcha hit for '{q}' page {n}")
                except Exception as e:
                    ctx.log(f"Naukri API error for '{q}' page {n}: {str(e)[:80]}")
                    data, is_captcha = None, False

                done += 1
                ctx.progress(done, total)

                if captcha_hits >= 3:
                    raise Blocked("Naukri is blocking requests. Try running with 'Naukri headless' turned off.")

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

                time.sleep(0.8)

        ctx.log(f"Naukri: {len(seen)} postings")

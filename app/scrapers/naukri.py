"""Naukri.com via a real Chrome/Edge browser (Naukri blocks plain HTTP clients with a captcha).

The browser opens Naukri's normal search page and reads the JSON the page itself loads.
"""
import re
from urllib.parse import quote

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
            browser = launch_browser(p, headless)
            context = browser.new_context(user_agent=UA, viewport={"width": 1366, "height": 900}, locale="en-IN")
            context.add_init_script(STEALTH_INIT_SCRIPT)
            page = context.new_page()
            page.route(re.compile(r"\.(png|jpg|jpeg|gif|webp)(\?|$)"), lambda r: r.abort())

            captured = {}

            def on_response(resp):
                if "jobapi/v3/search" in resp.url:
                    if resp.status == 406:
                        captured["captcha"] = True
                    elif resp.status == 200:
                        try:
                            captured["data"] = resp.json()
                        except Exception:
                            pass

            page.on("response", on_response)

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
                        
                        captured.clear()
                        try:
                            page.goto(url, wait_until="domcontentloaded", timeout=30000)
                            # Wait up to 6s for the background search API response
                            for _ in range(30):
                                if "data" in captured or "captcha" in captured or ctx.stopped:
                                    break
                                page.wait_for_timeout(200)
                        except Exception as e:
                            ctx.log(f"Naukri page error for '{q}' page {n}: {str(e)[:80]}")

                        if captured.get("captcha"):
                            captcha_hits += 1

                        data = captured.get("data")
                        done += 1
                        ctx.progress(done, total)
                        if captcha_hits >= 3:
                            raise Blocked("Naukri asked for a captcha. Turn off 'Naukri headless' in Settings and run again.")
                        
                        jobs = (data.get("jobDetails") or []) if data else []
                        if jobs:
                            for d in jobs:
                                if not d.get("jobId") or d["jobId"] in seen:
                                    continue
                                seen.add(d["jobId"])
                                ctx.emit(self.normalize(d, q))
                            if len(jobs) < 20:
                                done += pages - n
                                break
                        else:
                            # DOM fallback: parse job cards directly from the rendered HTML
                            try:
                                from bs4 import BeautifulSoup
                                soup = BeautifulSoup(page.content(), "html.parser")
                                tuples = soup.select(".srp-jobtuple-wrapper") or soup.select(".cust-job-tuple") or soup.select("article.jobTuple")
                                dom_found = 0
                                for t in tuples:
                                    a = t.select_one("a.title") or t.select_one(".title")
                                    if not a or not a.get("href"):
                                        continue
                                    href = a.get("href")
                                    m = re.search(r"-([0-9]{10,14})(?:\?|$)", href)
                                    jid = m.group(1) if m else None
                                    if not jid or jid in seen:
                                        continue
                                    comp = t.select_one(".comp-name") or t.select_one("a.subTitle")
                                    loc_el = t.select_one(".loc-wrap") or t.select_one(".location")
                                    exp_el = t.select_one(".exp-wrap") or t.select_one(".experience")
                                    desc_el = t.select_one(".job-desc") or t.select_one(".job-description")
                                    tags = [tag.get_text(strip=True) for tag in t.select(".tags-gt li, .dot-gt li, .tag-li")]
                                    raw_desc = desc_el.get_text(" ", strip=True) if desc_el else ""
                                    lo, hi = parse_label_experience(exp_el.get_text(strip=True) if exp_el else "")
                                    loc_str = loc_el.get_text(" ", strip=True) if loc_el else (loc or "")
                                    seen.add(jid)
                                    dom_found += 1
                                    ctx.emit({
                                        "source": self.key, "source_id": str(jid), "url": href, "apply_url": href,
                                        "title": a.get_text(" ", strip=True),
                                        "company": comp.get_text(" ", strip=True) if comp else "",
                                        "company_logo": None,
                                        "location": loc_str,
                                        "remote": bool(re.search(r"remote|work from home|wfh", loc_str, re.I)),
                                        "salary": None, "posted_at": None,
                                        "description_html": sanitize_html(raw_desc), "description_text": raw_desc,
                                        "tags": tags, "exp_min": lo, "exp_max": hi, "exp_source": "naukri" if lo is not None else None,
                                        "query": q, "detail_fetched": 1,
                                    })
                                if dom_found < 20 and n > 1:
                                    done += pages - n
                                    break
                            except Exception as e:
                                ctx.log(f"Naukri DOM parse error: {str(e)[:60]}")
                        page.wait_for_timeout(1000)
            finally:
                browser.close()
        ctx.log(f"Naukri: {len(seen)} postings")

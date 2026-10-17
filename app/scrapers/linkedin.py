import os
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qs, quote, unquote, urlparse

from bs4 import BeautifulSoup

from ..textutil import html_to_text, sanitize_html
from .base import STEALTH_INIT_SCRIPT, UA, Blocked, Scraper, launch_browser

SEARCH = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
DETAIL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{}"


def _exp_levels(years):
    """LinkedIn f_E: 1 intern, 2 entry, 3 associate, 4 mid-senior, 5 director, 6 executive."""
    if years is None:
        return None
    y = float(years)
    if y < 1:
        return "1,2"
    if y < 3:
        return "2,3"
    if y < 7:
        return "3,4"
    if y < 12:
        return "4"
    return "4,5"


class LinkedIn(Scraper):
    key = "linkedin"
    label = "LinkedIn"
    region = "Global / your locations"
    description = "Public LinkedIn job search, including full descriptions and applicant counts."

    def _search(self, ctx, keywords, location, start, remote=False):
        params = {"keywords": keywords, "location": location, "f_TPR": f"r{ctx.days * 86400}", "start": start}
        lv = _exp_levels(ctx.profile.get("years_experience"))
        if lv:
            params["f_E"] = lv
        if remote:
            params["f_WT"] = "2"
        r = self.get(SEARCH, params=params, throttle=(1.0, 2.0))
        soup = BeautifulSoup(r.text, "html.parser")
        out = []
        for card in soup.select("div.base-card"):
            urn = card.get("data-entity-urn") or ""
            jid = urn.rsplit(":", 1)[-1]
            if not jid.isdigit():
                continue
            t = card.select_one("h3.base-search-card__title")
            c = card.select_one("h4.base-search-card__subtitle")
            loc = card.select_one(".job-search-card__location")
            tm = card.select_one("time")
            a = card.select_one("a.base-card__full-link")
            img = card.select_one("img")
            url = (a.get("href") or "").split("?")[0] if a else f"https://www.linkedin.com/jobs/view/{jid}"
            title = t.get_text(" ", strip=True) if t else ""
            location_text = loc.get_text(" ", strip=True) if loc else location
            out.append({
                "source": self.key, "source_id": jid, "url": url, "apply_url": url,
                "title": title, "company": c.get_text(" ", strip=True) if c else "",
                "company_logo": img.get("data-delayed-url") if img else None,
                "location": location_text,
                "remote": remote or bool(re.search(r"remote", location_text or "", re.I)),
                "posted_at": tm.get("datetime") if tm else None,
                "query": keywords,
                "detail_fetched": 0,
            })
        return out

    def fetch_detail(self, jid):
        r = self.get(DETAIL.format(jid), throttle=(0.8, 1.6))
        soup = BeautifulSoup(r.text, "html.parser")
        d = {"detail_fetched": 1}
        desc = soup.select_one(".show-more-less-html__markup") or soup.select_one(".description__text")
        if desc:
            raw = str(desc)
            d["description_html"] = sanitize_html(raw)
            d["description_text"] = html_to_text(raw)
        ap = soup.select_one(".num-applicants__caption") or soup.select_one(".num-applicants__figure")
        if ap:
            d["applicants"] = ap.get_text(" ", strip=True)
        for item in soup.select(".description__job-criteria-item"):
            h = item.select_one(".description__job-criteria-subheader")
            v = item.select_one(".description__job-criteria-text")
            if not h or not v:
                continue
            key, val = h.get_text(strip=True).lower(), v.get_text(" ", strip=True)
            if "seniority" in key:
                d["seniority"] = val
            elif "employment" in key:
                d["job_type"] = val
        code = soup.select_one("code#applyUrl")
        if code:
            m = re.search(r'"(https?://[^"]+)"', code.decode_contents())
            if m:
                link = m.group(1)
                qs = parse_qs(urlparse(link).query)
                d["apply_url"] = unquote(qs["url"][0]) if "url" in qs else link
        return d

    def _search_browser(self, ctx, plan, cards):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            ctx.log("LinkedIn: Playwright not installed, skipping browser search.")
            return
        headless = bool(ctx.profile.get("linkedin_headless", True))
        try:
            with sync_playwright() as p:
                browser = launch_browser(p, headless)
                context = browser.new_context(user_agent=UA, viewport={"width": 1366, "height": 900}, locale="en-IN")
                context.add_init_script(STEALTH_INIT_SCRIPT)
                page = context.new_page()
                page.route(re.compile(r"\.(png|jpg|jpeg|gif|webp)(\?|$)"), lambda r: r.abort())
                try:
                    for q, loc, remote in plan:
                        if ctx.stopped:
                            return
                        url = f"https://www.linkedin.com/jobs/search?keywords={quote(q)}"
                        if loc:
                            url += f"&location={quote(loc)}"
                        if remote:
                            url += "&f_WT=2"
                        url += f"&f_TPR=r{ctx.days * 86400}"
                        lv = _exp_levels(ctx.profile.get("years_experience"))
                        if lv:
                            url += f"&f_E={quote(lv)}"
                        try:
                            page.goto(url, wait_until="domcontentloaded", timeout=25000)
                            page.wait_for_timeout(2000)
                            soup = BeautifulSoup(page.content(), "html.parser")
                            lis = soup.select("ul.jobs-search__results-list li") or soup.select("div.base-card")
                            for li in lis:
                                a = li.select_one("a.base-card__full-link") or li.select_one("a")
                                if not a or not a.get("href"):
                                    continue
                                href = a.get("href")
                                m = re.search(r"-([0-9]{8,15})(?:\?|$)", href)
                                if not m:
                                    m = re.search(r"/view/([0-9]{8,15})", href)
                                jid = m.group(1) if m else None
                                if not jid or jid in cards:
                                    continue
                                t = li.select_one("h3.base-search-card__title") or li.select_one("h3") or a
                                c = li.select_one("h4.base-search-card__subtitle") or li.select_one("h4")
                                loc_el = li.select_one(".job-search-card__location")
                                tm = li.select_one("time")
                                clean_url = f"https://www.linkedin.com/jobs/view/{jid}"
                                title = t.get_text(" ", strip=True) if t else ""
                                comp = c.get_text(" ", strip=True) if c else ""
                                loc_str = loc_el.get_text(" ", strip=True) if loc_el else (loc or "")
                                cards[jid] = {
                                    "source": self.key, "source_id": jid, "url": clean_url, "apply_url": clean_url,
                                    "title": title, "company": comp, "company_logo": None,
                                    "location": loc_str,
                                    "remote": remote or bool(re.search(r"remote", loc_str or "", re.I)),
                                    "posted_at": tm.get("datetime") if tm else None,
                                    "query": q,
                                    "detail_fetched": 0,
                                }
                        except Exception as e:
                            ctx.log(f"LinkedIn browser query warning for '{q}': {str(e)[:60]}")
                finally:
                    browser.close()
        except Exception as e:
            ctx.log(f"LinkedIn browser search error: {str(e)[:80]}")

    def run(self, ctx):
        pages = int(ctx.profile.get("linkedin_pages") or 3)
        max_details = int(ctx.profile.get("linkedin_details") or 150)
        plan = []
        for q in ctx.queries:
            for loc in ctx.locations:
                plan.append((q, loc, False))
        if ctx.profile.get("remote_ok", True):
            country = ctx.profile.get("country") or "India"
            for q in ctx.queries[:3]:
                if (q, country, False) not in plan:
                    plan.append((q, country, True))

        total_steps = len(plan) * pages + max_details
        done = 0
        cards = {}
        use_browser_direct = bool(os.environ.get("DOCKER_CONTAINER"))

        if use_browser_direct:
            ctx.log("LinkedIn: Using browser search for cloud container environment")
            self._search_browser(ctx, plan, cards)
            done = len(plan) * pages
            ctx.progress(done, total_steps)
        else:
            throttled = False
            for q, loc, remote in plan:
                if ctx.stopped:
                    return
                for p in range(pages):
                    try:
                        batch = self._search(ctx, q, loc, p * 25, remote)
                    except Blocked as e:
                        ctx.log(f"LinkedIn guest API throttled ({e}); switching to browser search...")
                        throttled = True
                        break
                    done += 1
                    ctx.progress(done, total_steps)
                    for j in batch:
                        cards.setdefault(j["source_id"], j)
                    if len(batch) < 10:
                        done += pages - p - 1
                        break
                if throttled:
                    self._search_browser(ctx, plan, cards)
                    done = len(plan) * pages
                    ctx.progress(done, total_steps)
                    break

        ctx.log(f"LinkedIn: {len(cards)} unique postings from {len(plan)} searches")

        ranked = sorted(cards.values(), key=lambda j: ctx.prioritize(j["title"], ""), reverse=True)
        to_detail = [j for j in ranked if ctx.prioritize(j["title"], "") > 0][:max_details]
        total_steps = done + len(to_detail)
        rest = [j for j in ranked if j not in to_detail]
        for j in rest:
            ctx.emit(j)

        blocked = {"hit": 0}

        def work(job):
            if ctx.stopped or blocked["hit"] >= 3:
                return job
            try:
                job.update(self.fetch_detail(job["source_id"]))
            except Blocked:
                blocked["hit"] += 1
            except Exception:
                pass
            return job

        with ThreadPoolExecutor(max_workers=3) as ex:
            for job in ex.map(work, to_detail):
                done += 1
                ctx.progress(done, total_steps)
                ctx.emit(job)
        if blocked["hit"] >= 3:
            ctx.log("LinkedIn rate limited detailed descriptions. Basic job info emitted; details load on demand.")

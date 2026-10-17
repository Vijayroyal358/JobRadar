"""Apply queue: one browser thread that opens each job, fills the form and waits for you to submit.

The browser is your installed Chrome or Edge with its own persistent profile under data/apply/browser,
so logins to LinkedIn, Naukri and company portals survive between runs. Everything that touches the
browser happens on the worker thread; the API talks to it through STATE and a command queue.
"""
import os
import queue
import threading
import time
import traceback

from .. import db
from ..textutil import iso, now_utc
from . import adapters, answers, forms

APPLY_DIR = db.DATA_DIR / "apply"
BROWSER_DIR = APPLY_DIR / "browser"
SHOTS_DIR = APPLY_DIR / "screenshots"
for _d in (APPLY_DIR, BROWSER_DIR, SHOTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)
UPLOADS = db.DATA_DIR / "uploads"

DEFAULT_APPLY_PROFILE = {
    "first_name": "", "last_name": "", "email": "", "phone": "", "phone_code": "+91",
    "city": "", "state": "", "country": "India", "postal_code": "", "address": "",
    "linkedin_url": "", "github_url": "", "portfolio_url": "",
    "current_company": "", "current_title": "", "years_experience": "",
    "work_authorized": "yes", "needs_sponsorship": "no", "willing_to_relocate": "yes", "remote_ok": "yes",
    "notice_period": "30 days", "current_salary": "", "expected_salary": "", "salary_currency": "INR",
    "cover_letter": "", "how_heard": "Job board",
    "eeo_gender": "", "eeo_race": "", "eeo_veteran": "", "eeo_disability": "", "pronouns": "",
    "resume_choice": "tailored", "use_ai_answers": True, "auto_continue": True,
}

_lock = threading.Lock()
_cmds = queue.Queue()
_thread = None
STATE = {"running": False, "login_mode": False, "current": None, "log": [], "browser": "closed"}
MAX_STEPS = 14
WAIT_TIMEOUT = 45 * 60


class NeedsUser(Exception):
    """Pause: the user has to do something in the browser (log in, solve a captcha, click submit)."""


class Done(Exception):
    """The application is already complete (e.g. the portal shows 'Applied')."""


class Skip(Exception):
    pass


class Stop(Exception):
    pass


# ---------------------------------------------------------------- profile
def get_apply_profile(user_id="default"):
    user_id = str(user_id or "default").strip() or "default"
    p = dict(DEFAULT_APPLY_PROFILE)
    saved = db.get_setting(f"apply.profile.{user_id}")
    if saved is None and user_id == "default":
        saved = db.get_setting("apply.profile", {})
    p.update(saved or {})
    up = db.get_profile(user_id=user_id)
    if not p.get("first_name") and up.get("name"):
        parts = up["name"].split()
        p["first_name"], p["last_name"] = parts[0], " ".join(parts[1:])
    if not p.get("current_title") and up.get("current_title"):
        p["current_title"] = up["current_title"]
    if p.get("years_experience") in ("", None) and up.get("years_experience") is not None:
        p["years_experience"] = up["years_experience"]
    if not p.get("city") and up.get("search_locations"):
        loc = up["search_locations"][0]
        if loc.lower() not in ("india", "remote", "worldwide", (up.get("country") or "").lower()):
            p["city"] = loc
    if not p.get("country") and up.get("country"):
        p["country"] = up["country"]
    return p


def save_apply_profile(data, user_id="default"):
    user_id = str(user_id or "default").strip() or "default"
    cur = db.get_setting(f"apply.profile.{user_id}", {}) or {}
    for k in DEFAULT_APPLY_PROFILE:
        if k in data:
            v = data[k]
            cur[k] = v if isinstance(v, bool) else ("" if v is None else str(v).strip())
    db.set_setting(f"apply.profile.{user_id}", cur)
    if user_id == "default":
        db.set_setting("apply.profile", cur)
    return get_apply_profile(user_id)


def profile_ready(p=None):
    p = p or get_apply_profile()
    missing = [k for k in ("first_name", "email", "phone") if not p.get(k)]
    return not missing, missing


def resume_for(job_id, choice):
    up = db.get_profile()
    original = UPLOADS / up["resume_filename"] if up.get("resume_filename") else None
    if choice == "tailored":
        for t in db.tailored_for_job(job_id):
            for variant in ("ats", ""):
                p = db.tailored_path(t["id"], variant)
                if p and os.path.exists(p):
                    return p, ("ATS-safe tailored" if variant else "tailored")
    if original and original.exists():
        return str(original), "original"
    return None, None


# ---------------------------------------------------------------- state helpers
def _log(msg):
    with _lock:
        STATE["log"].append({"t": iso(now_utc()), "msg": str(msg)[:300]})
        STATE["log"] = STATE["log"][-120:]


def _set(**kw):
    with _lock:
        if STATE["current"] is None:
            STATE["current"] = {}
        STATE["current"].update(kw)
        if "status" in kw and STATE["current"].get("id"):
            fields = {"status": kw["status"]}
            if "message" in kw:
                fields["message"] = kw["message"]
            db.update_application(STATE["current"]["id"], **fields)


def status():
    with _lock:
        cur = dict(STATE["current"]) if STATE["current"] else None
        out = {"running": STATE["running"], "login_mode": STATE["login_mode"], "browser": STATE["browser"],
               "current": cur, "log": list(STATE["log"][-40:])}
    out["queue"] = db.applications()
    return out


def command(action, payload=None):
    _cmds.put((action, payload or {}))


# ---------------------------------------------------------------- queue control
def start(job_ids):
    ok, missing = profile_ready()
    if not ok:
        raise ValueError("Fill in your application profile first (" + ", ".join(missing) + ").")
    up = db.get_profile()
    if not up.get("resume_filename"):
        raise ValueError("Upload your resume first.")
    already = db.queued_job_ids()
    added = 0
    for jid in job_ids:
        if jid in already or not db.q("SELECT id FROM jobs WHERE id = ?", (jid,), one=True):
            continue
        db.add_application(int(jid))
        added += 1
    _ensure_thread()
    return added


def open_login(site):
    """Open the browser on a portal's login page so the saved profile holds the session."""
    urls = {"linkedin": "https://www.linkedin.com/login", "naukri": "https://www.naukri.com/nlogin/login",
            "indeed": "https://secure.indeed.com/account/login"}
    url = urls.get(site, site if str(site).startswith("http") else "https://www.linkedin.com/login")
    with _lock:
        STATE["login_mode"] = True
    _ensure_thread()
    command("open", {"url": url})


def stop():
    db.cancel_queued()
    with _lock:
        STATE["login_mode"] = False
    command("stop")


def _ensure_thread():
    global _thread
    with _lock:
        if _thread and _thread.is_alive():
            return
        STATE["running"] = True
        _thread = threading.Thread(target=_worker, name="apply-worker", daemon=True)
        _thread.start()


# ---------------------------------------------------------------- browser
def _launch(p):
    args = ["--disable-blink-features=AutomationControlled", "--no-first-run", "--no-default-browser-check",
            "--start-maximized"]
    headless = os.environ.get("JOBRADAR_APPLY_HEADLESS") == "1"
    last = None
    for channel in ("chrome", "msedge", None):
        try:
            kw = {"headless": headless, "args": args, "viewport": None if not headless else {"width": 1280, "height": 900},
                  "ignore_default_args": ["--enable-automation"], "accept_downloads": True}
            if channel:
                kw["channel"] = channel
            return p.chromium.launch_persistent_context(str(BROWSER_DIR), **kw)
        except Exception as e:
            last = e
    raise RuntimeError(f"Could not start Chrome or Edge: {str(last)[:200]}")


def _worker():
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as p:
            try:
                ctx = _launch(p)
            except Exception as e:
                _log(str(e))
                with _lock:
                    STATE["browser"] = "error"
                app = db.next_queued_application()
                while app:
                    db.update_application(app["id"], status="failed", message=str(e)[:300], finished_at=iso(now_utc()))
                    app = db.next_queued_application()
                return
            with _lock:
                STATE["browser"] = "open"
            runner = _Runner(ctx)
            try:
                runner.loop()
            finally:
                try:
                    ctx.close()
                except Exception:
                    pass
    except Exception as e:
        _log(f"Apply worker crashed: {e}")
        traceback.print_exc()
    finally:
        with _lock:
            STATE["running"] = False
            STATE["login_mode"] = False
            STATE["browser"] = "closed"
            STATE["current"] = None


class _Runner:
    NeedsUser, Done, Skip, Stop = NeedsUser, Done, Skip, Stop

    def __init__(self, ctx):
        self.ctx = ctx
        self.page = None
        self.stop_flag = False

    def log(self, msg):
        _log(msg)

    # ------------------------------------------------------------ main loop
    def loop(self):
        try:
            self._loop()
        except Stop:
            pass

    def _loop(self):
        idle_since = None
        while not self.stop_flag:
            self._drain_commands(block=False)
            if self.stop_flag:
                break
            app = db.next_queued_application()
            if app:
                idle_since = None
                self.process(app)
                continue
            with _lock:
                login_mode = STATE["login_mode"]
            if login_mode:
                # Keep the browser open while the user logs in; close when they say so or close the window.
                if not self.ctx.pages:
                    with _lock:
                        STATE["login_mode"] = False
                    break
                self._drain_commands(block=True, timeout=1.0)
                continue
            idle_since = idle_since or time.time()
            if time.time() - idle_since > 3:
                break
            self._drain_commands(block=True, timeout=0.5)

    def _drain_commands(self, block=False, timeout=0.5):
        try:
            while True:
                action, payload = _cmds.get(block=block, timeout=timeout) if block else _cmds.get_nowait()
                block = False
                self._handle_global(action, payload)
        except queue.Empty:
            pass

    def _handle_global(self, action, payload):
        if action == "stop":
            self.stop_flag = True
            raise Stop()
        if action == "open":
            pg = self.ctx.new_page()
            try:
                pg.goto(payload["url"], wait_until="domcontentloaded", timeout=45000)
                pg.bring_to_front()
            except Exception as e:
                self.log(f"Could not open {payload['url']}: {str(e)[:80]}")
        elif action == "close_login":
            with _lock:
                STATE["login_mode"] = False

    # ------------------------------------------------------------ one application
    def process(self, app):
        job = db.get_job(app["job_id"])
        prof = get_apply_profile()
        with _lock:
            STATE["current"] = {"id": app["id"], "job_id": app["job_id"], "title": job["title"] if job else "", "company": job["company"] if job else "",
                                "status": "running", "message": "Opening the application page", "questions": [], "filled": [],
                                "portal": "", "url": "", "instruction": "", "started_at": iso(now_utc())}
        db.update_application(app["id"], status="running", started_at=iso(now_utc()), message="Opening the application page")
        if not job:
            self._finish(app, "failed", "Job no longer exists")
            return
        resume_path, resume_kind = resume_for(job["id"], prof.get("resume_choice") or "tailored")
        prof["_resume_path"] = resume_path
        if prof.get("cover_letter"):
            prof["cover_letter"] = (prof["cover_letter"].replace("{company}", job.get("company") or "your company")
                                    .replace("{title}", job.get("title") or "this role"))
        url = job.get("apply_url") or job.get("url")
        if not url:
            self._finish(app, "failed", "This job has no application link")
            return
        page = None
        try:
            page = self._open(url)
            self.page = page
            adapter = adapters.detect(page.url, page, self)
            _set(portal=adapter.label, url=page.url, message=f"Detected {adapter.label}")
            db.update_application(app["id"], portal=adapter.key, url=page.url, resume_path=resume_path)
            self._ensure_logged_in(page, adapter)
            page = adapter.prepare(page)
            self.page = page
            if adapter.key == "generic":
                adapter2 = adapters.detect(page.url, page, self)
                if adapter2.key != "generic":
                    adapter = adapter2
                    page = adapter.prepare(page)
                    self.page = page
                    _set(portal=adapter.label, url=page.url)
            if adapter.key == "naukri":
                self._naukri_flow(page, adapter, app, job, prof)
            else:
                self._form_flow(page, adapter, app, job, prof, resume_kind)
        except Done as e:
            self._finish(app, "submitted", str(e), job)
        except Skip as e:
            self._finish(app, "skipped", str(e) or "Skipped by you")
        except Stop:
            self._finish(app, "skipped", "Stopped")
            self.stop_flag = True
        except NeedsUser as e:
            # Timed out waiting for the user.
            self._finish(app, "failed", str(e))
        except Exception as e:
            shot = self._screenshot(app["id"])
            self.log(f"{job.get('title')}: {type(e).__name__}: {str(e)[:200]}")
            db.update_application(app["id"], screenshot=shot)
            self._finish(app, "failed", f"{type(e).__name__}: {str(e)[:220]}")
        finally:
            try:
                for pg in list(self.ctx.pages)[1:]:
                    pg.close()
            except Exception:
                pass

    def _open(self, url):
        pages = self.ctx.pages
        page = pages[0] if pages else self.ctx.new_page()
        for extra in pages[1:]:
            try:
                extra.close()
            except Exception:
                pass
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(1500)
        try:
            page.bring_to_front()
        except Exception:
            pass
        return page

    def click_maybe_new_tab(self, page, locator):
        """Click something that may open a new tab; return the page that now holds the application."""
        try:
            with self.ctx.expect_page(timeout=4000) as info:
                locator.click()
            new = info.value
            new.wait_for_load_state("domcontentloaded", timeout=30000)
            new.bring_to_front()
            return new
        except Exception:
            page.wait_for_timeout(1500)
            return page

    def _ensure_logged_in(self, page, adapter):
        if not adapter.needs_login(page):
            return
        self._wait_user(f"Log in to {adapter.label.split()[0]} in the browser window. I continue automatically once you are in.",
                        until=lambda: not adapter.needs_login(page), status="needs_you")
        page.wait_for_timeout(1500)

    # ------------------------------------------------------------ flows
    def _form_flow(self, page, adapter, app, job, prof, resume_kind):
        asked = []
        all_filled = []
        for step in range(MAX_STEPS):
            _set(message=f"Filling the form" + (f" (step {step + 1})" if step else ""))
            page.wait_for_timeout(600)
            filled, questions = forms.fill(page, prof, adapter.scope, log=self.log, skip_ids={a["id"] for a in asked})
            all_filled += filled
            if filled:
                self.log(f"Filled {len(filled)} field(s): " + ", ".join(f['label'][:30] for f in filled[:6]))
            qs = [forms.describe(q) for q in questions if q["id"] not in {a["id"] for a in asked}]
            if qs:
                resolved = self._answer_questions(page, qs, prof, job)
                asked += resolved
            _set(questions=asked, filled=[f["label"] for f in all_filled], url=page.url)
            nxt = adapter.next_button(page)
            if nxt is None or not prof.get("auto_continue", True):
                break
            blocking = [a for a in asked if not a.get("answer") and a.get("required")]
            if blocking:
                self._wait_user("Some required questions have no answer. Fill them in the browser, then click Continue here.",
                                until=None, status="needs_you")
            try:
                nxt.click()
            except Exception as e:
                self.log(f"Could not press Next: {str(e)[:80]}")
                break
            page.wait_for_timeout(1200)
            if adapter.is_submitted(page):
                raise Done("Submitted")
        note = f"Resume attached: {resume_kind}." if resume_kind and any(f["key"] == "resume" for f in all_filled) else \
            ("No resume field was found; attach it manually if the form asks for one." if resume_kind else "")
        instruction = adapter.instruction + (" " + note if note else "")
        try:
            _set(instruction=instruction, url=page.url, page_title=page.title())
        except Exception:
            _set(instruction=instruction)
        self._wait_user(instruction, until=lambda: adapter.is_submitted(page), status="needs_you")
        raise Done("Submitted")

    def _naukri_flow(self, page, adapter, app, job, prof):
        _set(instruction=adapter.instruction, message="Waiting for you to click Apply")
        deadline = time.time() + WAIT_TIMEOUT
        asked = []
        answered_norms = set()
        while time.time() < deadline:
            self._poll_commands(page, asked, prof, timeout=1.0)
            if adapter.is_submitted(page):
                raise Done("Applied on Naukri")
            drawer = page.locator(".chatbot_Drawer, .chatbot_DrawerContentWrapper").first
            if drawer.count() and drawer.is_visible():
                q = self._naukri_question(page)
                if q and db.norm_question(q["label"]) not in answered_norms:
                    _set(status="running", message=f"Answering: {q['label'][:80]}")
                    res = self._answer_questions(page, [q], prof, job, fill_now=False)
                    asked += res
                    a = res[0]
                    if a.get("answer"):
                        self._naukri_send(page, q, a["answer"])
                        answered_norms.add(db.norm_question(q["label"]))
                    else:
                        self._wait_user(f"Naukri asks: {q['label']}. Answer it in the browser, then click Continue here.", until=None, status="needs_you")
                        answered_norms.add(db.norm_question(q["label"]))
                    _set(questions=asked, status="needs_you", message="Check the chat and finish the application")
                    continue
            _set(status="needs_you")
        raise NeedsUser("Timed out waiting for you to finish on Naukri.")

    def _naukri_question(self, page):
        bot = page.locator(".botMsg, .chatbot_MessageContainer .botMsg, [class*='botMsg']")
        if not bot.count():
            return None
        text = (bot.last.inner_text() or "").strip()
        if not text:
            return None
        options = []
        radios = page.locator(".chatbot_Drawer input[type=radio], .ssrc__radio-btn-container label, .chatbot_Drawer .chatbot_ListItem")
        for i in range(min(radios.count(), 20)):
            try:
                t = (radios.nth(i).inner_text() or radios.nth(i).get_attribute("value") or "").strip()
                if t:
                    options.append(t)
            except Exception:
                pass
        return {"id": f"naukri_{len(text)}", "label": text[:200], "kind": "choice" if options else "text", "required": True, "options": options}

    def _naukri_send(self, page, q, answer):
        if q["options"]:
            opt = page.locator(".chatbot_Drawer label, .chatbot_Drawer .chatbot_ListItem, .ssrc__radio-btn-container label").filter(has_text=answer).first
            if opt.count():
                opt.click()
        else:
            box = page.locator(".chatbot_Drawer [contenteditable=true], .chatbot_Drawer textarea, .chatbot_Drawer input[type=text]").first
            if box.count():
                box.click()
                page.keyboard.type(str(answer))
        send = page.locator(".chatbot_Drawer .sendMsg, .chatbot_Drawer button:has-text('Send'), .chatbot_Drawer button:has-text('Save')").first
        if send.count():
            send.click()
        page.wait_for_timeout(1500)

    # ------------------------------------------------------------ questions
    def _answer_questions(self, page, qs, prof, job, fill_now=True):
        _set(message=f"Working out {len(qs)} question(s)")
        up = db.get_profile()
        resolved = answers.resolve(qs, prof, up, job, use_ai=bool(prof.get("use_ai_answers", True)), log=self.log)
        if fill_now:
            fields = {f["id"]: f for f in forms.discover(page, None)}
            for a in resolved:
                f = fields.get(a["id"])
                if f and a.get("answer"):
                    a["filled"] = forms.apply_answer(page, f, a["answer"], self.log)
        return resolved

    def _apply_user_answer(self, page, asked, payload):
        fid, ans, remember = payload.get("id"), payload.get("answer", ""), payload.get("remember")
        for a in asked:
            if a["id"] == fid:
                a["answer"] = ans
                a["source"] = "user"
                a["uncertain"] = False
                if remember and ans:
                    db.save_answer(a["label"], ans, "user")
                if not fid.startswith("naukri_"):
                    fields = {f["id"]: f for f in forms.discover(page, None)}
                    if fid in fields:
                        a["filled"] = forms.apply_answer(page, fields[fid], ans, self.log)
                elif ans:
                    self._naukri_send(page, {"options": a.get("options") or []}, ans)
        try:
            _set(questions=asked, page_title=page.title())
        except Exception:
            _set(questions=asked)

    # ------------------------------------------------------------ waiting on the user
    def _poll_commands(self, page, asked, prof, timeout=1.0):
        try:
            action, payload = _cmds.get(timeout=timeout)
        except queue.Empty:
            return None
        if action == "answer":
            self._apply_user_answer(page, asked, payload)
            return None
        if action == "skip":
            raise Skip(payload.get("reason") or "Skipped by you")
        if action == "submitted":
            raise Done("Marked as submitted by you")
        if action == "continue":
            return "continue"
        self._handle_global(action, payload)
        return None

    def _wait_user(self, message, until=None, status="needs_you"):
        _set(status=status, message=message)
        try:
            self.page.bring_to_front()
        except Exception:
            pass
        deadline = time.time() + WAIT_TIMEOUT
        cur = STATE["current"] or {}
        asked = cur.get("questions") or []
        while time.time() < deadline:
            r = self._poll_commands(self.page, asked, None, timeout=1.0)
            if r == "continue":
                return
            if until is not None:
                try:
                    if until():
                        return
                except Exception:
                    pass
            if self.page.is_closed():
                raise Skip("The browser tab was closed")
        raise NeedsUser("Timed out waiting for you in the browser.")

    # ------------------------------------------------------------ finishing
    def _screenshot(self, app_id):
        try:
            path = SHOTS_DIR / f"{app_id}.png"
            self.page.screenshot(path=str(path), full_page=False)
            return path.name
        except Exception:
            return None

    def _finish(self, app, status, message, job=None):
        cur = STATE["current"] or {}
        db.update_application(app["id"], status=status, message=message, finished_at=iso(now_utc()),
                              answers=cur.get("questions") or [])
        if status == "submitted":
            db.execute("UPDATE jobs SET status = 'applied', status_at = ? WHERE id = ?", (iso(now_utc()), app["job_id"]))
            for a in cur.get("questions") or []:
                if a.get("answer") and a.get("source") in ("ai", "user") and not a.get("uncertain"):
                    db.save_answer(a["label"], a["answer"], a["source"])
        self.log(f"{cur.get('title') or 'Job'} at {cur.get('company') or ''}: {status} - {message}")
        with _lock:
            STATE["current"] = None

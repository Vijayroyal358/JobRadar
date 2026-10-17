"""Common scraper interface."""
import random
import threading
import time

import requests

import sys

if sys.platform.startswith("linux"):
    UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
else:
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"

STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
if (!window.chrome) { window.chrome = {}; }
window.chrome.runtime = {};
Object.defineProperty(navigator, 'languages', { get: () => ['en-IN', 'en-US', 'en'] });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
"""


def launch_browser(p, headless=True):
    args = [
        "--disable-blink-features=AutomationControlled",
        "--no-first-run",
        "--no-default-browser-check",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
    ]
    # headless=False forces Playwright to use the full Chrome/Chromium binary instead of
    # chromium-headless-shell. The headless shell is easily fingerprinted by sites like Naukri.
    # We then pass --headless=new so Chrome runs without any display (works in Docker/Railway).
    if headless:
        args.append("--headless=new")

    last = None
    for channel in ("chrome", "msedge", None):
        try:
            kw = {"headless": False, "args": args}
            if channel:
                kw["channel"] = channel
            return p.chromium.launch(**kw)
        except Exception as e:
            last = e
    raise RuntimeError(f"Could not start Chromium browser: {last}")


class Blocked(Exception):
    """The site refused us (captcha, 403, persistent 429)."""


class RunContext:
    """Passed to every scraper: what to search for and callbacks to report results."""

    def __init__(self, profile, queries, emit, log, progress, stop_event, prioritize):
        self.profile = profile
        self.queries = queries            # list of keyword strings (roles)
        self.emit = emit                  # emit(job_dict) -> bool (True if stored as relevant)
        self.log = log                    # log(message)
        self.progress = progress          # progress(done, total)
        self.stop_event = stop_event
        self.prioritize = prioritize      # prioritize(title, text) -> float 0..1 quick relevance

    @property
    def stopped(self):
        return self.stop_event.is_set()

    @property
    def days(self):
        return int(self.profile.get("posted_within_days") or 14)

    @property
    def locations(self):
        locs = [l for l in self.profile.get("search_locations") or [] if l.strip()]
        return locs or [self.profile.get("country") or "India"]


class Scraper:
    key = ""
    label = ""
    region = ""          # shown in UI
    description = ""
    needs_browser = False

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
        self._last = 0.0
        self._lock = threading.Lock()

    def throttle(self, lo=0.6, hi=1.4):
        with self._lock:
            wait = self._last + random.uniform(lo, hi) - time.time()
            if wait > 0:
                time.sleep(wait)
            self._last = time.time()

    def get(self, url, *, params=None, headers=None, timeout=25, retries=3, throttle=(0.3, 0.8), as_json=False):
        last_exc = None
        for attempt in range(retries):
            self.throttle(*throttle)
            try:
                r = self.session.get(url, params=params, headers=headers, timeout=timeout)
            except requests.RequestException as e:
                last_exc = e
                time.sleep(2 * (attempt + 1))
                continue
            if r.status_code == 429:
                time.sleep(8 * (attempt + 1))
                last_exc = Blocked("Rate limited (429)")
                continue
            if r.status_code in (403, 406, 999):
                raise Blocked(f"HTTP {r.status_code}")
            if r.status_code >= 500:
                last_exc = Exception(f"HTTP {r.status_code}")
                time.sleep(2 * (attempt + 1))
                continue
            r.raise_for_status()
            return r.json() if as_json else r
        raise last_exc or Exception("request failed")

    def run(self, ctx: RunContext):
        raise NotImplementedError

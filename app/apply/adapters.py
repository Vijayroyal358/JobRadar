"""Portal adapters: how to reach the application form, which part of the page holds it, how to step through
multi-page forms, and how to tell that the application went through. The generic adapter covers everything else.
"""
import re
from urllib.parse import urlparse

SUBMITTED_TEXT = re.compile(
    r"application (has been |was )?(submitted|sent|received|complete)|thank you for (applying|your application|your interest)|"
    r"you('ve| have) (successfully )?applied|successfully applied|we('ve| have) received your application|"
    r"your application (is|has been) (in|received|under review)|application sent", re.I)
LOGIN_URL = re.compile(r"/login|/signin|/sign-in|/authwall|/checkpoint|/uas/login|nlogin|accounts\.google", re.I)


class Adapter:
    key = "generic"
    label = "Company site"
    scope = None                    # CSS selector that contains the form, or None for the whole page
    instruction = "Review the filled form in the browser, complete anything marked, then click Submit."
    manual_submit_note = ""

    def __init__(self, runner):
        self.r = runner

    @staticmethod
    def match(url, page):
        return True

    def needs_login(self, page):
        return bool(LOGIN_URL.search(page.url))

    def prepare(self, page):
        """Get to the form. May return a different page (new tab)."""
        if page.locator("form input:visible, form textarea:visible, form select:visible").count() >= 3:
            return page
        btn = page.get_by_role("link", name=re.compile(r"^(apply|apply now|apply for this (job|position)|i'm interested|start application)", re.I)).first
        if not btn.count():
            btn = page.get_by_role("button", name=re.compile(r"^(apply|apply now|apply for this (job|position)|i'm interested|start application)", re.I)).first
        if btn.count():
            return self.r.click_maybe_new_tab(page, btn)
        return page

    def next_button(self, page):
        """Locator for a non-final 'next step' button inside the form, or None."""
        b = page.get_by_role("button", name=re.compile(r"^(next|continue|save and continue|next step|review)\b", re.I)).first
        return b if b.count() and b.is_visible() else None

    def submit_button(self, page):
        b = page.get_by_role("button", name=re.compile(r"submit|send application|apply now|apply$", re.I)).first
        return b if b.count() else None

    def is_submitted(self, page):
        try:
            if SUBMITTED_TEXT.search(page.locator("body").inner_text(timeout=2000)[:20000]):
                return True
        except Exception:
            pass
        return bool(re.search(r"thank|confirmation|submitted|success", page.url, re.I))


class Greenhouse(Adapter):
    key = "greenhouse"
    label = "Greenhouse"
    scope = "#application_form, #application-form, form[action*='greenhouse'], #main_fields, form"

    @staticmethod
    def match(url, page):
        return "greenhouse.io" in url or page.locator("#application_form, #application-form, [data-provides='greenhouse']").count() > 0

    def prepare(self, page):
        if page.locator("#application_form, #application-form").count():
            if page.locator("#application_form input, #application-form input").first.is_visible():
                return page
        tab = page.get_by_role("link", name=re.compile(r"^apply", re.I)).first
        if tab.count():
            page = self.r.click_maybe_new_tab(page, tab)
        elif page.locator("#apply_button, a[href*='#app'], button:has-text('Apply')").count():
            page.locator("#apply_button, a[href*='#app'], button:has-text('Apply')").first.click()
        page.wait_for_timeout(1200)
        return page


class Lever(Adapter):
    key = "lever"
    label = "Lever"
    scope = "form#application-form, form.application-form, .application-form, form"

    @staticmethod
    def match(url, page):
        return "lever.co" in url

    def prepare(self, page):
        if "/apply" not in page.url:
            link = page.locator("a.postings-btn, a[href$='/apply'], a:has-text('Apply for this job')").first
            if link.count():
                page = self.r.click_maybe_new_tab(page, link)
                page.wait_for_load_state("domcontentloaded")
        return page


class Ashby(Adapter):
    key = "ashby"
    label = "Ashby"
    scope = "form, [class*='ashby-application-form'], main"

    @staticmethod
    def match(url, page):
        return "ashbyhq.com" in url

    def prepare(self, page):
        if "/application" not in page.url:
            link = page.locator("a[href$='/application'], a:has-text('Apply for this Job'), button:has-text('Apply')").first
            if link.count():
                page = self.r.click_maybe_new_tab(page, link)
                page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(800)
        return page


class SmartRecruiters(Adapter):
    key = "smartrecruiters"
    label = "SmartRecruiters"
    scope = "form, [class*='application'], main"

    @staticmethod
    def match(url, page):
        return "smartrecruiters.com" in url

    def prepare(self, page):
        btn = page.locator("a[href*='/apply'], a:has-text(\"I'm interested\"), button:has-text(\"I'm interested\"), a:has-text('Apply')").first
        if btn.count() and not page.locator("form input[type=email]").count():
            page = self.r.click_maybe_new_tab(page, btn)
            page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(800)
        return page


class Workday(Adapter):
    key = "workday"
    label = "Workday"
    scope = "form, main"
    instruction = "Workday needs an account on this company's portal. Sign in or create one in the browser; I fill each step after that."

    @staticmethod
    def match(url, page):
        return "myworkdayjobs.com" in url or "workday" in url

    def needs_login(self, page):
        return bool(LOGIN_URL.search(page.url)) or page.locator("[data-automation-id='signInContent'], [data-automation-id='createAccountContent']").count() > 0

    def prepare(self, page):
        btn = page.locator("a[data-automation-id='adventureButton'], a:has-text('Apply'), button:has-text('Apply')").first
        if btn.count():
            page = self.r.click_maybe_new_tab(page, btn)
            page.wait_for_timeout(1500)
            man = page.locator("a[data-automation-id='applyManually'], a:has-text('Apply Manually')").first
            if man.count():
                man.click()
        return page

    def next_button(self, page):
        b = page.locator("button[data-automation-id='bottom-navigation-next-button'], button:has-text('Save and Continue'), button:has-text('Next')").first
        return b if b.count() and b.is_visible() else None


class LinkedIn(Adapter):
    key = "linkedin"
    label = "LinkedIn Easy Apply"
    scope = ".jobs-easy-apply-modal, .jobs-easy-apply-content, [data-test-modal], div[role=dialog]"
    instruction = "The Easy Apply form is filled up to the last step. Check it in the browser and click 'Submit application'."

    @staticmethod
    def match(url, page):
        return "linkedin.com" in url

    def needs_login(self, page):
        if LOGIN_URL.search(page.url):
            return True
        return page.locator("a[href*='/login'], .nav__button-secondary:has-text('Sign in'), form.login__form").count() > 0 and \
            not page.locator(".global-nav__me, #global-nav").count()

    def prepare(self, page):
        page.wait_for_timeout(1500)
        modal = page.locator(self.scope).first
        if modal.count() and modal.is_visible():
            return page
        btn = page.locator(".jobs-apply-button, button.jobs-apply-button--top-card, button:has-text('Easy Apply')").first
        if not btn.count():
            btn = page.get_by_role("button", name=re.compile(r"easy apply", re.I)).first
        if not btn.count():
            if page.locator("span:has-text('Applied'), .artdeco-inline-feedback--success").count():
                raise self.r.Done("LinkedIn shows you already applied to this job.")
            ext = page.get_by_role("button", name=re.compile(r"^apply\b", re.I)).first
            if ext.count():
                self.r.log("This job uses an external application site. Following it.")
                return self.r.click_maybe_new_tab(page, ext)
            raise self.r.NeedsUser("Could not find the Easy Apply button. Open the application in the browser; I will continue once a form appears.")
        label = (btn.get_attribute("aria-label") or btn.inner_text() or "").lower()
        if "easy apply" not in label:
            self.r.log("This job uses an external application site. Following it.")
            return self.r.click_maybe_new_tab(page, btn)
        btn.click()
        page.wait_for_selector(self.scope, timeout=15000)
        return page

    def next_button(self, page):
        for sel in ("button[aria-label='Continue to next step']", "button[aria-label='Review your application']",
                    "footer button:has-text('Next')", "footer button:has-text('Review')"):
            b = page.locator(sel).first
            if b.count() and b.is_visible():
                return b
        return None

    def submit_button(self, page):
        b = page.locator("button[aria-label='Submit application'], footer button:has-text('Submit application')").first
        return b if b.count() else None

    def is_submitted(self, page):
        try:
            if page.locator("text=/application (was )?sent|your application was sent|applied/i").first.is_visible(timeout=800):
                return True
        except Exception:
            pass
        return not page.locator(self.scope).first.is_visible() and page.locator(".artdeco-inline-feedback--success, span:has-text('Applied')").count() > 0


class Naukri(Adapter):
    key = "naukri"
    label = "Naukri"
    scope = ".chatbot_Drawer, .chatbot_DrawerContentWrapper, body"
    instruction = "Click Apply in the browser. If the recruiter has questions, I answer them from your saved answers and the AI; you confirm each one."

    @staticmethod
    def match(url, page):
        return "naukri.com" in url

    def needs_login(self, page):
        if LOGIN_URL.search(page.url):
            return True
        return page.locator("a#login_Layer, a[title='Jobseeker Login'], .nI-gNb-lg-rg a:has-text('Login')").count() > 0

    def prepare(self, page):
        if page.locator("#already-applied, span:has-text('Applied'), .already-applied").count():
            raise self.r.Done("Naukri shows you already applied to this job.")
        btn = page.locator("#apply-button, button.apply-button, button:has-text('Apply')").first
        if btn.count() and re.search(r"company site", (btn.inner_text() or ""), re.I):
            self.r.log("This job applies on the company site. Following it.")
            return self.r.click_maybe_new_tab(page, btn)
        return page

    def is_submitted(self, page):
        return page.locator("#already-applied, .apply-status-header:has-text('applied'), span:has-text('You have successfully applied')").count() > 0 \
            or bool(re.search(r"successfully applied|already applied", _safe_text(page), re.I))


def _safe_text(page, limit=20000):
    try:
        return page.locator("body").inner_text(timeout=1500)[:limit]
    except Exception:
        return ""


ADAPTERS = [LinkedIn, Naukri, Greenhouse, Lever, Ashby, SmartRecruiters, Workday, Adapter]


def detect(url, page, runner):
    for cls in ADAPTERS:
        try:
            if cls.match(url or "", page):
                return cls(runner)
        except Exception:
            continue
    return Adapter(runner)


def host(url):
    try:
        return urlparse(url).netloc
    except Exception:
        return ""

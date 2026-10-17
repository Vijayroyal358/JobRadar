"""Generic application-form filler.

Discovers every visible field on the page (or inside a scope such as a modal), derives a human label
for it, maps the label to a value from the application profile, and fills it. Fields it cannot map
are returned as questions for the answer bank or the AI.
"""
import re
import time

# label pattern -> profile field. Order matters: more specific first.
RULES = [
    ("first_name", r"first\s*name|given\s*name|\bfname\b|forename"),
    ("last_name", r"last\s*name|surname|family\s*name|\blname\b"),
    ("full_name", r"^(full\s*|legal\s*|your\s*|candidate\s*)?name\b|^name\s*[*:]?$"),
    ("email", r"e-?mail"),
    ("phone", r"phone|mobile|contact\s*(no|number)|telephone|\bcell\b|whatsapp"),
    ("linkedin_url", r"linkedin"),
    ("github_url", r"github|git\s*hub"),
    ("portfolio_url", r"portfolio|personal\s*(web)?site|website|\burl\b|\blink\b"),
    ("postal_code", r"\bzip\b|postal|pin\s*code|postcode"),
    ("city", r"^city|current\s*(city|location)|^location|where\s*are\s*you\s*(based|located)|city\s*of\s*residence"),
    ("state", r"^state\b|province"),
    ("country", r"country|nationality"),
    ("address", r"address"),
    ("years_experience", r"years?\s*of\s*(total\s*|relevant\s*|work\s*|professional\s*)?(experience|exp)|total\s*experience|experience\s*\(?\s*(in\s*)?years|how\s*many\s*years"),
    ("current_company", r"current\s*(company|employer|organi[sz]ation)|most\s*recent\s*(company|employer)|company\s*name|employer\s*name|^company$|^organi[sz]ation$"),
    ("current_title", r"current\s*(title|role|position|designation)|job\s*title|most\s*recent\s*(title|role)|^title$|^designation$"),
    ("notice_period", r"notice\s*period|when\s*can\s*you\s*(start|join)|earliest\s*(start|joining)|available\s*to\s*start|start\s*date|availability|joining\s*time"),
    ("expected_salary", r"(expected|desired|target|preferred)\s*(ctc|salary|compensation|pay|package)|salary\s*expectation|compensation\s*expectation|what\s*salary"),
    ("current_salary", r"current\s*(ctc|salary|compensation|pay|package)|present\s*(ctc|salary)"),
    ("needs_sponsorship", r"sponsorship|sponsor|visa\s*(status|support|requirement)|require\s*.*visa"),
    ("work_authorized", r"authori[sz]ed\s*to\s*work|legally\s*(eligible|entitled|permitted|authori[sz]ed)|right\s*to\s*work|work\s*(permit|authori[sz]ation)|eligible\s*to\s*work|legal\s*right"),
    ("willing_to_relocate", r"relocat"),
    ("remote_ok", r"work\s*remotely|remote\s*work|work\s*from\s*home|comfortable\s*(working\s*)?remote|hybrid"),
    ("cover_letter", r"cover\s*letter|why\s*(do\s*you\s*want|are\s*you\s*interested|should\s*we)|tell\s*us\s*(about|why)|additional\s*(information|comments)|message\s*to\s*(the\s*)?(hiring|recruit)|anything\s*else|^comments?$|motivation"),
    ("eeo_gender", r"\bgender\b|\bsex\b|gender\s*identity"),
    ("eeo_race", r"\brace\b|ethnic|hispanic|latino"),
    ("eeo_veteran", r"veteran|military"),
    ("eeo_disability", r"disabilit|handicap"),
    ("pronouns", r"pronoun"),
    ("how_heard", r"how\s*did\s*you\s*(hear|find|learn)|where\s*did\s*you\s*(hear|find)|source\s*of|referr(al|ed)\s*by|hear\s*about"),
    ("resume", r"resume|\bcv\b|curriculum"),
    ("consent", r"\bconsent\b|privacy\s*(policy|notice)|terms\s*(and|&)\s*conditions|i\s*(agree|acknowledge|accept|certify|confirm)|gdpr|data\s*(processing|protection)"),
]
AUTOCOMPLETE = {"given-name": "first_name", "family-name": "last_name", "name": "full_name", "email": "email",
                "tel": "phone", "tel-national": "phone", "postal-code": "postal_code", "country-name": "country",
                "address-level2": "city", "address-level1": "state", "street-address": "address",
                "organization": "current_company", "organization-title": "current_title", "url": "portfolio_url"}
NAME_HINTS = {"org": "current_company", "comments": "cover_letter", "urls[linkedin]": "linkedin_url",
              "urls[github]": "github_url", "urls[portfolio]": "portfolio_url", "urls[other]": "portfolio_url",
              "urls[twitter]": None, "resume": "resume", "cv": "resume", "cover_letter": "cover_letter",
              "cover-letter": None, "phone": "phone", "email": "email", "name": "full_name", "location": "city"}
YES = re.compile(r"^(yes|y|true|i am|i do|agree)\b", re.I)
NO = re.compile(r"^(no|n|false|i am not|i do not|disagree)\b", re.I)
PREFER_NOT = re.compile(r"decline|prefer\s*not|not\s*(to\s*)?(say|answer|disclose|specify)|rather\s*not|wish\s*not|don't\s*wish|do\s*not\s*wish", re.I)

_RULES = [(k, re.compile(rx, re.I)) for k, rx in RULES]

# Runs inside the page: tags every form control with data-jr-id and returns a description of each one.
DISCOVER_JS = r"""
(scopeSel) => {
  const root = scopeSel ? document.querySelector(scopeSel) : document;
  if (!root) return [];
  const vis = (el) => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
    return cs.visibility !== 'hidden' && cs.display !== 'none' && (r.width > 0 || r.height > 0 || el.type === 'file'); };
  const clean = (s) => (s || '').replace(/\s+/g, ' ').replace(/\s*[*]\s*$/, '').trim();
  const txt = (el) => clean(el ? (el.innerText || el.textContent) : '');
  // Text of a label without the text of any control nested inside it (e.g. a select's options).
  const labelText = (l) => { const c = l.cloneNode(true); c.querySelectorAll('input,select,textarea,button').forEach((x) => x.remove()); return clean(c.textContent); };
  const labelFor = (el) => {
    let t = '';
    if (el.id) { const l = root.querySelector(`label[for="${CSS.escape(el.id)}"]`); if (l) t = labelText(l); }
    if (!t) { const l = el.closest('label'); if (l) t = labelText(l); }
    if (!t && el.getAttribute('aria-labelledby')) {
      t = el.getAttribute('aria-labelledby').split(/\s+/).map((id) => txt(document.getElementById(id))).filter(Boolean).join(' ');
    }
    if (!t) t = clean(el.getAttribute('aria-label'));
    if (!t) { const fs = el.closest('fieldset'); const lg = fs && fs.querySelector('legend'); if (lg) t = txt(lg); }
    if (!t) {
      // Walk up a few levels and take the text of a preceding label-like element.
      let node = el, depth = 0;
      while (node && depth < 4 && !t) {
        let sib = node.previousElementSibling;
        while (sib && !t) { if (!sib.querySelector('input,select,textarea')) t = txt(sib); sib = sib.previousElementSibling; }
        node = node.parentElement; depth++;
      }
    }
    if (!t) t = clean(el.getAttribute('placeholder'));
    if (!t) t = clean(el.name || el.id);
    return t.slice(0, 200);
  };
  const groupLabel = (el) => {
    const fs = el.closest('fieldset'); const lg = fs && fs.querySelector('legend');
    if (lg) return txt(lg);
    const g = el.closest('[role=group],[role=radiogroup]');
    if (g) { const lb = g.getAttribute('aria-labelledby'); if (lb) return clean(document.getElementById(lb)?.innerText); const h = g.querySelector('legend,label,h1,h2,h3,h4,h5,h6,p,span,div'); if (h && !h.querySelector('input')) return txt(h); }
    let node = el.parentElement, depth = 0;
    while (node && depth < 5) {
      // Stop climbing once the container holds controls that belong to other fields.
      if ([...node.querySelectorAll('input,select,textarea')].some((i) => i !== el && i.name !== el.name)) break;
      const cand = [...node.children].find((c) => !c.querySelector('input,select,textarea') && txt(c).length > 2);
      if (cand) return txt(cand);
      node = node.parentElement; depth++;
    }
    return '';
  };
  const sameName = (el) => el.name ? root.querySelectorAll(`input[type="${el.type}"][name="${CSS.escape(el.name)}"]`).length : 1;
  const out = []; let n = 0; const groups = {};
  const els = root.querySelectorAll('input, select, textarea, [role=combobox], [contenteditable=true]');
  for (const el of els) {
    const tag = el.tagName.toLowerCase();
    const type = (el.getAttribute('type') || (tag === 'input' ? 'text' : tag)).toLowerCase();
    if (['hidden', 'submit', 'button', 'reset', 'image', 'search'].includes(type)) continue;
    if (type !== 'file' && !vis(el)) continue;
    if (el.disabled || el.readOnly) continue;
    if (!el.dataset.jrId) el.dataset.jrId = 'f' + (++n) + '_' + Math.random().toString(36).slice(2, 7);
    const id = el.dataset.jrId;
    const req = el.required || el.getAttribute('aria-required') === 'true' || /\*\s*$/.test((el.closest('label') || {}).innerText || '') ||
      !!(el.id && root.querySelector(`label[for="${CSS.escape(el.id)}"]`)?.innerText.includes('*'));
    if (type === 'radio' || type === 'checkbox') {
      const optLabel = labelFor(el) || clean(el.value);
      const multi = sameName(el) > 1;
      const key = type + ':' + (el.name || (multi ? groupLabel(el) : '') || id);
      if (!groups[key]) {
        groups[key] = { id, kind: type === 'radio' ? 'radio' : 'checkbox', label: multi ? (groupLabel(el) || optLabel) : optLabel, name: el.name || '',
          required: req, options: [], checked: [] , autocomplete: '' };
        out.push(groups[key]);
      }
      groups[key].options.push({ id, text: optLabel, value: el.value });
      if (el.checked) groups[key].checked.push(optLabel);
      if (req) groups[key].required = true;
      continue;
    }
    const item = { id, kind: tag === 'select' ? 'select' : type === 'file' ? 'file' : (el.getAttribute('role') === 'combobox' || el.getAttribute('aria-autocomplete') === 'list' || /select__input|autocomplete/i.test(el.className)) ? 'combobox' : tag === 'textarea' || el.isContentEditable ? 'textarea' : type,
      label: labelFor(el), name: el.name || '', placeholder: clean(el.getAttribute('placeholder')), required: req,
      autocomplete: (el.getAttribute('autocomplete') || '').toLowerCase(), value: tag === 'select' ? (el.selectedOptions[0]?.text || '') : (el.value || el.innerText || ''),
      options: tag === 'select' ? [...el.options].filter((o) => o.value !== '' || o.text.trim()).map((o) => ({ text: clean(o.text), value: o.value })) : [], accept: el.getAttribute('accept') || '' };
    if (item.kind === 'select' && item.options.length && /^(select|choose|please|--|pick)/i.test(item.options[0].text)) item.options = item.options.slice(1);
    out.push(item);
  }
  return out;
}
"""


def classify(field):
    """Return the profile field key this form field asks for, or None."""
    ac = field.get("autocomplete") or ""
    if ac in AUTOCOMPLETE:
        return AUTOCOMPLETE[ac]
    name = (field.get("name") or "").lower()
    if name in NAME_HINTS:
        return NAME_HINTS[name]
    if field.get("kind") == "file":
        lab = (field.get("label") or "").lower()
        return None if re.search(r"cover|letter|photo|transcript|portfolio|other", lab) else "resume"
    text = " ".join(filter(None, [field.get("label"), field.get("placeholder"), name])).strip()
    if not text:
        return None
    for key, rx in _RULES:
        if rx.search(text):
            if key == "consent" and field.get("kind") != "checkbox":
                continue
            if key == "cover_letter" and field.get("kind") not in ("textarea", "text"):
                continue
            return key
    return None


def _pick_option(options, wanted):
    """Choose the option whose text best matches `wanted` (a string or list of candidate strings)."""
    if not options:
        return None
    cands = [wanted] if isinstance(wanted, str) else list(wanted or [])
    texts = [(o, (o.get("text") or "").strip()) for o in options]
    for w in cands:
        w = (w or "").strip().lower()
        if not w:
            continue
        for o, t in texts:
            if t.lower() == w:
                return o
        for o, t in texts:
            if w in t.lower() or t.lower() in w and len(t) > 2:
                return o
    return None


def yes_no_option(options, truthy):
    for o in options:
        t = (o.get("text") or "")
        if (YES.search(t) if truthy else NO.search(t)):
            return o
    return None


def prefer_not_option(options):
    for o in options:
        if PREFER_NOT.search(o.get("text") or ""):
            return o
    return None


def value_for(key, prof, field):
    """Return what to put in the field for profile key `key`, or None if we have nothing."""
    kind = field.get("kind")
    opts = field.get("options") or []
    v = prof.get(key)
    if key == "full_name":
        v = v or " ".join(filter(None, [prof.get("first_name"), prof.get("last_name")]))
    if key == "phone" and v and prof.get("phone_code") and kind in ("tel", "text") and not str(v).startswith("+"):
        ph = field.get("placeholder") or ""
        if "+" in ph or "country" in (field.get("label") or "").lower():
            v = f"{prof['phone_code']} {v}"
    if key in ("work_authorized", "needs_sponsorship", "willing_to_relocate", "remote_ok"):
        truthy = str(v).lower() in ("yes", "true", "1")
        if kind in ("select", "radio", "combobox"):
            o = yes_no_option(opts, truthy)
            return o["text"] if o else None
        if kind == "checkbox":
            return "yes" if truthy else None
        return "Yes" if truthy else "No"
    if key == "consent":
        return "yes" if kind == "checkbox" else None
    if key.startswith("eeo_") or key == "pronouns":
        o = _pick_option(opts, v) if v else None
        if not o and opts:
            o = prefer_not_option(opts)
        return o["text"] if o else (v or None)
    if key == "how_heard":
        o = _pick_option(opts, [v or "", "job board", "linkedin", "other", "online"])
        return o["text"] if o else (v or "Job board")
    if key == "years_experience":
        if v in (None, ""):
            return None
        if kind in ("select", "radio", "combobox"):
            o = _pick_option(opts, [str(v), str(int(float(v))), f"{int(float(v))}+", f"{int(float(v))} years"])
            return o["text"] if o else None
        return str(int(float(v))) if float(v).is_integer() else str(v)
    if key == "notice_period" and kind in ("select", "radio", "combobox"):
        o = _pick_option(opts, [v or "", "30", "1 month", "immediate"])
        return o["text"] if o else None
    if key == "cover_letter":
        return v or None
    if key == "resume":
        return prof.get("_resume_path")
    if v in (None, ""):
        return None
    if kind in ("select", "radio", "combobox"):
        o = _pick_option(opts, str(v))
        return o["text"] if o else None
    return str(v)


def discover(page, scope=None):
    try:
        return page.evaluate(DISCOVER_JS, scope)
    except Exception:
        return []


def _loc(page, fid):
    return page.locator(f'[data-jr-id="{fid}"]').first


def set_value(page, field, value, log=None):
    """Fill one field. Returns True when something was entered."""
    kind = field["kind"]
    fid = field["id"]
    try:
        if kind == "file":
            if not value:
                return False
            _loc(page, fid).set_input_files(value)
            return True
        if kind == "select":
            opts = field.get("options") or []
            o = _pick_option(opts, value)
            if not o:
                return False
            _loc(page, fid).select_option(value=o["value"]) if o.get("value") not in (None, "") else _loc(page, fid).select_option(label=o["text"])
            return True
        if kind == "radio":
            o = _pick_option(field.get("options") or [], value)
            if not o:
                return False
            page.locator(f'[data-jr-id="{o["id"]}"]').first.check(force=True)
            return True
        if kind == "checkbox":
            opts = field.get("options") or []
            if len(opts) == 1:
                want = str(value).lower() in ("yes", "true", "1", "on")
                loc = page.locator(f'[data-jr-id="{opts[0]["id"]}"]').first
                if want and not loc.is_checked():
                    loc.check(force=True)
                return want
            wanted = value if isinstance(value, list) else [value]
            hit = False
            for w in wanted:
                o = _pick_option(opts, w)
                if o:
                    page.locator(f'[data-jr-id="{o["id"]}"]').first.check(force=True)
                    hit = True
            return hit
        if kind == "combobox":
            loc = _loc(page, fid)
            loc.click()
            loc.fill("")
            loc.type(str(value)[:80], delay=20)
            page.wait_for_timeout(600)
            opt = page.locator('[role="option"], [class*="option"]:not([class*="options"]), li[id*="option"]').filter(has_text=re.compile(re.escape(str(value)[:40]), re.I)).first
            try:
                opt.click(timeout=2500)
            except Exception:
                page.keyboard.press("Enter")
            return True
        loc = _loc(page, fid)
        if kind == "textarea" and field.get("label") and loc.evaluate("el => el.isContentEditable"):
            loc.click()
            page.keyboard.press("Control+A")
            page.keyboard.type(str(value))
            return True
        loc.fill(str(value))
        return True
    except Exception as e:
        if log:
            log(f"Could not fill '{field.get('label')}': {str(e)[:90]}")
        return False


def fill(page, prof, scope=None, log=None, skip_ids=()):
    """Fill every field we can. Returns (filled, questions) where questions are unmapped or unfilled fields."""
    fields = discover(page, scope)
    filled, questions = [], []
    for f in fields:
        if f["id"] in skip_ids:
            continue
        if f.get("value") and f["kind"] not in ("file", "radio", "checkbox", "select", "combobox"):
            continue  # already has text (prefilled by the site or by us)
        if f["kind"] in ("radio", "checkbox") and f.get("checked") and f["kind"] == "radio":
            continue
        if f["kind"] == "select" and f.get("value") and not re.match(r"^(select|choose|please|--|pick|none)", f["value"], re.I):
            continue
        key = classify(f)
        if key is None:
            if f["kind"] == "checkbox" and len(f.get("options") or []) == 1 and not f.get("required"):
                continue
            questions.append(f)
            continue
        val = value_for(key, prof, f)
        if val is None:
            if key in ("resume", "consent") or f.get("required") or f["kind"] in ("textarea", "radio", "select"):
                questions.append(f)
            continue
        if set_value(page, f, val, log):
            filled.append({"id": f["id"], "label": f.get("label"), "key": key, "value": "(file)" if key == "resume" else val})
            time.sleep(0.15)
        else:
            questions.append(f)
    return filled, questions


def apply_answer(page, field, answer, log=None):
    """Put a bank or AI answer into a field, mapping free text onto options when needed."""
    kind = field["kind"]
    opts = field.get("options") or []
    if kind in ("select", "radio", "combobox") and opts:
        o = _pick_option(opts, answer)
        if not o:
            if YES.search(str(answer)):
                o = yes_no_option(opts, True)
            elif NO.search(str(answer)):
                o = yes_no_option(opts, False)
        if not o and PREFER_NOT.search(str(answer)):
            o = prefer_not_option(opts)
        if not o:
            return False
        return set_value(page, field, o["text"], log)
    if kind == "checkbox":
        return set_value(page, field, "yes" if YES.search(str(answer)) or len(opts) > 1 else "no", log) if len(opts) == 1 else set_value(page, field, [a.strip() for a in re.split(r"[,;/]", str(answer))], log)
    return set_value(page, field, answer, log)


def describe(field):
    """Compact dict for the UI and the AI."""
    return {"id": field["id"], "label": field.get("label") or field.get("placeholder") or field.get("name") or "Question",
            "kind": field["kind"], "required": bool(field.get("required")),
            "options": [o.get("text") for o in (field.get("options") or []) if o.get("text")][:40]}

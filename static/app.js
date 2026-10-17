/* JobRadar dashboard */
(() => {
  "use strict";

  // ------------------------------------------------------------ icons
  const ICONS = {
    radar: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><path d="M12 12l6-6"/></svg>',
    stop: '<svg viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>',
    moon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>',
    sun: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>',
    upload: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M12 18v-6M9 15l3-3 3 3"/></svg>',
    file: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h6"/></svg>',
    search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>',
    chev: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 9l6 6 6-6"/></svg>',
    download: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 3v12M7 10l5 5 5-5M5 21h14"/></svg>',
    x: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>',
    ext: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/></svg>',
    bookmark: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M6 3h12v18l-6-4-6 4z"/></svg>',
    check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12l5 5 9-10"/></svg>',
    eyeoff: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 3l18 18M10.6 6.1A9.6 9.6 0 0 1 12 6c5 0 9 6 9 6a15 15 0 0 1-3 3.5M6.6 7.6C4.2 9.2 3 12 3 12s4 6 9 6a8.6 8.6 0 0 0 4.4-1.2"/><path d="M9.9 10a3 3 0 0 0 4.1 4.1"/></svg>',
    undo: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 14L4 9l5-5"/><path d="M4 9h11a5 5 0 0 1 0 10h-3"/></svg>',
    doc: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 6h16M4 12h16M4 18h10"/></svg>',
    pin: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 21s-7-6.5-7-12a7 7 0 0 1 14 0c0 5.5-7 12-7 12z"/><circle cx="12" cy="9" r="2.5"/></svg>',
    user: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></svg>',
    sparkles: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/><path d="M19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8z"/></svg>',
    eye: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 12s4-6 9-6 9 6 9 6-4 6-9 6-9-6-9-6z"/><circle cx="12" cy="12" r="3"/></svg>',
    trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/></svg>',
    spinner: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M12 3a9 9 0 1 0 9 9"/></svg>',
    send: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4z"/></svg>',
  };
  const icon = (n) => `<span class="ico">${ICONS[n] || ""}</span>`;
  const paintIcons = (root = document) => root.querySelectorAll(".ico[data-i]").forEach((el) => { el.innerHTML = ICONS[el.dataset.i] || ""; });

  // ------------------------------------------------------------ helpers
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const safeUrl = (u) => (/^https?:\/\//i.test(u || "") ? u : "#");
  const debounce = (fn, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };

  async function api(path, opts = {}) {
    const init = { ...opts, headers: { ...(opts.headers || {}) } };
    if (opts.json !== undefined) {
      init.body = JSON.stringify(opts.json);
      init.headers["Content-Type"] = "application/json";
      delete init.json;
    }
    const r = await fetch(path, init);
    if (!r.ok) {
      let msg = `${r.status}`;
      try { msg = (await r.json()).detail || msg; } catch (_) {}
      throw new Error(msg);
    }
    return r.json();
  }

  function toast(msg, err = false) {
    const el = document.createElement("div");
    el.className = "toast" + (err ? " err" : "");
    el.textContent = msg;
    $("#toasts").appendChild(el);
    setTimeout(() => el.remove(), err ? 6000 : 3200);
  }

  function ago(days) {
    if (days == null) return "date unknown";
    if (days < 1) return "today";
    if (days < 2) return "yesterday";
    if (days < 30) return `${Math.floor(days)} days ago`;
    return `${Math.floor(days / 30)} mo ago`;
  }

  function relTime(isoStr) {
    if (!isoStr) return "";
    const s = (Date.now() - new Date(isoStr).getTime()) / 1000;
    if (s < 60) return "just now";
    if (s < 3600) return `${Math.floor(s / 60)} min ago`;
    if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
    return `${Math.floor(s / 86400)} d ago`;
  }

  const store = {
    get(k, d) { try { const v = localStorage.getItem("jr:" + k); return v == null ? d : JSON.parse(v); } catch (_) { return d; } },
    set(k, v) { try { localStorage.setItem("jr:" + k, JSON.stringify(v)); } catch (_) {} },
  };

  // ------------------------------------------------------------ state
  const S = {
    meta: { sources: [], skills: [], roles: [] },
    profile: null,
    draft: null,
    dirty: false,
    filters: Object.assign({ q: "", chance: [], sources: [], remote: "all", days: 0, sort: "chance", min: 35, excl: false, status: "active" },
      store.get("filters", {})),
    page: 1,
    selected: new Set(),
    items: [],
    total: 0,
    running: false,
    pollTimer: null,
    lastListRefresh: 0,
    sourceLabel: {},
  };

  // ------------------------------------------------------------ theme
  function applyTheme(t) {
    if (t) document.documentElement.dataset.theme = t; else delete document.documentElement.dataset.theme;
    const dark = t ? t === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
    $("#btnTheme").innerHTML = icon(dark ? "sun" : "moon");
  }
  $("#btnTheme").addEventListener("click", () => {
    const cur = document.documentElement.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    const next = cur === "dark" ? "light" : "dark";
    store.set("theme", next);
    applyTheme(next);
  });

  // ------------------------------------------------------------ sidebar panels
  function showPanel(name) {
    if (!["profile", "ai", "apply"].includes(name)) name = "profile";
    $$("#sideNav button").forEach((b) => b.classList.toggle("on", b.dataset.panel === name));
    $("#panelProfile").classList.toggle("hidden", name !== "profile");
    $("#panelAi").classList.toggle("hidden", name !== "ai");
    $("#panelApply").classList.toggle("hidden", name !== "apply");
    store.set("panel", name);
    $("#sidebar").scrollTop = 0;
  }
  $("#sideNav").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-panel]");
    if (b) showPanel(b.dataset.panel);
  });

  // ------------------------------------------------------------ AI settings (API keys, provider, model)
  const AI = { settings: null, provider: "anthropic", draft: {} };

  async function loadAiSettings() {
    AI.settings = await api("/api/ai/settings");
    AI.provider = AI.settings.provider;
    AI.draft = {};
    for (const [p, v] of Object.entries(AI.settings.providers)) AI.draft[p] = { api_key: "", model: v.model, base_url: v.base_url };
    renderAi();
  }

  function aiLabel(p) { return ((AI.settings && AI.settings.catalog[p]) || {}).label || p || ""; }

  function renderAi() {
    if (!AI.settings) return;
    const cat = AI.settings.catalog;
    $("#aiProviderTabs").innerHTML = Object.entries(cat).map(([k, m]) =>
      `<button type="button" data-p="${k}" class="${k === AI.provider ? "on" : ""}">${esc(m.label)}${AI.settings.providers[k].ready ? '<i class="ok" title="Key saved"></i>' : ""}</button>`).join("");
    const m = cat[AI.provider], v = AI.settings.providers[AI.provider], d = AI.draft[AI.provider];
    const key = $("#aiKey");
    key.value = d.api_key || "";
    key.placeholder = v.has_key ? `Saved ${v.key_mask}. Paste a new key to replace it.` : m.key_hint;
    $("#aiKeyStatus").textContent = v.has_key ? `saved ${v.key_mask}` : "not saved";
    $("#aiKeyRemove").classList.toggle("hidden", !v.has_key);
    $("#aiModel").value = d.model || "";
    $("#aiModel").placeholder = m.default_model || "e.g. model-name";
    $("#aiModelList").innerHTML = (m.models || []).map((x) => `<option value="${esc(x)}">`).join("");
    $("#aiBaseUrlField").classList.toggle("hidden", !m.needs_base_url);
    $("#aiBaseUrl").value = d.base_url || "";
    $("#aiHelp").textContent = m.help || "";
    const ready = AI.settings.ready;
    const st = $("#aiState");
    st.textContent = ready ? `Ready · ${aiLabel(AI.settings.provider)}` : "Not set up";
    st.className = "pill " + (ready ? "High" : "src");
    $("#aiNavDot").classList.toggle("hidden", ready);
  }

  $("#aiProviderTabs").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-p]");
    if (!b) return;
    AI.provider = b.dataset.p;
    $("#aiTestResult").classList.add("hidden");
    renderAi();
  });
  $("#aiKey").addEventListener("input", (e) => { AI.draft[AI.provider].api_key = e.target.value; });
  $("#aiModel").addEventListener("input", (e) => { AI.draft[AI.provider].model = e.target.value; });
  $("#aiBaseUrl").addEventListener("input", (e) => { AI.draft[AI.provider].base_url = e.target.value; });
  $("#aiKeyToggle").addEventListener("click", () => {
    const k = $("#aiKey");
    k.type = k.type === "password" ? "text" : "password";
    $("#aiKeyToggle").innerHTML = icon(k.type === "password" ? "eye" : "eyeoff");
  });
  $("#aiKeyRemove").addEventListener("click", async () => {
    if (!confirm(`Remove the saved ${aiLabel(AI.provider)} API key?`)) return;
    try {
      const prov = AI.provider;
      await api("/api/ai/settings", { method: "PUT", json: { providers: { [prov]: { api_key: null } } } });
      toast("API key removed.");
      await loadAiSettings();
      AI.provider = prov; renderAi();
    } catch (e) { toast(e.message, true); }
  });

  function aiPayload() {
    const providers = {};
    for (const [p, d] of Object.entries(AI.draft)) {
      providers[p] = { model: d.model, base_url: d.base_url };
      if ((d.api_key || "").trim()) providers[p].api_key = d.api_key.trim();
    }
    return { provider: AI.provider, providers };
  }

  async function saveAiSettings(quiet = false) {
    const btn = $("#btnAiSave");
    btn.disabled = true;
    try {
      const prov = AI.provider;
      AI.settings = await api("/api/ai/settings", { method: "PUT", json: aiPayload() });
      for (const p of Object.keys(AI.draft)) AI.draft[p].api_key = "";
      AI.provider = prov;
      renderAi();
      if (!quiet) toast(AI.settings.ready ? `AI settings saved. Tailoring uses ${aiLabel(AI.settings.provider)}.` : "AI settings saved. Add an API key to enable tailoring.");
      if (S.current) renderDrawer(S.current);
      return true;
    } catch (e) {
      toast("Could not save: " + e.message, true);
      return false;
    } finally { btn.disabled = false; }
  }
  $("#btnAiSave").addEventListener("click", () => saveAiSettings());
  $("#btnAiTest").addEventListener("click", async () => {
    const btn = $("#btnAiTest"), out = $("#aiTestResult");
    if (!(await saveAiSettings(true))) return;
    btn.disabled = true; btn.textContent = "Testing...";
    out.className = "callout"; out.textContent = `Contacting ${aiLabel(AI.provider)}...`;
    try {
      const r = await api("/api/ai/test", { method: "POST", json: { provider: AI.provider } });
      out.className = "callout ok"; out.textContent = r.message;
    } catch (e) {
      out.className = "callout bad"; out.textContent = e.message;
    } finally { btn.disabled = false; btn.textContent = "Test connection"; }
  });

  // ------------------------------------------------------------ profile UI
  function markDirty() {
    S.dirty = true;
    $("#dirty").classList.remove("hidden");
    renderQueries();
  }

  function chipEditor(listKey, containerSel, inputSel, { canonical } = {}) {
    const box = $(containerSel);
    const input = $(inputSel);
    const render = () => {
      const arr = S.draft[listKey] || [];
      box.innerHTML = arr.map((v, i) => `<span class="chip">${esc(v)}<button data-i="${i}" title="Remove">×</button></span>`).join("");
      if (listKey === "skills") $("#skillCount").textContent = arr.length ? `${arr.length}` : "";
      if (listKey === "target_roles") renderRoleSuggest();
    };
    box.addEventListener("click", (e) => {
      const b = e.target.closest("button[data-i]");
      if (!b) return;
      S.draft[listKey].splice(+b.dataset.i, 1);
      render(); markDirty();
    });
    const add = (raw) => {
      raw.split(",").map((x) => x.trim()).filter(Boolean).forEach((v) => {
        if (canonical) {
          const hit = S.meta.skills.find((s) => s.toLowerCase() === v.toLowerCase());
          if (hit) v = hit;
        }
        const arr = S.draft[listKey] = S.draft[listKey] || [];
        if (!arr.some((x) => x.toLowerCase() === v.toLowerCase())) arr.push(v);
      });
      input.value = "";
      render(); markDirty();
    };
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && input.value.trim()) { e.preventDefault(); add(input.value); }
    });
    input.addEventListener("change", () => {
      // Selecting from the datalist fires change; add immediately when it's an exact option.
      const v = input.value.trim();
      const list = listKey === "skills" ? S.meta.skills : listKey === "target_roles" ? S.meta.roles : [];
      if (v && list.some((x) => x.toLowerCase() === v.toLowerCase())) add(v);
    });
    return { render, add };
  }

  let skillsEd, rolesEd, locEd;

  function renderRoleSuggest() {
    const have = new Set((S.draft.target_roles || []).map((r) => r.toLowerCase()));
    const sug = (S.draft.suggested_roles || []).filter((r) => !have.has(r.toLowerCase()));
    $("#roleSuggest").innerHTML = sug.map((r) => `<span class="chip" data-r="${esc(r)}">+ ${esc(r)}</span>`).join("");
  }
  $("#roleSuggest").addEventListener("click", (e) => {
    const c = e.target.closest(".chip[data-r]");
    if (c) rolesEd.add(c.dataset.r);
  });

  function renderQueries() {
    const d = S.draft;
    let roles = (d.target_roles || []).filter(Boolean);
    if (!roles.length) roles = [d.current_title, ...(d.suggested_roles || [])].filter(Boolean);
    roles = [...new Set(roles)].slice(0, +d.max_queries || 6);
    $("#queriesPreview").innerHTML = roles.length
      ? `Searches will use: <b>${roles.map(esc).join("</b>, <b>")}</b> in <b>${(d.search_locations || []).map(esc).join("</b>, <b>") || esc(d.country || "")}</b>`
      : "Add target roles or upload your resume to define what to search for.";
  }

  function fillProfile(p) {
    S.profile = p;
    S.draft = JSON.parse(JSON.stringify(p));
    $("#pName").value = p.name || "";
    $("#pTitle").value = p.current_title || "";
    $("#pYears").value = p.years_experience ?? "";
    $("#yearsHint").textContent = p.years_method && p.years_experience != null ? `(${p.years_method})` : "";
    $("#pCountry").value = p.country || "";
    $("#pDays").value = String(p.posted_within_days || 14);
    $("#pRemote").checked = !!p.remote_ok;
    $("#pHeadless").checked = !!p.naukri_headless;
    $("#aQueries").value = p.max_queries;
    $("#aMin").value = p.min_match_to_show;
    $("#aLiPages").value = p.linkedin_pages;
    $("#aLiDetails").value = p.linkedin_details;
    $("#aNkPages").value = p.naukri_pages;
    const dz = $("#drop");
    if (p.resume_filename) {
      dz.classList.add("loaded");
      dz.querySelector(".ico").innerHTML = ICONS.file;
      $("#resumeName").textContent = p.resume_filename;
      $("#resumeHint").textContent = `Uploaded ${relTime(p.resume_uploaded_at)}. Click or drop to replace.`;
    }
    renderSourcesList();
    skillsEd.render(); rolesEd.render(); locEd.render();
    renderQueries();
    S.dirty = false;
    $("#dirty").classList.add("hidden");
  }

  function renderSourcesList() {
    const on = new Set(S.draft.sources || []);
    $("#sourcesList").innerHTML = S.meta.sources.map((s) => `
      <label class="src-opt"><input type="checkbox" value="${s.key}" ${on.has(s.key) ? "checked" : ""}>
        <div><div class="t">${esc(s.label)} <span class="pill src">${esc(s.region)}</span></div><div class="d">${esc(s.description)}</div></div>
      </label>`).join("");
  }
  $("#sourcesList").addEventListener("change", () => {
    S.draft.sources = $$("#sourcesList input:checked").map((i) => i.value);
    markDirty();
  });

  const bindField = (sel, key, conv = (v) => v) => {
    $(sel).addEventListener("input", (e) => {
      S.draft[key] = conv(e.target.type === "checkbox" ? e.target.checked : e.target.value);
      markDirty();
    });
    $(sel).addEventListener("change", (e) => {
      S.draft[key] = conv(e.target.type === "checkbox" ? e.target.checked : e.target.value);
      markDirty();
    });
  };
  const num = (v) => (v === "" ? null : Number(v));

  async function saveProfile() {
    const btn = $("#btnSave");
    btn.disabled = true; btn.textContent = "Saving...";
    try {
      const body = { ...S.draft };
      delete body.has_resume; delete body.queries;
      const p = await api("/api/profile", { method: "PUT", json: body });
      fillProfile(p);
      toast("Profile saved. All jobs re-scored.");
      S.page = 1; loadJobs();
    } catch (e) {
      toast("Save failed: " + e.message, true);
    } finally {
      btn.disabled = false; btn.textContent = "Save and re-score";
    }
  }

  async function uploadResume(file) {
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    $("#resumeName").textContent = "Reading " + file.name + "...";
    try {
      const r = await fetch("/api/resume", { method: "POST", body: fd });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || r.status);
      fillProfile(data.profile);
      const p = data.parsed;
      toast(`Resume read: ${p.skills.length} skills found` + (p.years_experience != null ? `, ${p.years_experience} years experience` : "") + ". Check and adjust, then Find jobs.");
      loadJobs();
    } catch (e) {
      toast("Could not read resume: " + e.message, true);
      if (S.profile) fillProfile(S.profile);
    }
  }

  // ------------------------------------------------------------ scraping
  async function startSearch() {
    if (S.dirty) await saveProfile();
    try {
      await api("/api/scrape", { method: "POST", json: {} });
      S.running = true;
      setRunningUI(true);
      poll();
    } catch (e) {
      toast(e.message, true);
    }
  }

  function setRunningUI(on) {
    $("#btnFind").classList.toggle("hidden", on);
    $("#btnStop").classList.toggle("hidden", !on);
    if (on) $("#progressPanel").classList.remove("hidden");
    $("#progressTitle").textContent = on ? "Searching job portals..." : "Last search";
  }

  function renderStatus(st) {
    const srcs = st.sources || {};
    const keys = Object.keys(srcs);
    if (!keys.length && st.last_run && st.last_run.summary) {
      Object.assign(srcs, st.last_run.summary);
    }
    const tiles = Object.entries(srcs).map(([k, s]) => {
      const state = s.state || "queued";
      const pct = Math.round((s.progress ?? (state === "done" ? 1 : 0)) * 100);
      const label = s.label || S.sourceLabel[k] || k;
      const stateTxt = { queued: "Queued", running: `${pct}%`, done: "Done", error: "Error", blocked: "Blocked", stopped: "Stopped" }[state] || state;
      return `<div class="tile ${state}">
        <div class="tile-top"><span>${esc(label)}</span><span class="small muted" style="display:flex;align-items:center;gap:6px">${stateTxt}<i class="dot ${state}"></i></span></div>
        <div class="bar"><i style="width:${state === "done" ? 100 : pct}%"></i></div>
        <div class="tile-meta"><b>${s.relevant ?? 0}</b> relevant · ${s.scanned ?? 0} scanned${s.new ? ` · ${s.new} new` : ""}</div>
        ${s.message && state !== "done" ? `<div class="tile-msg" title="${esc(s.message)}">${esc(s.message)}</div>` : ""}
      </div>`;
    }).join("");
    $("#sourceTiles").innerHTML = tiles;
    if (tiles) $("#progressPanel").classList.remove("hidden");
    const vals = Object.values(srcs);
    const rel = vals.reduce((a, s) => a + (s.relevant || 0), 0);
    const scanned = vals.reduce((a, s) => a + (s.scanned || 0), 0);
    const failed = vals.filter((s) => s.state === "error" || s.state === "blocked").length;
    const doneN = vals.filter((s) => ["done", "error", "blocked", "stopped"].includes(s.state)).length;
    $("#progressSummary").textContent = st.running
      ? `${doneN} of ${vals.length} portals finished · ${rel} relevant jobs so far from ${scanned} scanned`
      : `${rel} relevant jobs from ${scanned} scanned across ${vals.length} portals` + (failed ? ` · ${failed} portal${failed > 1 ? "s" : ""} had problems` : "");
    const collapsed = !st.running && !S.showDetails && !failed;
    $("#progressPanel").classList.toggle("collapsed", collapsed);
    $("#btnDetails").textContent = collapsed ? "Details" : "Hide details";
    $("#btnDetails").classList.toggle("hidden", !!st.running);
    S.lastStatus = st;
    $("#logBox").textContent = (st.log || []).map((l) => `${new Date(l.t).toLocaleTimeString()}  ${l.msg}`).join("\n");
    const lr = st.last_run;
    $("#lastRun").textContent = st.running ? "Search in progress" : lr ? `Last search ${relTime(lr.finished_at)}` : "No searches yet";
  }

  async function poll() {
    clearTimeout(S.pollTimer);
    try {
      const st = await api("/api/scrape/status");
      renderStatus(st);
      if (st.running) {
        if (Date.now() - S.lastListRefresh > 4000) loadJobs(true);
        S.pollTimer = setTimeout(poll, 1500);
      } else if (S.running) {
        S.running = false;
        setRunningUI(false);
        loadJobs();
        const tot = Object.values(st.sources || {}).reduce((a, s) => a + (s.new || 0), 0);
        toast(`Search finished. ${tot} new matching jobs.`);
      }
    } catch (e) {
      S.pollTimer = setTimeout(poll, 4000);
    }
  }

  // ------------------------------------------------------------ jobs list
  function query(extra = {}) {
    const f = S.filters;
    const p = new URLSearchParams({
      q: f.q, chance: f.chance.join(","), sources: f.sources.join(","), remote: f.remote, days: f.days, sort: f.sort,
      min_score: f.min, show_excluded: f.excl, status: f.status, ...extra,
    });
    return p.toString();
  }

  async function loadJobs(silent = false) {
    S.lastListRefresh = Date.now();
    store.set("filters", S.filters);
    if (!silent && S.page === 1) $("#jobs").innerHTML = '<div class="skeleton"></div>'.repeat(4);
    try {
      const pageSize = 30;
      const size = silent ? Math.max(pageSize, S.items.length) : pageSize;
      const data = await api(`/api/jobs?${query({ page: silent ? 1 : S.page, page_size: size })}`);
      S.items = silent || S.page === 1 ? data.items : S.items.concat(data.items);
      S.total = data.total;
      renderStats(data.stats);
      renderFacets(data.facets);
      renderJobs();
    } catch (e) {
      if (!silent) $("#jobs").innerHTML = `<div class="empty"><h3>Could not load jobs</h3><p>${esc(e.message)}</p></div>`;
    }
  }

  function renderStats(s) {
    $("#sMatched").textContent = s.matched;
    $("#sHigh").textContent = s.high;
    $("#sNew").textContent = s.new;
    $("#sSaved").textContent = s.saved;
    $("#sApplied").textContent = s.applied;
  }

  function renderFacets(f) {
    const sel = new Set(S.filters.sources);
    $("#fSources").innerHTML = S.meta.sources.map((s) =>
      `<label><input type="checkbox" value="${s.key}" ${sel.has(s.key) ? "checked" : ""}>${esc(s.label)}<span class="n">${f.sources[s.key] || 0}</span></label>`).join("");
    $("#fSourcesBtn").innerHTML = (sel.size ? `${sel.size} source${sel.size > 1 ? "s" : ""}` : "All sources") + " " + icon("chev");
    $$("#fChance button").forEach((b) => {
      b.textContent = `${b.dataset.c} ${f.chance[b.dataset.c] ?? 0}`;
    });
  }

  function ring(score, label) {
    const r = 25, c = 2 * Math.PI * r;
    const color = label === "High" ? "var(--high)" : label === "Medium" ? "var(--med)" : "var(--low)";
    const off = c * (1 - Math.max(0, Math.min(100, score)) / 100);
    return `<div class="ring" title="Interview chance ${score}%">
      <svg viewBox="0 0 58 58"><circle class="bg" cx="29" cy="29" r="${r}" fill="none" stroke-width="5"/>
      <circle class="fg" cx="29" cy="29" r="${r}" fill="none" stroke="${color}" stroke-width="5" stroke-dasharray="${c}" stroke-dashoffset="${off}"/></svg>
      <div class="val"><b>${Math.round(score)}</b><span>chance</span></div></div>`;
  }

  function srcLabel(k) { return S.sourceLabel[k] || k; }

  function jobCard(j) {
    const b = j.breakdown || {};
    const matched = (j.matched_skills || []).slice(0, 8).map((s) => `<span class="chip match">${esc(s)}</span>`).join("");
    const moreM = (j.matched_skills || []).length > 8 ? `<span class="chip match">+${j.matched_skills.length - 8}</span>` : "";
    const missing = (j.missing_skills || []).slice(0, 4).map((s) => `<span class="chip miss" title="Mentioned in the job, not in your skills">${esc(s)}</span>`).join("");
    const logo = j.company_logo ? `<img class="company-logo" src="${esc(safeUrl(j.company_logo))}" alt="" loading="lazy" onerror="this.remove()">` : "";
    const also = (j.also_on || []).map((a) => `<span class="pill src">${esc(srcLabel(a.source))}</span>`).join(" ");
    const why = [b.exp_note, b.location === "maybe" ? b.location_note : null, b.comp_note && j.applicants ? b.comp_note : null]
      .filter(Boolean).map(esc).join(" · ");
    const st = j.status;
    const ap = j.apply_state;
    const apPill = ap ? `<span class="pill ap-${esc(ap)}">${{ queued: "Apply queued", running: "Applying", needs_you: "Needs you", submitted: "Auto applied", failed: "Apply failed", skipped: "Apply skipped" }[ap] || esc(ap)}</span>` : "";
    return `<article class="job ${st === "hidden" || j.excluded ? "dim" : ""} ${S.selected.has(j.id) ? "selected" : ""}" data-id="${j.id}">
      <div class="job-left">${ring(j.chance_score, j.chance_label)}
        <label class="sel" title="Select for auto apply"><input type="checkbox" class="job-sel" ${S.selected.has(j.id) ? "checked" : ""}><span></span></label></div>
      <div class="job-main">
        <div class="job-title" data-act="jd">${esc(j.title)}</div>
        <div class="job-sub">
          <span>${logo}<span class="co">${esc(j.company || "Unknown company")}</span></span>
          ${j.location ? `<span class="sep">${esc(j.location)}</span>` : ""}
          ${j.remote ? '<span class="pill new">Remote</span>' : ""}
          <span class="sep">${ago(j.days_ago)}</span>
          <span class="pill ${esc(j.chance_label)}">${esc(j.chance_label)} chance</span>
          <span class="pill src">${esc(srcLabel(j.source))}</span>${also}
          ${j.is_new ? '<span class="pill new">New</span>' : ""}
          ${j.tailored_count ? `<span class="pill tailored" title="You have a tailored resume for this job">${icon("sparkles")}Tailored</span>` : ""}
          ${apPill}
          ${j.salary ? `<span class="sep">${esc(j.salary)}</span>` : ""}
        </div>
        <div class="chips">${matched}${moreM}${missing}</div>
        <div class="job-why">Match ${Math.round(j.match_score)}%${why ? " · " + why : ""}
          ${j.excluded ? `<span class="pill excl">Excluded: ${esc(j.exclude_reason || "")}</span>` : ""}</div>
      </div>
      <div class="job-actions">
        <button class="btn small" data-act="jd">${icon("doc")}Show JD</button>
        <button class="btn small ai" data-act="tailor" title="Rewrite your resume for this job with AI">${icon("sparkles")}Tailor resume</button>
        <button class="btn small" data-act="apply" title="Open this application in the assistant browser and fill it" ${["queued", "running", "needs_you"].includes(ap) ? "disabled" : ""}>${icon("send")}${ap === "submitted" ? "Apply again" : "Auto apply"}</button>
        <a class="btn small primary" href="${esc(safeUrl(j.apply_url || j.url))}" target="_blank" rel="noopener" data-act="apply">Apply ${icon("ext")}</a>
        <div class="row">
          <button class="btn small icon icon-btn ${st === "saved" ? "on-saved" : ""}" data-act="saved" title="${st === "saved" ? "Unsave" : "Save"}">${icon("bookmark")}</button>
          <button class="btn small icon icon-btn ${st === "applied" ? "on-applied" : ""}" data-act="applied" title="${st === "applied" ? "Unmark applied" : "Mark as applied"}">${icon("check")}</button>
          <button class="btn small icon icon-btn" data-act="hidden" title="${st === "hidden" ? "Unhide" : "Hide"}">${icon(st === "hidden" ? "undo" : "eyeoff")}</button>
        </div>
      </div>
    </article>`;
  }

  function renderJobs() {
    const box = $("#jobs");
    const f = S.filters;
    if (!S.items.length) {
      let title = "No jobs yet", body = "Click <b>Find jobs</b> to search all portals.";
      if (!S.profile || !(S.profile.skills || []).length) {
        title = "Start by uploading your resume";
        body = "JobRadar reads your skills, experience and current role, then searches LinkedIn, Naukri and remote job boards for jobs that fit you.";
      } else if (f.status !== "active") {
        title = `Nothing ${f.status === "all" ? "stored" : f.status} yet`;
        body = "Jobs you save, apply to or hide appear here.";
      } else if (S.profile && !S.running && $("#sMatched").textContent !== "0") {
        title = "No jobs match these filters";
        body = "Try lowering the minimum match, clearing the search box or selecting more sources.";
      }
      box.innerHTML = `<div class="empty">${icon("radar")}<h3>${title}</h3><p>${body}</p></div>`;
      $("#btnMore").classList.add("hidden");
      $("#resultInfo").textContent = "";
      return;
    }
    box.innerHTML = S.items.map(jobCard).join("");
    $("#btnMore").classList.toggle("hidden", S.items.length >= S.total);
    $("#resultInfo").textContent = `Showing ${S.items.length} of ${S.total} jobs`;
  }

  async function setStatus(id, status) {
    const j = S.items.find((x) => x.id === id) || S.current;
    const next = j && j.status === status ? "new" : status;
    try {
      await api(`/api/jobs/${id}/status`, { method: "POST", json: { status: next } });
      if (j) j.status = next;
      const msg = { saved: "Saved", applied: "Marked as applied", hidden: "Hidden", new: "Restored" }[next];
      toast(msg);
      if (S.current && S.current.id === id) { S.current.status = next; renderDrawer(S.current); }
      loadJobs(true);
    } catch (e) { toast(e.message, true); }
  }

  $("#jobs").addEventListener("click", (e) => {
    const card = e.target.closest(".job");
    if (!card) return;
    const id = +card.dataset.id;
    const act = e.target.closest("[data-act]")?.dataset.act;
    if (e.target.closest(".job-sel")) return;
    if (act === "jd") openDrawer(id);
    else if (act === "tailor") tailorJob(id);
    else if (act === "apply") applyJobs([id]);
    else if (act === "saved" || act === "applied" || act === "hidden") setStatus(id, act);
  });

  // ------------------------------------------------------------ drawer
  function bar(label, val, note) {
    return `<div class="why-item"><div class="lbl"><span>${label}</span><span>${val}%</span></div>
      <div class="bar"><i style="width:${val}%"></i></div>${note ? `<div class="note">${esc(note)}</div>` : ""}</div>`;
  }

  function renderDrawer(j) {
    const b = j.breakdown || {};
    const logo = j.company_logo ? `<img class="company-logo" src="${esc(safeUrl(j.company_logo))}" alt="" onerror="this.remove()">` : "";
    const matched = (j.matched_skills || []).map((s) => `<span class="chip match">${esc(s)}</span>`).join("") || '<span class="muted small">None detected</span>';
    const missing = (j.missing_skills || []).map((s) => `<span class="chip miss">${esc(s)}</span>`).join("") || '<span class="muted small">Nothing missing</span>';
    const also = (j.also_on || []).map((a) => `<a class="btn small ghost" href="${esc(safeUrl(a.url))}" target="_blank" rel="noopener">Also on ${esc(srcLabel(a.source))} ${icon("ext")}</a>`).join("");
    const notes = (b.notes || []).map((n) => `<div class="callout warn">${esc(n)}</div>`).join("");
    const st = j.status;
    $("#drawerBody").innerHTML = `
      <div class="job-sub" style="margin:0 0 6px">${logo}<span class="co">${esc(j.company || "")}</span>
        ${j.location ? `<span class="sep">${icon("pin")} ${esc(j.location)}</span>` : ""}
        ${j.remote ? '<span class="pill new">Remote</span>' : ""}</div>
      <h1 class="d-title">${esc(j.title)}</h1>
      <div class="job-sub">
        <span class="pill ${esc(j.chance_label)}">${esc(j.chance_label)} interview chance · ${Math.round(j.chance_score)}%</span>
        <span>Match ${Math.round(j.match_score)}%</span>
        <span class="sep">${ago(j.days_ago)}</span>
        <span class="pill src">${esc(srcLabel(j.source))}</span>
        ${j.job_type ? `<span class="sep">${esc(j.job_type)}</span>` : ""}
        ${j.salary ? `<span class="sep">${esc(j.salary)}</span>` : ""}
        ${j.applicants ? `<span class="sep">${esc(j.applicants)}</span>` : ""}
      </div>
      <div class="d-actions">
        <a class="btn primary" href="${esc(safeUrl(j.apply_url || j.url))}" target="_blank" rel="noopener">Apply now ${icon("ext")}</a>
        <button class="btn ${st === "saved" ? "success" : ""}" data-st="saved">${icon("bookmark")}${st === "saved" ? "Saved" : "Save"}</button>
        <button class="btn ${st === "applied" ? "success" : ""}" data-st="applied">${icon("check")}${st === "applied" ? "Applied" : "Mark applied"}</button>
        <button class="btn ghost" data-st="hidden">${icon(st === "hidden" ? "undo" : "eyeoff")}${st === "hidden" ? "Unhide" : "Not interested"}</button>
        ${j.url && j.url !== j.apply_url ? `<a class="btn ghost" href="${esc(safeUrl(j.url))}" target="_blank" rel="noopener">View posting ${icon("ext")}</a>` : ""}
        ${also}
      </div>
      <div class="tl-actions">
        <button class="btn ai" data-tl="run" ${S.tailoring === j.id ? "disabled" : ""}>${icon("sparkles")}${S.tailoring === j.id ? "Tailoring..." : (j.tailored && j.tailored.length ? "Tailor again" : "Tailor resume to this job")}</button>
        <span class="muted small">${AI.settings && AI.settings.ready ? `Uses ${esc(aiLabel(AI.settings.provider))} · ${esc(AI.settings.providers[AI.settings.provider].model)}` : "Add an API key under AI settings first"}</span>
      </div>
      ${tailorSection(j)}
      ${j.excluded ? `<div class="callout bad">Excluded from matches: ${esc(j.exclude_reason || "")}</div>` : ""}
      <div class="d-section">
        <h3>Why this job fits</h3>
        <div class="why-grid">
          ${bar("Skills", b.skills ?? 0, `${(j.matched_skills || []).length} of your skills appear in this job`)}
          ${bar("Experience", b.experience ?? 0, b.exp_note)}
          ${bar("Role similarity", b.role ?? 0, b.role_note)}
          ${bar("Freshness", b.freshness ?? 0, b.fresh_note)}
          ${bar("Competition", b.competition ?? 0, b.comp_note)}
          ${bar("Location fit", b.location === "yes" ? 100 : b.location === "maybe" ? 50 : 0, b.location_note)}
        </div>
        ${notes}
      </div>
      <div class="d-section"><h3>Your matching skills</h3><div class="chips">${matched}</div></div>
      <div class="d-section"><h3>Skills in the job you have not listed</h3><div class="chips">${missing}</div></div>
      <div class="d-section">
        <h3>Job description</h3>
        <div class="jd">${j.description_html || `<p class="muted">The full description could not be loaded here. <a href="${esc(safeUrl(j.url))}" target="_blank" rel="noopener">Open the original posting</a>.</p>`}</div>
      </div>`;
  }

  $("#drawerBody").addEventListener("click", async (e) => {
    const b = e.target.closest("[data-st]");
    if (b && S.current) return setStatus(S.current.id, b.dataset.st);
    const t = e.target.closest("[data-tl]");
    if (!t || !S.current) return;
    const [act, arg] = t.dataset.tl.split(":");
    if (act === "run") tailorJob(S.current.id);
    else if (act === "close") { S.current.tailorView = null; S.current.tailorError = null; renderDrawer(S.current); }
    else if (act === "view") {
      try { S.current.tailorView = await api(`/api/tailored/${arg}`); S.current.tailorError = null; renderDrawer(S.current); }
      catch (err) { toast(err.message, true); }
    } else if (act === "del") {
      if (!confirm("Delete this tailored resume file?")) return;
      try {
        await api(`/api/tailored/${arg}`, { method: "DELETE" });
        S.current.tailored = (S.current.tailored || []).filter((x) => x.id !== +arg);
        if (S.current.tailorView && S.current.tailorView.id === +arg) S.current.tailorView = null;
        renderDrawer(S.current); loadJobs(true); toast("Deleted.");
      } catch (err) { toast(err.message, true); }
    }
  });

  // ------------------------------------------------------------ resume tailoring
  function tailorSection(j) {
    const parts = [];
    if (S.tailoring === j.id) {
      parts.push(`<div class="tailor-box working"><span class="ico spin">${ICONS.spinner}</span>
        <div><b>Tailoring your resume for ${esc(j.title)} at ${esc(j.company || "this company")}...</b>
        <div class="muted small">Usually 20 to 60 seconds. You can keep browsing; the result appears here.</div></div></div>`);
    } else if (j.tailorError) {
      parts.push(`<div class="callout bad tl-err"><b>Tailoring failed.</b> ${esc(j.tailorError)} <button class="btn small ghost" data-tl="close">Dismiss</button></div>`);
    }
    const v = j.tailorView;
    if (v && S.tailoring !== j.id) {
      const kws = (v.keywords || []).map((k) => `<span class="chip match">${esc(k)}</span>`).join("");
      const n = (v.changes || []).length;
      const ch = (v.changes || []).map((c) => `<div class="change">
          <div class="before">${esc(c.before)}</div>
          <div class="after">${esc(c.after)}</div>
          ${c.reason ? `<div class="why muted small">${esc(c.reason)}</div>` : ""}
        </div>`).join("");
      parts.push(`<div class="tailor-box result">
        <div class="tl-head">
          <div><b>${icon("sparkles")} Tailored resume ready</b><div class="muted small">${esc(aiLabel(v.provider))} ${esc(v.model || "")} · ${relTime(v.created_at)}</div></div>
          <button class="btn small ghost icon" data-tl="close" title="Hide">${icon("x")}</button>
        </div>
        ${v.summary ? `<p class="tl-summary">${esc(v.summary)}</p>` : ""}
        ${v.note ? `<div class="muted small tl-note">${esc(v.note)}</div>` : ""}
        ${atsBlock(v)}
        ${!v.ats || !v.ats.formatted ? (kws ? `<div class="tl-kw"><span class="muted small">Job keywords now in your resume</span><div class="chips">${kws}</div></div>` : "") : ""}
        <details class="sub" open><summary>${n} line${n === 1 ? "" : "s"} changed</summary><div class="changes">${ch || '<div class="muted small">No line-level changes recorded.</div>'}</div></details>
      </div>`);
    }
    const list = (j.tailored || []).filter((x) => !v || x.id !== v.id);
    if (list.length) {
      parts.push(`<div class="d-section tl-list"><h3>Tailored resumes for this job</h3>
        ${list.map((x) => `<div class="tl-item">
          <div class="tl-item-main"><b>${x.ats && x.ats.score != null ? `<span class="pill ${x.ats.score >= 85 ? "High" : x.ats.score >= 65 ? "Medium" : "Low"}">ATS ${x.ats.score}</span> ` : ""}${esc(x.filename)}</b><div class="muted small">${esc(aiLabel(x.provider))} ${esc(x.model || "")} · ${relTime(x.created_at)}${x.summary ? " · " + esc(x.summary) : ""}</div></div>
          <div class="row">
            ${x.ats_filename ? `<a class="btn small" href="/api/tailored/${x.id}/download?variant=ats" title="Download ATS-safe copy">${icon("download")}ATS</a>` : ""}
            <a class="btn small" href="/api/tailored/${x.id}/download" title="Download">${icon("download")}</a>
            <button class="btn small" data-tl="view:${x.id}">Changes</button>
            <button class="btn small ghost icon" data-tl="del:${x.id}" title="Delete">${icon("trash")}</button>
          </div></div>`).join("")}
      </div>`);
    }
    return parts.join("");
  }

  function atsBlock(v) {
    const a = v.ats || {};
    const fmt = a.formatted, safe = a.ats_copy;
    if (!fmt) return `<div class="tl-dl"><a class="btn primary small" href="/api/tailored/${v.id}/download">${icon("download")}Download ${esc((v.output_format || "").toUpperCase())}</a></div>`;
    const best = safe || fmt;
    const cls = (sc) => (sc >= 85 ? "High" : sc >= 65 ? "Medium" : "Low");
    const issues = fmt.checks.filter((c) => c.status !== "pass" && c.id !== "keywords");
    const dl = (variant, label, sub, sc, primary) => `<a class="dl-card ${primary ? "primary" : ""}" href="/api/tailored/${v.id}/download${variant ? "?variant=" + variant : ""}">
        <span class="dl-score ${cls(sc)}">${sc}</span><span class="dl-txt"><b>${icon("download")}${label}</b><span class="muted small">${sub}</span></span></a>`;
    const checkRow = (c) => `<div class="ck ${c.status}"><i></i><div><b>${esc(c.label)}</b><div class="muted small">${esc(c.detail)}</div></div></div>`;
    const covered = (best.covered || []).map((k) => `<span class="chip match">${esc(k)}</span>`).join("");
    const missing = (best.missing || []).map((k) => `<span class="chip miss" title="Add this only if you genuinely have it">${esc(k)}</span>`).join("");
    let note = "";
    if (safe && issues.length) note = `<div class="callout warn small">Your original layout has ${issues.length} ATS risk${issues.length > 1 ? "s" : ""} (${issues.map((c) => c.label.toLowerCase()).join(", ")}). Upload the ATS-safe copy to job portals and keep the formatted one for people.</div>`;
    else if (safe) note = `<div class="callout ok small">Your layout passed every structural check. Either file is safe to upload.</div>`;
    return `<div class="ats">
      <div class="ats-head"><b>ATS check</b><span class="muted small">score ${best.score}/100 · structure ${best.structure_score} · keywords ${best.keyword_score}%</span></div>
      <div class="dl-grid">
        ${safe ? dl("ats", "ATS-safe DOCX", "Single column, standard headings, no tables. Use for online applications.", safe.score, true) : ""}
        ${dl("", (safe ? "Your layout" : "Tailored") + " " + (v.output_format || "").toUpperCase(), safe ? "Your original formatting with the rewritten text." : "ATS-safe single-column layout.", fmt.score, !safe)}
      </div>
      ${note}
      <div class="ats-kw">
        <div><span class="muted small">Job keywords found (${(best.covered || []).length})</span><div class="chips">${covered || '<span class="muted small">None</span>'}</div></div>
        ${missing ? `<div><span class="muted small">Not found (${(best.missing || []).length}) — only add what you truly have</span><div class="chips">${missing}</div></div>` : ""}
      </div>
      <details class="sub"><summary>${fmt.checks.length} checks on ${safe ? "your layout" : "the file"}${issues.length ? ` · ${issues.length} to review` : " · all passed"}</summary>
        <div class="checks">${fmt.checks.map(checkRow).join("")}</div>
      </details>
    </div>`;
  }

  async function tailorJob(id) {
    if (!S.profile || !S.profile.has_resume) {
      toast("Upload your resume first, then tailor it to a job.", true);
      showPanel("profile"); return;
    }
    if (!AI.settings || !AI.settings.ready) {
      toast("Add an API key under AI settings to tailor your resume.", true);
      showPanel("ai"); return;
    }
    if (S.tailoring) { toast("Another resume is being tailored. Wait for it to finish.", true); return; }
    if (!S.current || S.current.id !== id) await openDrawer(id);
    if (!S.current || S.current.id !== id) return;
    S.tailoring = id;
    S.current.tailorError = null;
    renderDrawer(S.current);
    try {
      const rec = await api(`/api/jobs/${id}/tailor`, { method: "POST", json: {} });
      S.tailoring = null;
      if (S.current && S.current.id === id) {
        S.current.tailorView = rec;
        S.current.tailored = [rec, ...(S.current.tailored || [])];
        renderDrawer(S.current);
        $("#drawerBody").scrollTop = 0;
      }
      toast(`Tailored resume ready: ${rec.changes.length} lines rewritten.`);
      loadJobs(true);
    } catch (e) {
      S.tailoring = null;
      if (S.current && S.current.id === id) { S.current.tailorError = e.message; renderDrawer(S.current); }
      toast("Tailoring failed: " + e.message, true);
    }
  }

  async function openDrawer(id) {
    $("#overlay").classList.remove("hidden");
    $("#drawer").classList.add("open");
    $("#drawer").setAttribute("aria-hidden", "false");
    $("#drawerBody").innerHTML = '<div class="skeleton" style="height:60px;margin:10px 0"></div><div class="skeleton" style="height:300px"></div>';
    try {
      const [j, tl] = await Promise.all([api(`/api/jobs/${id}`), api(`/api/jobs/${id}/tailored`).catch(() => ({ items: [] }))]);
      j.tailored = tl.items || [];
      S.current = j;
      renderDrawer(j);
      $("#drawerBody").scrollTop = 0;
    } catch (e) {
      $("#drawerBody").innerHTML = `<div class="empty"><h3>Could not load this job</h3><p>${esc(e.message)}</p></div>`;
    }
  }
  function closeDrawer() {
    $("#drawer").classList.remove("open");
    $("#drawer").setAttribute("aria-hidden", "true");
    $("#overlay").classList.add("hidden");
    S.current = null;
  }
  $("#btnClose").addEventListener("click", closeDrawer);
  $("#overlay").addEventListener("click", closeDrawer);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDrawer(); });

  // ------------------------------------------------------------ filters wiring
  function syncFilterUI() {
    const f = S.filters;
    $("#fQ").value = f.q;
    $("#fRemote").value = f.remote;
    $("#fDays").value = String(f.days);
    $("#fSort").value = f.sort;
    $("#fMin").value = f.min; $("#fMinV").textContent = f.min;
    $("#fExcl").checked = f.excl;
    $$("#fChance button").forEach((b) => b.classList.toggle("on", f.chance.includes(b.dataset.c)));
    $$("#statusTabs button").forEach((b) => b.classList.toggle("on", b.dataset.s === f.status));
  }
  const refilter = () => { S.page = 1; loadJobs(); };
  $("#fQ").addEventListener("input", debounce((e) => { S.filters.q = e.target.value.trim(); refilter(); }, 250));
  $("#fRemote").addEventListener("change", (e) => { S.filters.remote = e.target.value; refilter(); });
  $("#fDays").addEventListener("change", (e) => { S.filters.days = +e.target.value; refilter(); });
  $("#fSort").addEventListener("change", (e) => { S.filters.sort = e.target.value; refilter(); });
  $("#fMin").addEventListener("input", (e) => { $("#fMinV").textContent = e.target.value; });
  $("#fMin").addEventListener("change", (e) => { S.filters.min = +e.target.value; refilter(); });
  $("#fExcl").addEventListener("change", (e) => { S.filters.excl = e.target.checked; refilter(); });
  $("#fChance").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    const c = b.dataset.c, arr = S.filters.chance;
    S.filters.chance = arr.includes(c) ? arr.filter((x) => x !== c) : [...arr, c];
    syncFilterUI(); refilter();
  });
  $("#statusTabs").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    S.filters.status = b.dataset.s; syncFilterUI(); refilter();
  });
  $("#fSourcesBtn").addEventListener("click", (e) => { e.stopPropagation(); $("#fSourcesDD").classList.toggle("open"); });
  document.addEventListener("click", (e) => { if (!e.target.closest("#fSourcesDD")) $("#fSourcesDD").classList.remove("open"); });
  $("#fSources").addEventListener("change", () => {
    S.filters.sources = $$("#fSources input:checked").map((i) => i.value); refilter();
  });
  $("#btnMore").addEventListener("click", () => { S.page += 1; loadJobs(); });
  $("#btnExport").addEventListener("click", (e) => { e.preventDefault(); window.location = `/api/jobs/export.csv?${query()}`; });

  // ------------------------------------------------------------ misc wiring
  $("#btnFind").addEventListener("click", startSearch);
  $("#btnStop").addEventListener("click", async () => { await api("/api/scrape/stop", { method: "POST" }); toast("Stopping after current requests..."); });
  $("#btnSave").addEventListener("click", saveProfile);
  $("#btnDetails").addEventListener("click", () => {
    S.showDetails = $("#progressPanel").classList.contains("collapsed");
    if (S.lastStatus) renderStatus(S.lastStatus);
  });
  $("#btnLog").addEventListener("click", () => {
    $("#progressPanel").classList.remove("collapsed");
    const hidden = $("#logBox").classList.toggle("hidden");
    $("#btnLog").textContent = hidden ? "Show log" : "Hide log";
  });
  $("#btnClear").addEventListener("click", async () => {
    if (!confirm("Delete all stored jobs except the ones you saved or applied to?")) return;
    await api("/api/jobs?keep_tracked=true", { method: "DELETE" });
    toast("Stored jobs cleared."); refilter();
  });

  const dz = $("#drop");
  $("#resumeFile").addEventListener("change", (e) => uploadResume(e.target.files[0]));
  ["dragenter", "dragover"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.add("over"); }));
  ["dragleave", "drop"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.remove("over"); }));
  dz.addEventListener("drop", (e) => uploadResume(e.dataTransfer.files[0]));

  window.addEventListener("beforeunload", (e) => { if (S.dirty) { e.preventDefault(); e.returnValue = ""; } });

  // ------------------------------------------------------------ apply assistant
  const AP = { profile: null, ready: false, missing: [], status: null, timer: null, active: false };
  const AP_FIELDS = ["first_name", "last_name", "email", "phone_code", "phone", "city", "country", "linkedin_url", "github_url",
    "portfolio_url", "current_company", "current_title", "years_experience", "notice_period", "current_salary", "expected_salary",
    "work_authorized", "needs_sponsorship", "willing_to_relocate", "remote_ok", "cover_letter", "eeo_gender", "pronouns", "eeo_race",
    "eeo_veteran", "eeo_disability", "how_heard", "resume_choice", "use_ai_answers", "auto_continue"];
  const AP_LABEL = { queued: "Queued", running: "Working", needs_you: "Needs you", submitted: "Submitted", failed: "Failed", skipped: "Skipped" };

  async function loadApplyProfile() {
    const r = await api("/api/apply/profile");
    AP.profile = r.profile; AP.ready = r.ready; AP.missing = r.missing;
    for (const k of AP_FIELDS) {
      const el = $("#ap_" + k); if (!el) continue;
      if (el.type === "checkbox") el.checked = !!r.profile[k]; else el.value = r.profile[k] ?? "";
    }
    renderApplyReady();
  }
  function renderApplyReady() {
    const st = $("#applyState");
    st.textContent = AP.ready ? "Ready" : "Add " + AP.missing.join(", ");
    st.className = "pill " + (AP.ready ? "High" : "src");
    $("#applyNavDot").classList.toggle("hidden", AP.ready);
  }
  function applyPayload() {
    const out = {};
    for (const k of AP_FIELDS) { const el = $("#ap_" + k); if (el) out[k] = el.type === "checkbox" ? el.checked : el.value; }
    return out;
  }
  async function saveApplyProfile(quiet = false) {
    try {
      const r = await api("/api/apply/profile", { method: "PUT", json: applyPayload() });
      AP.profile = r.profile; AP.ready = r.ready; AP.missing = r.missing;
      renderApplyReady();
      if (!quiet) toast(r.ready ? "Application profile saved." : "Saved. Still missing: " + r.missing.join(", "));
      return r.ready;
    } catch (e) { toast("Could not save: " + e.message, true); return false; }
  }
  $("#btnApplySave").addEventListener("click", () => saveApplyProfile());
  $("#panelApply").addEventListener("click", async (e) => {
    const b = e.target.closest("[data-login]");
    if (!b) return;
    try {
      await api("/api/apply/login", { method: "POST", json: { site: b.dataset.login } });
      toast("A browser window is opening. Log in there; the session is remembered.");
      startApplyPoll();
    } catch (err) { toast(err.message, true); }
  });

  async function loadAnswers() {
    const r = await api("/api/apply/answers");
    $("#answersCount").textContent = r.items.length ? `(${r.items.length})` : "";
    $("#answersList").innerHTML = r.items.map((a) => `<div class="ans"><div><b>${esc(a.question)}</b><div class="muted small">${esc(a.answer)}</div></div>
      <button class="btn small ghost icon" data-del="${a.id}" title="Delete">${icon("trash")}</button></div>`).join("") || '<div class="muted small">No saved answers yet.</div>';
  }
  $("#answersList").addEventListener("click", async (e) => {
    const b = e.target.closest("[data-del]"); if (!b) return;
    await api(`/api/apply/answers/${b.dataset.del}`, { method: "DELETE" }); loadAnswers();
  });
  $("#btnAnsAdd").addEventListener("click", async () => {
    const q = $("#ansQ").value.trim(), a = $("#ansA").value.trim();
    if (!q || !a) return toast("Enter both a question and an answer.", true);
    try { await api("/api/apply/answers", { method: "POST", json: { question: q, answer: a } }); $("#ansQ").value = ""; $("#ansA").value = ""; loadAnswers(); }
    catch (err) { toast(err.message, true); }
  });

  // selection
  function renderSelBar() {
    const n = S.selected.size;
    $("#selBar").classList.toggle("hidden", !n);
    $("#selCount").textContent = n;
  }
  $("#jobs").addEventListener("change", (e) => {
    const cb = e.target.closest(".job-sel"); if (!cb) return;
    const card = cb.closest(".job"); const id = +card.dataset.id;
    if (cb.checked) S.selected.add(id); else S.selected.delete(id);
    card.classList.toggle("selected", cb.checked);
    renderSelBar();
  });
  $("#btnSelAll").addEventListener("click", () => { S.items.forEach((j) => S.selected.add(j.id)); renderJobs(); renderSelBar(); });
  $("#btnSelNone").addEventListener("click", () => { S.selected.clear(); renderJobs(); renderSelBar(); });
  $("#btnApplySel").addEventListener("click", () => applyJobs([...S.selected]));
  $("#btnApplyShown").addEventListener("click", () => {
    if (!S.items.length) return toast("No jobs listed.", true);
    if (!confirm(`Queue all ${S.items.length} listed jobs for auto apply?`)) return;
    applyJobs(S.items.map((j) => j.id));
  });
  $("#btnTailorSel").addEventListener("click", async () => {
    const ids = [...S.selected];
    if (!ids.length) return;
    if (!AI.settings || !AI.settings.ready) { toast("Add an API key under AI settings first.", true); showPanel("ai"); return; }
    if (!confirm(`Tailor your resume for ${ids.length} job(s) one after another? Each takes 20 to 60 seconds.`)) return;
    let ok = 0;
    for (const id of ids) {
      try { await api(`/api/jobs/${id}/tailor`, { method: "POST", json: {} }); ok++; toast(`Tailored ${ok} of ${ids.length}`); }
      catch (e) { toast("Tailoring failed for one job: " + e.message, true); }
    }
    loadJobs(true);
  });

  async function applyJobs(ids) {
    ids = [...new Set(ids)].filter(Boolean);
    if (!ids.length) return;
    if (!S.profile || !S.profile.has_resume) { toast("Upload your resume first.", true); showPanel("profile"); return; }
    if (!AP.ready) {
      if (!(await saveApplyProfile(true))) { toast("Fill in your application profile first: " + AP.missing.join(", "), true); showPanel("apply"); return; }
    }
    if (AP.profile && AP.profile.use_ai_answers && !(AI.settings && AI.settings.ready)) {
      toast("AI answers are on but no API key is saved. Unknown questions will wait for you.", false);
    }
    try {
      const r = await api("/api/apply/start", { method: "POST", json: { job_ids: ids } });
      toast(r.queued ? `${r.queued} job(s) queued. A browser window will open.` : "Those jobs are already queued.");
      S.selected.clear(); renderSelBar();
      renderApply(r); startApplyPoll(); loadJobs(true);
      $("#applyPanel").scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (e) { toast(e.message, true); }
  }

  function startApplyPoll() {
    clearTimeout(AP.timer);
    AP.active = true;
    pollApply();
  }
  async function pollApply() {
    clearTimeout(AP.timer);
    try {
      const st = await api("/api/apply/status");
      renderApply(st);
      const busy = st.running || st.login_mode;
      if (busy) AP.timer = setTimeout(pollApply, 1500);
      else if (AP.active) { AP.active = false; loadJobs(true); loadAnswers(); }
    } catch (e) { AP.timer = setTimeout(pollApply, 4000); }
  }

  function renderApply(st) {
    AP.status = st;
    const panel = $("#applyPanel");
    const queue = st.queue || [];
    const cur = st.current;
    if (!queue.length && !cur && !st.login_mode) { panel.classList.add("hidden"); return; }
    panel.classList.remove("hidden");
    const counts = {};
    queue.forEach((a) => { counts[a.status] = (counts[a.status] || 0) + 1; });
    $("#applySummary").textContent = (st.running ? "Browser open · " : "Browser closed · ") +
      Object.entries(counts).map(([k, v]) => `${v} ${AP_LABEL[k] || k}`).join(" · ");
    $("#btnApplyStop").classList.toggle("hidden", !st.running && !st.login_mode);
    const box = $("#applyCurrent");
    if (cur) {
      const qs = (cur.questions || []).map((q) => `<div class="aq ${q.uncertain ? "unsure" : ""}">
          <div class="aq-l"><b>${esc(q.label)}</b> <span class="pill src">${q.source === "bank" ? "saved answer" : q.source === "ai" ? "AI draft" : q.source === "user" ? "yours" : "no answer"}</span>${q.required ? '<span class="muted small"> required</span>' : ""}${q.filled === false ? '<span class="muted small"> · could not fill, type it in the browser</span>' : ""}</div>
          ${q.options && q.options.length ? `<select class="aq-a" data-q="${esc(q.id)}"><option value="">(choose)</option>${q.options.map((o) => `<option ${o === q.answer ? "selected" : ""}>${esc(o)}</option>`).join("")}</select>`
                                            : `<textarea class="aq-a" data-q="${esc(q.id)}" rows="${(q.answer || "").length > 90 ? 3 : 1}">${esc(q.answer || "")}</textarea>`}
          <div class="aq-b"><label class="small"><input type="checkbox" class="aq-rem" checked> remember</label><button class="btn small" data-use="${esc(q.id)}">Use this answer</button></div>
        </div>`).join("");
      box.innerHTML = `<div class="ap-cur ${esc(cur.status)}">
        <div class="ap-head">
          <div><b>${esc(cur.title)}</b> <span class="muted">at ${esc(cur.company || "")}</span>
            ${cur.portal ? `<span class="pill src">${esc(cur.portal)}</span>` : ""}
            <span class="pill ap-${esc(cur.status)}">${AP_LABEL[cur.status] || esc(cur.status)}</span></div>
          <div class="row">
            <button class="btn small" data-cmd="continue" title="I did what you asked in the browser">Continue</button>
            <button class="btn small success" data-cmd="submitted">${icon("check")}I submitted it</button>
            <button class="btn small ghost" data-cmd="skip">Skip</button>
          </div>
        </div>
        <div class="ap-msg ${cur.status === "needs_you" ? "warn" : ""}">${cur.status === "running" ? `<span class="ico spin small">${ICONS.spinner}</span>` : ""}${esc(cur.message || "")}</div>
        ${cur.filled && cur.filled.length ? `<div class="muted small">Filled: ${cur.filled.slice(0, 12).map(esc).join(", ")}${cur.filled.length > 12 ? ` and ${cur.filled.length - 12} more` : ""}</div>` : ""}
        ${qs ? `<div class="aq-list"><div class="muted small" style="margin:8px 0 4px">Screening questions. Check each answer; edit and click Use to change it in the form.</div>${qs}</div>` : ""}
      </div>`;
    } else if (st.login_mode) {
      box.innerHTML = `<div class="ap-cur needs_you"><div class="ap-head"><div><b>Browser open for login</b></div>
        <div class="row"><button class="btn small" data-cmd="close_login">Done, close it</button></div></div>
        <div class="ap-msg warn">Log in to the portal in the browser window. Your session is saved for future applications.</div></div>`;
    } else {
      box.innerHTML = "";
    }
    const rows = queue.map((a) => `<div class="apq ${esc(a.status)}">
        <span class="pill ap-${esc(a.status)}">${AP_LABEL[a.status] || esc(a.status)}</span>
        <div class="apq-main"><b>${esc(a.title || "Job " + a.job_id)}</b> <span class="muted">${esc(a.company || "")}</span>
          ${a.portal ? `<span class="pill src">${esc(a.portal)}</span>` : ""}
          ${a.message && a.status !== "queued" ? `<div class="muted small">${esc(a.message)}</div>` : ""}
          ${a.screenshot ? `<a class="small" href="/api/apply/screenshot/${esc(a.screenshot)}" target="_blank">Screenshot</a>` : ""}</div>
        ${a.url ? `<a class="btn small ghost" href="${esc(safeUrl(a.url))}" target="_blank" rel="noopener">${icon("ext")}</a>` : ""}
      </div>`).join("");
    $("#applyQueue").innerHTML = rows;
    $("#lastRun").textContent = st.running && cur ? `Applying: ${cur.title}` : $("#lastRun").textContent;
  }

  $("#applyCurrent").addEventListener("click", async (e) => {
    const c = e.target.closest("[data-cmd]");
    if (c) {
      try { await api("/api/apply/command", { method: "POST", json: { action: c.dataset.cmd } }); }
      catch (err) { toast(err.message, true); }
      return;
    }
    const u = e.target.closest("[data-use]");
    if (u) {
      const wrap = u.closest(".aq");
      const ans = wrap.querySelector(".aq-a").value.trim();
      const rem = wrap.querySelector(".aq-rem").checked;
      try {
        await api("/api/apply/command", { method: "POST", json: { action: "answer", id: u.dataset.use, answer: ans, remember: rem } });
        toast("Answer sent to the form.");
      } catch (err) { toast(err.message, true); }
    }
  });
  $("#btnApplyStop").addEventListener("click", async () => {
    if (!confirm("Stop the apply assistant and close its browser? Queued jobs are cancelled.")) return;
    await api("/api/apply/stop", { method: "POST" }); toast("Stopping..."); startApplyPoll();
  });
  $("#btnApplyClear").addEventListener("click", async () => { await api("/api/apply/history", { method: "DELETE" }); pollApply(); });

  // ------------------------------------------------------------ init
  async function init() {
    applyTheme(store.get("theme", null));
    paintIcons();
    syncFilterUI();
    showPanel(store.get("panel", "profile"));
    const [meta, profile, st] = await Promise.all([api("/api/meta"), api("/api/profile"), api("/api/scrape/status"),
      loadAiSettings().catch((e) => toast("AI settings could not load: " + e.message, true)),
      loadApplyProfile().catch(() => null), loadAnswers().catch(() => null)]);
    pollApply();
    S.meta = meta;
    meta.sources.forEach((s) => { S.sourceLabel[s.key] = s.label; });
    $("#skillList").innerHTML = meta.skills.map((s) => `<option value="${esc(s)}">`).join("");
    $("#roleList").innerHTML = meta.roles.map((s) => `<option value="${esc(s)}">`).join("");
    S.draft = JSON.parse(JSON.stringify(profile));
    skillsEd = chipEditor("skills", "#skillsChips", "#skillInput", { canonical: true });
    rolesEd = chipEditor("target_roles", "#rolesChips", "#roleInput");
    locEd = chipEditor("search_locations", "#locChips", "#locInput");
    fillProfile(profile);
    bindField("#pName", "name");
    bindField("#pTitle", "current_title");
    bindField("#pYears", "years_experience", num);
    bindField("#pCountry", "country");
    bindField("#pDays", "posted_within_days", Number);
    bindField("#pRemote", "remote_ok");
    bindField("#pHeadless", "naukri_headless");
    bindField("#aQueries", "max_queries", Number);
    bindField("#aMin", "min_match_to_show", Number);
    bindField("#aLiPages", "linkedin_pages", Number);
    bindField("#aLiDetails", "linkedin_details", Number);
    bindField("#aNkPages", "naukri_pages", Number);
    if (!store.get("filters", null)) { S.filters.min = profile.min_match_to_show ?? 35; syncFilterUI(); }
    renderStatus(st);
    if (st.running) { S.running = true; setRunningUI(true); poll(); }
    else if (!Object.keys(st.sources || {}).length && !st.last_run) $("#progressPanel").classList.add("hidden");
    else setRunningUI(false);
    loadJobs();
  }
  init().catch((e) => toast("Failed to start: " + e.message, true));
})();

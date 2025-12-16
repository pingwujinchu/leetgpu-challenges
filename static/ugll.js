const $ = (id) => /** @type {HTMLElement} */ (document.getElementById(id));

const AUTH_TOKEN_KEY = "ugll_token";

const state = {
  data: null,
  selected: { key: null, fw: null },
  auth: {
    token: localStorage.getItem(AUTH_TOKEN_KEY),
    me: null,
    jobs: [],
    selectedJobId: null,
    lastJobsFetchMs: 0,
  },
  editor: {
    starter: "",
    touched: false,
  },
  filters: {
    gpu: "any",
    q: "",
    diff: { easy: true, medium: true, hard: true },
    fw: { cuda: true, triton: true, cute: true, cutile: true },
  },
};

function normalize(s) {
  return String(s ?? "").trim().toLowerCase();
}

function challengeKey(c) {
  return `${c.difficulty}/${c.slug}`;
}

function badge(label, variant = "pill") {
  const span = document.createElement("span");
  span.className = `pill ${variant}`;
  span.textContent = label;
  return span;
}

function setMeta(text) {
  $("listMeta").textContent = text;
}

function setAuthMsg(text) {
  $("authMsg").textContent = text || "";
}

function setSubmitMsg(text) {
  $("submitMsg").textContent = text || "";
}

function setAuthStatus(text) {
  $("authStatus").textContent = text || "未登录";
}

function authHeader() {
  return state.auth.token ? { Authorization: `Bearer ${state.auth.token}` } : {};
}

function formatApiError(res, body) {
  // FastAPI validation errors: { detail: [{ loc: [...], msg: "...", type: "..." }, ...] }
  if (body && typeof body === "object" && Array.isArray(body.detail)) {
    const items = body.detail
      .map((e) => {
        const loc = Array.isArray(e.loc) ? e.loc.filter((x) => x !== "body") : [];
        const where = loc.length ? loc.join(".") : "";
        const msg = e.msg ? String(e.msg) : "Invalid request";
        return where ? `${where}: ${msg}` : msg;
      })
      .filter(Boolean);
    if (items.length) return items.join("；");
  }
  if (body?.detail) return typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
  if (typeof body === "string" && body) return body;
  return `HTTP ${res?.status ?? ""}`.trim();
}

async function apiFetch(path, opts = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...authHeader(),
    ...(opts.headers || {}),
  };
  const res = await fetch(path, { ...opts, headers, credentials: "same-origin" });
  const ct = res.headers.get("content-type") || "";
  const body = ct.includes("application/json") ? await res.json().catch(() => null) : await res.text().catch(() => "");
  if (!res.ok) {
    throw new Error(formatApiError(res, body));
  }
  return body;
}

async function loadMe() {
  try {
    state.auth.me = await apiFetch("/me", { method: "GET" });
    return state.auth.me;
  } catch (e) {
    // Token expired or invalid.
    state.auth.token = null;
    localStorage.removeItem(AUTH_TOKEN_KEY);
    state.auth.me = null;
    return null;
  }
}

function renderAuthUI() {
  const me = state.auth.me;
  if (me) {
    setAuthStatus(`已登录：${me.tenant}/${me.username} (${me.role})`);
    $("logoutBtn").classList.remove("hidden");
  } else {
    setAuthStatus("未登录");
    $("logoutBtn").classList.add("hidden");
  }
}

function parseHash() {
  // Format: #/difficulty/slug?fw=cuda&gpu=nvidia
  const hash = window.location.hash || "";
  if (!hash.startsWith("#/")) return { key: null, fw: null, gpu: null };
  const rest = hash.slice(2);
  const [pathPart, queryPart] = rest.split("?", 2);
  const [difficulty, slug] = pathPart.split("/", 2);
  const params = new URLSearchParams(queryPart || "");
  return {
    key: difficulty && slug ? `${difficulty}/${slug}` : null,
    fw: params.get("fw"),
    gpu: params.get("gpu"),
  };
}

function updateHash({ key, fw, gpu }) {
  if (!key) return;
  const params = new URLSearchParams();
  if (fw) params.set("fw", fw);
  if (gpu && gpu !== "any") params.set("gpu", gpu);
  const q = params.toString();
  window.location.hash = `#/${key}${q ? `?${q}` : ""}`;
}

function gpuLabel(v) {
  return v === "nvidia"
    ? "NVIDIA"
    : v === "amd"
      ? "AMD"
      : v === "intel"
        ? "Intel"
        : v === "apple"
          ? "Apple (Metal)"
          : "Any";
}

function vendorPill(v) {
  if (v === "nvidia") return badge("NVIDIA", "pill--ok");
  if (v === "amd") return badge("AMD", "pill--accent");
  if (v === "intel") return badge("Intel", "pill--warn");
  if (v === "apple") return badge("Apple (Metal)", "pill--ok");
  return badge(v, "pill");
}

function difficultyPill(d) {
  if (d === "easy") return badge("easy", "pill--ok");
  if (d === "medium") return badge("medium", "pill--accent");
  if (d === "hard") return badge("hard", "pill--bad");
  return badge(d, "pill");
}

function bestFrameworkForChallenge(c, desiredGpu, desiredFw) {
  const exists = c.frameworks.filter((f) => f.exists);
  if (exists.length === 0) return null;

  const gpuFiltered =
    desiredGpu && desiredGpu !== "any"
      ? exists.filter((f) => (f.gpu_vendors || []).includes(desiredGpu))
      : exists;
  const candidates = gpuFiltered.length ? gpuFiltered : exists;

  if (desiredFw) {
    const hit = candidates.find((f) => f.id === desiredFw);
    if (hit) return hit.id;
  }
  return candidates[0].id;
}

function passesFilters(c) {
  if (!state.filters.diff[c.difficulty]) return false;

  // GPU vendor filter: challenge is shown if any existing framework can target that vendor.
  if (state.filters.gpu !== "any") {
    const ok = (c.frameworks || []).some(
      (f) => f.exists && Array.isArray(f.gpu_vendors) && f.gpu_vendors.includes(state.filters.gpu),
    );
    if (!ok) return false;
  }

  // Framework filter: shown if any selected framework exists for that challenge.
  const fwSelected = Object.entries(state.filters.fw)
    .filter(([, v]) => v)
    .map(([k]) => k);
  if (fwSelected.length) {
    const ok = fwSelected.some((id) => (c.frameworks || []).some((f) => f.exists && f.id === id));
    if (!ok) return false;
  }

  const q = normalize(state.filters.q);
  if (!q) return true;

  const hay = normalize(`${c.id ?? ""} ${c.slug ?? ""} ${c.title ?? ""} ${c.difficulty ?? ""}`);
  return hay.includes(q);
}

function renderList() {
  const list = $("challengeList");
  list.innerHTML = "";

  const challenges = state.data?.challenges ?? [];
  const filtered = challenges.filter(passesFilters);

  setMeta(`${filtered.length} / ${challenges.length} 个题目（GPU: ${gpuLabel(state.filters.gpu)}）`);

  if (filtered.length === 0) {
    const div = document.createElement("div");
    div.className = "meta";
    div.textContent = "没有匹配的题目。可以尝试放宽 GPU/语言筛选。";
    list.appendChild(div);
    return;
  }

  for (const c of filtered) {
    const key = challengeKey(c);
    const item = document.createElement("div");
    item.className = `item ${state.selected.key === key ? "active" : ""}`;
    item.onclick = () => {
      const fw = bestFrameworkForChallenge(c, state.filters.gpu, state.selected.fw);
      selectChallenge(key, fw);
    };

    const top = document.createElement("div");
    top.className = "item__top";
    const title = document.createElement("div");
    title.className = "item__title";
    title.textContent = `${c.id ?? "?"}. ${c.title ?? c.slug}`;
    top.appendChild(title);
    top.appendChild(difficultyPill(c.difficulty));

    const sub = document.createElement("div");
    sub.className = "item__sub";

    const vendors = Array.isArray(c.gpu_vendors) ? c.gpu_vendors : [];
    for (const v of vendors.slice(0, 3)) sub.appendChild(vendorPill(v));

    const existingFw = (c.frameworks || []).filter((f) => f.exists).map((f) => f.label);
    sub.appendChild(badge(existingFw.length ? existingFw.join(" / ") : "No starter", existingFw.length ? "pill--accent" : "pill--bad"));

    item.appendChild(top);
    item.appendChild(sub);
    list.appendChild(item);
  }
}

function setDetailVisible(visible) {
  $("emptyState").classList.toggle("hidden", visible);
  $("detail").classList.toggle("hidden", !visible);
}

function renderBadges(c, fwId) {
  const wrap = $("detailBadges");
  wrap.innerHTML = "";
  wrap.appendChild(difficultyPill(c.difficulty));

  if (c.access_tier) wrap.appendChild(badge(`tier: ${c.access_tier}`, "pill"));
  if (typeof c.num_gpus === "number") wrap.appendChild(badge(`num_gpus: ${c.num_gpus}`, "pill"));

  const fw = (c.frameworks || []).find((f) => f.id === fwId) || null;
  if (fw?.exists) wrap.appendChild(badge(`fw: ${fw.label}`, "pill--ok"));
  else if (fwId) wrap.appendChild(badge(`fw: ${fwId} (missing)`, "pill--warn"));

  const vendors = Array.isArray(c.gpu_vendors) ? c.gpu_vendors : [];
  for (const v of vendors) wrap.appendChild(vendorPill(v));
}

function renderTabs(c, selectedFw) {
  const tabs = $("fwTabs");
  tabs.innerHTML = "";
  for (const f of c.frameworks || []) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `tab ${f.id === selectedFw ? "active" : ""} ${f.exists ? "" : "disabled"}`;
    btn.textContent = f.label;
    btn.onclick = () => {
      if (!f.exists) return;
      selectChallenge(challengeKey(c), f.id);
    };
    tabs.appendChild(btn);
  }
}

async function loadText(path) {
  const res = await fetch(path, { cache: "no-store", credentials: "same-origin" });
  if (!res.ok) throw new Error(`HTTP ${res.status} for ${path}`);
  return await res.text();
}

async function loadStarterFor(c, fwId) {
  const fw = (c.frameworks || []).find((f) => f.id === fwId) || null;
  if (!fw) {
    state.editor.starter = "";
    return { ok: false, text: "未选择语言/框架。", fw: null };
  }
  if (!fw.exists) {
    state.editor.starter = "";
    const msg =
      fw.id === "cutile"
        ? `该题目没有 ${fw.label} starter（缺少：${fw.path}）。提示：已预留 CuTile-Python 入口，未来补文件即可。`
        : `该题目没有 ${fw.label} starter（缺少：${fw.path}）。`;
    return { ok: false, text: msg, fw };
  }
  try {
    const text = await loadText(fw.path);
    state.editor.starter = text;
    return { ok: true, text, fw };
  } catch (e) {
    state.editor.starter = "";
    const msg = String(e?.message || e);
    if (msg.includes("HTTP 401")) return { ok: false, text: "请先登录后再查看题面与 Starter。", fw };
    return { ok: false, text: `Starter 加载失败：${msg}`, fw };
  }
}

function renderDetail(c, fwId) {
  setDetailVisible(true);
  $("detailTitle").textContent = `${c.id ?? "?"}. ${c.title ?? c.slug}`;

  $("openChallengePy").href = c.paths?.challenge_py ?? "#";
  $("openChallengeHtml").href = c.paths?.challenge_html ?? "#";

  const frame = /** @type {HTMLIFrameElement} */ ($("problemFrame"));
  frame.src = c.paths?.challenge_html ?? "";

  renderTabs(c, fwId);
  renderBadges(c, fwId);

  // Default editor content: only autofill when user hasn't edited.
  const editor = /** @type {HTMLTextAreaElement} */ ($("codeEditor"));
  editor.placeholder = "选择一个语言/框架 tab…";
  setSubmitMsg("");
  loadStarterFor(c, fwId).then((r) => {
    if (!state.editor.touched || !editor.value) {
      editor.value = r.ok ? r.text : (r.text || "");
      state.editor.touched = false;
    }
  });
}

function selectChallenge(key, fwId) {
  if (!state.auth.me) {
    setAuthMsg("请先登录后再做题（查看题面/Starter）。");
    setDetailVisible(false);
    return;
  }
  const c = (state.data?.challenges || []).find((x) => challengeKey(x) === key);
  if (!c) return;

  const picked = bestFrameworkForChallenge(c, state.filters.gpu, fwId) || fwId || null;
  state.selected = { key, fw: picked };
  updateHash({ key, fw: picked, gpu: state.filters.gpu });
  renderList();
  renderDetail(c, picked);
}

function wireControls() {
  const gpuSelect = /** @type {HTMLSelectElement} */ ($("gpuSelect"));
  const searchInput = /** @type {HTMLInputElement} */ ($("searchInput"));

  gpuSelect.onchange = () => {
    state.filters.gpu = gpuSelect.value;
    // If a challenge is selected, re-pick best framework under new GPU view.
    if (state.selected.key) {
      const c = (state.data?.challenges || []).find((x) => challengeKey(x) === state.selected.key);
      if (c) selectChallenge(state.selected.key, state.selected.fw);
    } else {
      renderList();
    }
  };

  searchInput.oninput = () => {
    state.filters.q = searchInput.value;
    renderList();
  };

  const diffMap = { diffEasy: "easy", diffMedium: "medium", diffHard: "hard" };
  for (const [id, diff] of Object.entries(diffMap)) {
    /** @type {HTMLInputElement} */ ($(id)).onchange = (e) => {
      state.filters.diff[diff] = e.target.checked;
      renderList();
    };
  }

  const fwMap = { fwCuda: "cuda", fwTriton: "triton", fwCute: "cute", fwCutile: "cutile" };
  for (const [id, fw] of Object.entries(fwMap)) {
    /** @type {HTMLInputElement} */ ($(id)).onchange = (e) => {
      state.filters.fw[fw] = e.target.checked;
      renderList();
    };
  }

  const editor = /** @type {HTMLTextAreaElement} */ ($("codeEditor"));
  editor.oninput = () => {
    state.editor.touched = true;
  };

  $("logoutBtn").onclick = () => {
    // Best-effort server-side logout (clears httpOnly cookie).
    apiFetch("/auth/logout", { method: "POST" }).catch(() => null);
    state.auth.token = null;
    state.auth.me = null;
    localStorage.removeItem(AUTH_TOKEN_KEY);
    setAuthMsg("");
    renderAuthUI();
  };

  $("loginBtn").onclick = async () => {
    setAuthMsg("");
    try {
      const tenant = /** @type {HTMLInputElement} */ ($("tenantInput")).value;
      const username = /** @type {HTMLInputElement} */ ($("usernameInput")).value;
      const password = /** @type {HTMLInputElement} */ ($("passwordInput")).value;
      const tok = await apiFetch("/auth/login", { method: "POST", body: JSON.stringify({ tenant, username, password }) });
      state.auth.token = tok.access_token;
      localStorage.setItem(AUTH_TOKEN_KEY, state.auth.token);
      await loadMe();
      renderAuthUI();
      setAuthMsg("登录成功");
      refreshJobs(true);
    } catch (e) {
      setAuthMsg(`登录失败：${String(e?.message || e)}`);
    }
  };

  $("registerBtn").onclick = async () => {
    setAuthMsg("");
    try {
      const tenant = /** @type {HTMLInputElement} */ ($("tenantInput")).value.trim();
      const username = /** @type {HTMLInputElement} */ ($("usernameInput")).value.trim();
      const password = /** @type {HTMLInputElement} */ ($("passwordInput")).value;
      if (!tenant) throw new Error("tenant 不能为空");
      if (username.length < 3) throw new Error("username 至少 3 位");
      if ((password || "").length < 8) throw new Error("password 至少 8 位");
      await apiFetch("/auth/register", { method: "POST", body: JSON.stringify({ tenant, username, password }) });
      setAuthMsg("注册成功，请点击登录");
    } catch (e) {
      setAuthMsg(`注册失败：${String(e?.message || e)}`);
    }
  };

  $("resetToStarter").onclick = async () => {
    if (!state.selected.key || !state.selected.fw) return;
    const c = (state.data?.challenges || []).find((x) => challengeKey(x) === state.selected.key);
    if (!c) return;
    const r = await loadStarterFor(c, state.selected.fw);
    editor.value = r.text || "";
    state.editor.touched = false;
  };

  $("submitJob").onclick = async () => {
    setSubmitMsg("");
    if (!state.auth.me && !state.auth.token) {
      setSubmitMsg("请先登录（多租户：tenant/username）。");
      return;
    }
    if (!state.selected.key || !state.selected.fw) {
      setSubmitMsg("请先选择题目与语言/框架。");
      return;
    }
    const source_code = editor.value || "";
    if (!source_code.trim()) {
      setSubmitMsg("代码为空。");
      return;
    }
    const gpu_vendor = state.filters.gpu || "any";
    const gpu_arch = /** @type {HTMLInputElement} */ ($("gpuArchInput")).value || null;
    try {
      const job = await apiFetch("/jobs", {
        method: "POST",
        body: JSON.stringify({
          challenge_key: state.selected.key,
          framework: state.selected.fw,
          gpu_vendor,
          gpu_arch,
          source_code,
        }),
      });
      setSubmitMsg(`已提交任务 #${job.id}（${job.status}）`);
      refreshJobs(true);
    } catch (e) {
      setSubmitMsg(`提交失败：${String(e?.message || e)}`);
    }
  };

  $("refreshJobs").onclick = () => refreshJobs(true);
}

function statusPill(status) {
  if (status === "succeeded") return badge(status, "pill--ok");
  if (status === "failed") return badge(status, "pill--bad");
  if (status === "running") return badge(status, "pill--accent");
  return badge(status, "pill");
}

async function refreshJobs(force = false) {
  if (!state.auth.me && !state.auth.token) return;
  const now = Date.now();
  if (!force && now - state.auth.lastJobsFetchMs < 1500) return;
  state.auth.lastJobsFetchMs = now;
  try {
    const jobs = await apiFetch("/jobs", { method: "GET" });
    state.auth.jobs = Array.isArray(jobs) ? jobs : [];
    renderJobsList();
  } catch (e) {
    // token might have expired
    setSubmitMsg(`拉取任务失败：${String(e?.message || e)}`);
  }
}

function renderJobsList() {
  const wrap = $("jobsList");
  wrap.innerHTML = "";
  if (!state.auth.me) {
    const div = document.createElement("div");
    div.className = "meta";
    div.textContent = "登录后可查看任务列表与日志。";
    wrap.appendChild(div);
    return;
  }
  const jobs = (state.auth.jobs || []).slice(0, 30);
  if (jobs.length === 0) {
    const div = document.createElement("div");
    div.className = "meta";
    div.textContent = "暂无任务。";
    wrap.appendChild(div);
    return;
  }
  for (const j of jobs) {
    const item = document.createElement("div");
    item.className = `jobItem ${state.auth.selectedJobId === j.id ? "active" : ""}`;
    item.onclick = () => selectJob(j.id);
    const top = document.createElement("div");
    top.className = "jobItemTop";
    const left = document.createElement("div");
    const rt = typeof j.runtime_ms === "number" ? ` · ${j.runtime_ms}ms` : "";
    left.textContent = `#${j.id} ${j.challenge_key} · ${j.framework} · ${j.gpu_vendor}${rt}`;
    const st = statusPill(j.status);
    top.appendChild(left);
    top.appendChild(st);
    const small = document.createElement("div");
    small.className = "jobSmall";
    small.textContent = `queued: ${j.queued_at}${j.finished_at ? ` · finished: ${j.finished_at}` : ""}`;
    item.appendChild(top);
    item.appendChild(small);
    wrap.appendChild(item);
  }
}

async function selectJob(jobId) {
  state.auth.selectedJobId = jobId;
  renderJobsList();
  const log = $("jobLog");
  log.textContent = "加载中…";
  try {
    const d = await apiFetch(`/jobs/${jobId}`, { method: "GET" });
    const parts = [];
    parts.push(`job #${d.id} status=${d.status} exit_code=${d.exit_code ?? ""}`);
    if (d.error) parts.push(`\n[error]\n${d.error}`);
    if (d.stdout) parts.push(`\n[stdout]\n${d.stdout}`);
    if (d.stderr) parts.push(`\n[stderr]\n${d.stderr}`);
    log.textContent = parts.join("\n");
  } catch (e) {
    log.textContent = `加载失败：${String(e?.message || e)}`;
  }
}

async function init() {
  wireControls();
  await loadMe();
  renderAuthUI();
  try {
    const raw = await loadText("static/challenges.json");
    state.data = JSON.parse(raw);
  } catch (e) {
    setMeta(`加载 static/challenges.json 失败：${String(e?.message || e)}`);
    return;
  }

  const parsed = parseHash();
  if (parsed.gpu) {
    state.filters.gpu = parsed.gpu;
    /** @type {HTMLSelectElement} */ ($("gpuSelect")).value = parsed.gpu;
  }

  renderList();

  if (parsed.key) {
    selectChallenge(parsed.key, parsed.fw);
  } else {
    setDetailVisible(false);
  }

  // Background polling for jobs (only when logged in).
  setInterval(() => refreshJobs(false), 3000);
}

window.addEventListener("hashchange", () => {
  const parsed = parseHash();
  if (!parsed.key) return;
  if (parsed.gpu) {
    state.filters.gpu = parsed.gpu;
    /** @type {HTMLSelectElement} */ ($("gpuSelect")).value = parsed.gpu;
  }
  selectChallenge(parsed.key, parsed.fw);
});

init();


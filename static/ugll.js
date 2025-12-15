const $ = (id) => /** @type {HTMLElement} */ (document.getElementById(id));

const state = {
  data: null,
  selected: { key: null, fw: null },
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
  return v === "nvidia" ? "NVIDIA" : v === "amd" ? "AMD" : v === "intel" ? "Intel" : "Any";
}

function vendorPill(v) {
  if (v === "nvidia") return badge("NVIDIA", "pill--ok");
  if (v === "amd") return badge("AMD", "pill--accent");
  if (v === "intel") return badge("Intel", "pill--warn");
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
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) throw new Error(`HTTP ${res.status} for ${path}`);
  return await res.text();
}

async function renderCode(c, fwId) {
  const code = $("codeBlock");
  const note = $("codeNote");
  const open = $("openStarterFile");
  const fw = (c.frameworks || []).find((f) => f.id === fwId) || null;

  if (!fw) {
    code.textContent = "未选择语言/框架。";
    note.textContent = "";
    open.href = "#";
    open.classList.add("hidden");
    return;
  }

  open.classList.remove("hidden");
  open.href = fw.path;

  if (!fw.exists) {
    code.textContent = `该题目没有 ${fw.label} starter 模板（当前仓库缺少：${fw.path}）。`;
    note.textContent =
      fw.id === "cutile"
        ? "提示：本仓库暂未提供 CuTile-Python 模板，但网站入口已预留（未来新增 starter 文件即可自动出现）。"
        : "提示：部分题目可能只提供部分框架的 starter。";
    return;
  }

  try {
    code.textContent = "加载中…";
    const text = await loadText(fw.path);
    code.textContent = text;
    note.textContent =
      state.filters.gpu === "any"
        ? "可在顶部选择 GPU 视角（NVIDIA/AMD/Intel）来筛选与默认框架选择。"
        : `当前 GPU 视角：${gpuLabel(state.filters.gpu)}（注意：实际可运行性取决于本地/服务端安装的 CUDA/HIP/驱动与框架版本）。`;
  } catch (e) {
    code.textContent = `加载失败：${String(e?.message || e)}`;
    note.textContent = "如果你是本地直接打开 HTML 文件，请用静态服务器方式访问（否则 fetch 可能被浏览器拦截）。";
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
  renderCode(c, fwId);
}

function selectChallenge(key, fwId) {
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

  $("copyCode").onclick = async () => {
    const text = $("codeBlock").textContent || "";
    try {
      await navigator.clipboard.writeText(text);
      $("copyCode").textContent = "已复制";
      setTimeout(() => ($("copyCode").textContent = "复制"), 900);
    } catch {
      $("copyCode").textContent = "复制失败";
      setTimeout(() => ($("copyCode").textContent = "复制"), 900);
    }
  };
}

async function init() {
  wireControls();
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


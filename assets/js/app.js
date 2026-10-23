const MANIFEST_URL = new URL("../../manifest.json", import.meta.url);

const els = {
  brand: document.querySelector("[data-brand]"),
  nav: document.querySelector("[data-nav]"),
  content: document.querySelector("[data-content]"),
  search: document.querySelector("#memoSearch"),
  searchStatus: document.querySelector("#searchStatus"),
  pack: document.querySelector("[data-pack-download]"),
  sidebarMenu: document.querySelector("#sidebarMenu"),
};

let manifest = null;
let activeId = null;
let renderVersion = 0;
let searchVersion = 0;
let searchTimer;
const cache = new Map();

function listedFiles() {
  return (manifest?.files || []).filter((f) => f.listed !== false);
}

function allFiles() {
  return manifest?.files || [];
}

/** 合集喂 AI 顺序：分身最先，AGENTS 最后；中间按职责域。 */
const PACK_GROUPS = [
  {
    name: "培训",
    ids: ["peixun-guize-sucha", "peixun-qian-guize", "peixun-wancheng-cutongji"],
  },
  {
    name: "资质",
    ids: ["zizhi-daima", "teshu-jichang-zige-daima", "zizhi-luru-jiancha-yutishi"],
  },
  {
    name: "副驾驶与进度",
    ids: ["fujiashi-liuzhuan-gengxin", "yierjian-fujiashi-jindu-gengxin"],
  },
  {
    name: "迎审与规章",
    ids: [
      "jianchadan-shouce-bidui-tianxie",
      "yuedu-feixing-jishu-guanli-shouce",
      "yuedu-feixing-renyuan-xunlian-dagang",
    ],
  },
];

function sectionMarker(file) {
  const title = file.title || file.id || file.path;
  return `===== ${title}（${file.path}） =====`;
}

function packOrderedEntries() {
  const files = allFiles();
  const byId = new Map(files.map((f) => [f.id, f]));
  const used = new Set();
  const entries = [];

  const fenshen = byId.get("fenshen");
  if (fenshen) {
    entries.push({ file: fenshen, group: "身份" });
    used.add("fenshen");
  }

  for (const group of PACK_GROUPS) {
    for (const id of group.ids) {
      const file = byId.get(id);
      if (!file || used.has(id)) continue;
      entries.push({ file, group: group.name });
      used.add(id);
    }
  }

  for (const file of files) {
    if (used.has(file.id) || file.id === "AGENTS") continue;
    entries.push({ file, group: "其他" });
    used.add(file.id);
  }

  const agents = byId.get("AGENTS");
  if (agents) entries.push({ file: agents, group: "纪律" });

  return entries;
}

function stripFrontMatter(raw) {
  if (!raw.startsWith("---")) return raw;
  const end = raw.indexOf("\n---", 3);
  if (end === -1) return raw;
  return raw.slice(end + 4).replace(/^\s+/, "");
}

function normalizeQuery(value) {
  return String(value || "").trim().toLocaleLowerCase("zh-CN");
}

async function fetchText(path) {
  const url = new URL(path, document.baseURI);
  const res = await fetch(url);
  if (!res.ok) throw new Error(`加载失败：${res.status}`);
  return res.text();
}

async function loadRaw(path) {
  const cached = cache.get(path);
  if (cached !== undefined) return cached;

  const request = fetchText(path)
    .then((text) => {
      cache.set(path, text);
      return text;
    })
    .catch((err) => {
      cache.delete(path);
      throw err;
    });

  cache.set(path, request);
  return request;
}

function wrapTables(root) {
  root.querySelectorAll("table").forEach((table) => {
    if (table.parentElement?.classList.contains("table-wrap")) return;
    const wrapper = document.createElement("div");
    wrapper.className = "table-wrap";
    table.parentNode?.insertBefore(wrapper, table);
    wrapper.appendChild(table);
  });
}

function downloadName(file) {
  const title = String(file.title || file.id || "file")
    .replace(/[\\/:*?"<>|]/g, "_")
    .trim() || "file";
  return /\.md$/i.test(title) ? title : `${title}.md`;
}

function remoteSkillUrl(file) {
  const base = String(manifest?.remoteSkillBase || "").replace(/\/?$/, "/");
  const path = String(file.path || "").replace(/^\.\//, "");
  return `${base}${path}`;
}

/** 单篇：给 Agent 联网拉取该 Skill */
function agentFetchPrompt(file) {
  const url = remoteSkillUrl(file);
  const title = file.title || file.id || "Skill";
  return `请阅读 ${url}（皮燕子 Skill：${title}），然后启动本 Skill。`;
}

function triggerDownload(filename, text) {
  const blob = new Blob([text], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

async function copyText(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const area = document.createElement("textarea");
  area.value = text;
  area.setAttribute("readonly", "");
  area.style.position = "fixed";
  area.style.left = "-9999px";
  document.body.appendChild(area);
  area.select();
  document.execCommand("copy");
  area.remove();
}

function closeMobileMenu() {
  if (!els.sidebarMenu || window.matchMedia("(min-width: 768px)").matches) return;
  const collapse = window.bootstrap?.Collapse?.getOrCreateInstance(els.sidebarMenu, {
    toggle: false,
  });
  // Bootstrap 在展开动画中忽略 hide；选择较快时等展开完成再收起。
  if (els.sidebarMenu.classList.contains("collapsing")) {
    els.sidebarMenu.addEventListener("shown.bs.collapse", () => collapse?.hide(), { once: true });
    return;
  }
  collapse?.hide();
}

function syncThemeButtons() {
  if (!window.PiyanziTheme) return;
  const isDark = window.PiyanziTheme.getTheme() === "dark";
  const label = isDark ? "切换到白天模式" : "切换到暗夜模式";
  document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
    button.setAttribute("aria-label", label);
    button.setAttribute("aria-pressed", String(isDark));
    button.title = label;
  });
}

function markActive(id) {
  els.nav.querySelectorAll(".nav-link").forEach((link) => {
    link.classList.toggle("active", link.dataset.id === id);
  });
}

function createNavLink(file, snippet) {
  const link = document.createElement("a");
  link.href = `#${encodeURIComponent(file.id)}`;
  link.className = `nav-link${snippet ? " search-result" : ""}`;
  link.dataset.id = file.id;

  const head = document.createElement("span");
  head.className = "memo-link-head";

  const title = document.createElement("span");
  title.className = snippet ? "search-result-name" : "memo-link-title";
  title.textContent = file.title;
  head.appendChild(title);
  link.appendChild(head);

  if (snippet) {
    const summary = document.createElement("span");
    summary.className = "search-result-snippet";
    summary.textContent = snippet;
    link.appendChild(summary);
  }

  link.addEventListener("click", (event) => {
    event.preventDefault();
    selectFile(file.id);
  });

  return link;
}

function renderFullList() {
  els.nav.replaceChildren();
  for (const file of listedFiles()) {
    els.nav.appendChild(createNavLink(file));
  }
  if (activeId) markActive(activeId);
}

function makeSnippet(markdown, query) {
  const plain = stripFrontMatter(markdown).replace(/\s+/g, " ").trim();
  const lower = plain.toLocaleLowerCase("zh-CN");
  const index = lower.indexOf(query);
  if (index < 0) return "";
  const start = Math.max(0, index - 24);
  const end = Math.min(plain.length, index + query.length + 48);
  return `${start > 0 ? "…" : ""}${plain.slice(start, end)}${end < plain.length ? "…" : ""}`;
}

function highlightContent(query) {
  const q = normalizeQuery(query);
  if (!q) return;

  const nodes = [];
  const walker = document.createTreeWalker(els.content, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      const parent = node.parentElement;
      if (!parent || parent.closest("mark, script, style, .memo-toolbar")) {
        return NodeFilter.FILTER_REJECT;
      }
      return node.nodeValue?.toLocaleLowerCase("zh-CN").includes(q)
        ? NodeFilter.FILTER_ACCEPT
        : NodeFilter.FILTER_REJECT;
    },
  });
  while (walker.nextNode()) nodes.push(walker.currentNode);

  nodes.forEach((node) => {
    const source = node.nodeValue || "";
    const lowerSource = source.toLocaleLowerCase("zh-CN");
    const fragment = document.createDocumentFragment();
    let cursor = 0;
    let matchIndex = lowerSource.indexOf(q);

    while (matchIndex >= 0) {
      fragment.append(source.slice(cursor, matchIndex));
      const mark = document.createElement("mark");
      mark.className = "search-highlight";
      mark.textContent = source.slice(matchIndex, matchIndex + q.length);
      fragment.append(mark);
      cursor = matchIndex + q.length;
      matchIndex = lowerSource.indexOf(q, cursor);
    }
    fragment.append(source.slice(cursor));
    node.replaceWith(fragment);
  });

  els.content.querySelector(".search-highlight")?.scrollIntoView({ block: "center" });
}

function renderToolbar(file, markdown) {
  const toolbar = document.createElement("div");
  toolbar.className = "memo-toolbar";

  const prompt = agentFetchPrompt(file);

  const promptWrap = document.createElement("div");
  promptWrap.className = "memo-agent-prompt";

  const promptField = document.createElement("input");
  promptField.type = "text";
  promptField.className = "memo-agent-prompt-input";
  promptField.readOnly = true;
  promptField.value = prompt;
  promptField.title = "联网拉取本篇 Skill 的一句话指令";
  promptField.addEventListener("focus", () => promptField.select());
  promptField.addEventListener("click", () => promptField.select());

  const copyBtn = document.createElement("button");
  copyBtn.type = "button";
  copyBtn.className = "memo-download-button";
  copyBtn.textContent = "复制";
  copyBtn.title = "复制后粘贴给 Agent，独立启动本篇 Skill";
  copyBtn.addEventListener("click", async () => {
    try {
      await copyText(prompt);
      const prev = copyBtn.textContent;
      copyBtn.textContent = "已复制";
      window.setTimeout(() => {
        copyBtn.textContent = prev;
      }, 1200);
    } catch (err) {
      console.error(err);
      copyBtn.textContent = "复制失败";
      window.setTimeout(() => {
        copyBtn.textContent = "复制";
      }, 1200);
    }
  });

  promptWrap.append(promptField, copyBtn);

  const downloadBtn = document.createElement("button");
  downloadBtn.type = "button";
  downloadBtn.className = "memo-download-button";
  downloadBtn.textContent = "下载 Markdown";
  downloadBtn.addEventListener("click", () => {
    triggerDownload(downloadName(file), markdown);
  });

  toolbar.append(promptWrap, downloadBtn);
  return toolbar;
}

async function openFile(id, searchValue = els.search.value) {
  const version = ++renderVersion;
  const file = listedFiles().find((f) => f.id === id);
  if (!file) {
    els.content.textContent = "没有文件。";
    return;
  }

  activeId = id;
  document.title = `${file.title} - 皮燕子`;
  markActive(id);
  els.content.textContent = "正在加载...";

  try {
    const markdown = await loadRaw(file.path);
    if (version !== renderVersion) return;
    const body = document.createElement("div");
    body.className = "memo-body";
    const html = marked.parse(stripFrontMatter(markdown), {
      gfm: true,
      breaks: false,
    });
    body.innerHTML = DOMPurify.sanitize(html);
    els.content.replaceChildren(renderToolbar(file, markdown), body);
    wrapTables(els.content);
    highlightContent(searchValue);
    history.replaceState(null, "", `#${encodeURIComponent(file.id)}`);
  } catch (err) {
    if (version !== renderVersion) return;
    els.content.textContent = err instanceof Error ? err.message : String(err);
  }
}

function selectFile(id) {
  const nextHash = `#${encodeURIComponent(id)}`;
  if (location.hash === nextHash) {
    void openFile(id);
  } else {
    location.hash = nextHash;
  }
  closeMobileMenu();
}

async function runSearch(value, version) {
  const query = normalizeQuery(value);
  const pool = listedFiles();
  const settled = await Promise.allSettled(
    pool.map(async (file) => ({
      file,
      markdown: await loadRaw(file.path),
    }))
  );
  if (version !== searchVersion) return;
  const sources = settled.filter((r) => r.status === "fulfilled").map((r) => r.value);
  const failed = settled.length - sources.length;
  const failureNote = failed ? `；${failed} 篇加载失败，可重新输入重试` : "";

  const results = [];
  for (const { file, markdown } of sources) {
    const hay = `${file.title}\n${stripFrontMatter(markdown)}`.toLocaleLowerCase("zh-CN");
    if (!hay.includes(query)) continue;
    results.push({ file, snippet: makeSnippet(markdown, query) });
  }

  els.nav.replaceChildren();
  if (!results.length) {
    const empty = document.createElement("div");
    empty.className = "search-empty";
    empty.textContent = sources.length ? "没有命中" : "技能加载失败，请重试";
    els.nav.appendChild(empty);
    els.searchStatus.textContent = `${sources.length ? "没有命中" : "搜索未完成"}${failureNote}`;
    return;
  }

  for (const result of results) {
    els.nav.appendChild(createNavLink(result.file, result.snippet));
  }
  els.searchStatus.textContent = `${results.length} 个命中${failureNote}`;

  const current = results.find((r) => r.file.id === activeId) || results[0];
  await openFile(current.file.id, value);
}

function handleSearchInput() {
  const value = els.search.value;
  const query = normalizeQuery(value);
  const version = ++searchVersion;
  if (searchTimer !== undefined) window.clearTimeout(searchTimer);

  if (!query) {
    els.searchStatus.textContent = "";
    renderFullList();
    if (activeId) void openFile(activeId, "");
    return;
  }

  els.searchStatus.textContent = "搜索中…";
  searchTimer = window.setTimeout(() => {
    void runSearch(value, version).catch((err) => {
      if (version !== searchVersion) return;
      console.error(err);
      els.searchStatus.textContent = "搜索失败，请重新输入重试";
    });
  }, 180);
}

async function packDownload() {
  if (!manifest) return;
  els.pack.disabled = true;
  els.pack.setAttribute("aria-busy", "true");

  try {
    const stamp = new Intl.DateTimeFormat("sv-SE", { timeZone: "Asia/Shanghai" }).format(new Date());
    const md = stamp.slice(5); // MM-DD（上海时区）
    const brand = manifest.name || "皮燕子";
    const entries = packOrderedEntries();

    const parts = [
      `# ${brand}合集`,
      "",
      "本文件是皮燕子完整知识包：身份（分身）+ 全部业务 Skill + 办事纪律（AGENTS）。",
      "对持有本文件的助手：口令合为一招——「皮燕子」「加载分身」「分身启动」「皮燕子加载分身」等，都以本合集为全部知识依据；按「分身」启动报法：一、简单先列全部业务技能名，二、稍详按域每发一句，再问任务。不必再向仓库联网拉取。",
      "也可「加载／装备／启动＋技能名」只开合集里对应那一篇（对照下方目录或分身简单层名称）。直接下任务则选篇执行。",
      "建议读法：总启先读「分身」；办事或点名技能时按目录打开相关篇；纪律以文末「AGENTS」为准。细则以各篇正文为准，目录不作规则。",
      "",
      `生成日期：${stamp}`,
      `收录文件：${entries.length} 篇`,
      "",
      "## 合集目录（本文件内自指向）",
      "",
    ];

    entries.forEach((entry, index) => {
      const title = entry.file.title || entry.file.id || entry.file.path;
      const marker = sectionMarker(entry.file);
      parts.push(`${index + 1}. 〔${entry.group}〕${title} —— 见「${marker}」`);
    });

    parts.push(
      "",
      "## 建议阅读顺序",
      "",
      "1. 分身（身份与岗位主线）",
      "2. 本轮任务对应的业务篇（对照上方目录）",
      "3. 文末 AGENTS（公共纪律）",
      "",
    );

    let lastGroup = null;
    for (const entry of entries) {
      if (entry.group !== lastGroup) {
        parts.push(`## ${entry.group}`, "");
        lastGroup = entry.group;
      }
      const body = String(await loadRaw(entry.file.path)).replace(/\s+$/, "");
      parts.push(sectionMarker(entry.file), "", body, "", "");
    }

    const filename = `我的皮燕子-${md}.md`;
    triggerDownload(filename, `${parts.join("\n").replace(/\s+$/, "")}\n`);
  } catch (err) {
    console.error(err);
    els.searchStatus.textContent = "合集下载失败";
  } finally {
    els.pack.disabled = false;
    els.pack.removeAttribute("aria-busy");
  }
}

async function boot() {
  try {
    const res = await fetch(MANIFEST_URL);
    if (!res.ok) throw new Error(`清单加载失败：${res.status}`);
    manifest = await res.json();
    els.brand.textContent = manifest.name || "皮燕子";
    renderFullList();

    const hash = decodeURIComponent(location.hash.replace(/^#/, ""));
    const first = listedFiles()[0];
    const target = listedFiles().find((f) => f.id === hash)?.id || first?.id;
    if (target) await openFile(target);
    else els.content.textContent = "没有文件。";
  } catch (err) {
    els.content.textContent = err instanceof Error ? err.message : String(err);
  }
}

document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
  button.addEventListener("click", () => {
    window.PiyanziTheme?.toggleTheme();
  });
});
window.addEventListener("piyanzi:themechange", syncThemeButtons);
syncThemeButtons();

els.pack.addEventListener("click", () => {
  void packDownload();
});
els.search.addEventListener("input", handleSearchInput);
window.addEventListener("hashchange", () => {
  const id = decodeURIComponent(location.hash.replace(/^#/, ""));
  if (id && id !== activeId) void openFile(id, els.search.value);
});

boot();

import { validateManifest, listedFiles as catalogFiles, resourcePaths } from "./catalog.mjs";
import { localPackPrompt, buildSkillMarkdown, buildPackMarkdown, buildHistoryMarkdown } from "./knowledge-pack.mjs";

const MANIFEST_URL = new URL("../../manifest.json", import.meta.url);

const els = {
  brand: document.querySelector("[data-brand]"),
  nav: document.querySelector("[data-nav]"),
  content: document.querySelector("[data-content]"),
  status: document.querySelector("[data-status]"),
  packPrompt: document.querySelector("[data-pack-prompt]"),
  pack: document.querySelector("[data-pack-download]"),
  historyPack: document.querySelector("[data-history-download]"),
  packCopy: document.querySelector("[data-pack-copy]"),
  sidebarMenu: document.querySelector("#sidebarMenu"),
};

let manifest = null;
let activeId = null;
let renderVersion = 0;
const cache = new Map();

function listedFiles() {
  return manifest ? catalogFiles(manifest) : [];
}

function stripFrontMatter(raw) {
  if (!raw.startsWith("---")) return raw;
  const end = raw.indexOf("\n---", 3);
  if (end === -1) return raw;
  return raw.slice(end + 4).replace(/^\s+/, "");
}

function setStatus(text) {
  if (els.status) els.status.textContent = text || "";
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

async function flashButton(button, okText, failText, restore) {
  const prev = restore || button.textContent;
  try {
    button.textContent = okText;
  } catch {
    button.textContent = failText;
  }
  window.setTimeout(() => {
    button.textContent = prev;
  }, 1200);
}

function closeMobileMenu() {
  if (!els.sidebarMenu || window.matchMedia("(min-width: 768px)").matches) return;
  const collapse = window.bootstrap?.Collapse?.getOrCreateInstance(els.sidebarMenu, {
    toggle: false,
  });
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

function createNavLink(file) {
  const link = document.createElement("a");
  link.href = `#${encodeURIComponent(file.id)}`;
  link.className = "nav-link";
  link.dataset.id = file.id;

  const head = document.createElement("span");
  head.className = "memo-link-head";
  const title = document.createElement("span");
  title.className = "memo-link-title";
  title.textContent = file.title;
  head.appendChild(title);
  link.appendChild(head);

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

function renderResources(file) {
  const paths = resourcePaths([file]);
  if (!paths.length) return null;
  const section = document.createElement("details");
  const title = document.createElement("summary");
  title.textContent = "配套资源";
  const list = document.createElement("ul");
  for (const path of paths) {
    const item = document.createElement("li");
    const link = document.createElement("a");
    link.href = new URL(path, document.baseURI).href;
    link.textContent = path;
    link.download = path.split("/").at(-1);
    item.append(link);
    list.append(item);
  }
  section.append(title, list);
  return section;
}

function renderToolbar(file) {
  const toolbar = document.createElement("div");
  toolbar.className = "memo-toolbar";

  const downloadBtn = document.createElement("button");
  downloadBtn.type = "button";
  downloadBtn.className = "memo-download-button";
  downloadBtn.textContent = "下载本篇";
  downloadBtn.title = "仅下载本篇 Markdown（不含 AGENTS）";
  downloadBtn.addEventListener("click", async () => {
    downloadBtn.disabled = true;
    try {
      triggerDownload(downloadName(file), await buildSkillMarkdown(file, loadRaw));
      setStatus("");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : String(error));
    } finally {
      downloadBtn.disabled = false;
    }
  });

  toolbar.append(downloadBtn);
  return toolbar;
}

async function openFile(id) {
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
    const nodes = [renderToolbar(file)];
    const resources = renderResources(file);
    if (resources) nodes.push(resources);
    nodes.push(body);
    els.content.replaceChildren(...nodes);
    wrapTables(els.content);
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

function shanghaiDate() {
  return new Intl.DateTimeFormat("sv-SE", { timeZone: "Asia/Shanghai" }).format(new Date());
}

async function packDownload() {
  if (!manifest) return;
  els.pack.disabled = true;
  els.pack.setAttribute("aria-busy", "true");
  try {
    const stamp = shanghaiDate();
    const markdown = await buildPackMarkdown(manifest, loadRaw, stamp);
    triggerDownload(`我的皮燕子-${stamp}.md`, markdown);
    setStatus("");
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "合集下载失败");
  } finally {
    els.pack.disabled = false;
    els.pack.removeAttribute("aria-busy");
  }
}

async function historyDownload() {
  if (!manifest || !els.historyPack) return;
  els.historyPack.disabled = true;
  els.historyPack.setAttribute("aria-busy", "true");
  try {
    const stamp = shanghaiDate();
    const markdown = await buildHistoryMarkdown(manifest, loadRaw, stamp);
    triggerDownload(`皮燕子-历史打包-${stamp}.md`, markdown);
    setStatus("");
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "历史打包下载失败");
  } finally {
    els.historyPack.disabled = false;
    els.historyPack.removeAttribute("aria-busy");
  }
}

function fillPackPrompt() {
  if (!manifest || !els.packPrompt) return;
  els.packPrompt.value = localPackPrompt();
}

async function packCopyPrompt() {
  if (!manifest) return;
  const text = localPackPrompt();
  try {
    await copyText(text);
    if (els.packPrompt) {
      els.packPrompt.focus();
      els.packPrompt.select();
    }
    if (els.packCopy) await flashButton(els.packCopy, "已复制", "失败", "复制");
    setStatus("");
  } catch (err) {
    console.error(err);
    setStatus("复制失败");
  }
}

async function boot() {
  try {
    const res = await fetch(MANIFEST_URL);
    if (!res.ok) throw new Error(`清单加载失败：${res.status}`);
    manifest = validateManifest(await res.json());
    els.brand.textContent = manifest.name || "皮燕子";
    fillPackPrompt();
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
els.historyPack?.addEventListener("click", () => {
  void historyDownload();
});
els.packCopy?.addEventListener("click", () => {
  void packCopyPrompt();
});
els.packPrompt?.addEventListener("focus", () => els.packPrompt.select());
els.packPrompt?.addEventListener("click", () => els.packPrompt.select());
window.addEventListener("hashchange", () => {
  const id = decodeURIComponent(location.hash.replace(/^#/, ""));
  if (id && id !== activeId) void openFile(id);
});

boot();

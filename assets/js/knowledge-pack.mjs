/** 启动口令与 Markdown 交付；细则写进下载件正文，复制框只留短口令。 */
import { businessCatalog, packOrderedFiles, resourcePaths } from "./catalog.mjs";

/** 单篇短口令：文件已附上时，口头怎么点名即可。 */
export function localStartPrompt(file) {
  if (file.id === "AGENTS") return "皮燕子";
  if (file.id === "fenshen") return "分身启动";
  return `加载${file.title}`;
}

/** 合集短口令：与分身总启同调，说法不挑。 */
export function localPackPrompt(_manifest) {
  return "皮燕子启动";
}

const marker = file => `===== ${file.title}（${file.path}） =====`;

function usageBlock(kind) {
  if (kind === "pack") {
    return [
      "## 怎么用",
      "",
      "1. 把本文件交给 Agent，说「皮燕子启动」「分身启动」或「加载分身」均可。",
      "2. 先读文内 AGENTS，再读分身；按下方技能目录报名，点名某技能只读该篇正文。",
      "3. 已有具体任务直接办，不必先念完整报法。",
      "4. 配套模板、脚本见文末仓库相对路径；原始业务表由主人另附。",
      "",
    ];
  }
  return [
    "## 怎么用",
    "",
    "1. 把本文件交给 Agent，用短口令点名本篇即可（如「分身启动」「加载××」）。",
    "2. 先读文内 AGENTS，再读本篇；完整弹药名单见下方技能目录（仅目录，其它篇正文在合集里）。",
    "3. 已有具体任务直接办。",
    "4. 若本篇列有配套资源，见文末仓库相对路径；原始业务表另附。",
    "",
  ];
}

async function buildMarkdown(manifest, files, loadRaw, stamp, title, kind) {
  const paths = resourcePaths(files);
  const parts = [
    `# ${title}`,
    "",
    `生成日期：${stamp}`,
    "",
    ...usageBlock(kind),
    "## 技能目录",
    "",
    businessCatalog(manifest),
    "",
    "## 本文件收录",
    "",
    ...files.map((file, index) => `${index + 1}. 〔${file.group}〕${file.title} —— ${marker(file)}`),
    "",
    "## 配套资源",
    "",
  ];
  if (paths.length) {
    for (const path of paths) parts.push(`- ${path}`);
  } else {
    parts.push("本文件收录篇未另列配套资源。");
  }
  parts.push("");
  for (const file of files) {
    parts.push(marker(file), "", String(await loadRaw(file.path)).trimEnd(), "");
  }
  return parts.join("\n").trimEnd() + "\n";
}

export function buildSkillMarkdown(manifest, file, loadRaw, stamp) {
  const rules = manifest.files.find(entry => entry.id === "AGENTS");
  const files = file.id === "AGENTS" ? [rules] : [rules, file];
  return buildMarkdown(manifest, files, loadRaw, stamp, file.title, "skill");
}

export function buildPackMarkdown(manifest, loadRaw, stamp) {
  return buildMarkdown(manifest, packOrderedFiles(manifest), loadRaw, stamp, `${manifest.name}合集`, "pack");
}

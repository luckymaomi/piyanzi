/** 启动指令与 Markdown 交付；内容读取由调用者传入，不连接页面。 */
import { businessCatalog, packOrderedFiles, remoteUrl, resourcePaths } from "./catalog.mjs";

export function agentFetchPrompt(manifest, file) {
  const rules = manifest.files.find(entry => entry.id === "AGENTS");
  return `请先阅读 ${remoteUrl(manifest, rules.path)}（本轮已读则沿用），再读取 ${remoteUrl(manifest, "manifest.json")} 确认目录和配套资源，随后阅读 ${remoteUrl(manifest, file.path)} 并启动皮燕子「${file.title}」。只按任务需要取相关篇和资源，已有具体任务直接办理。`;
}

const marker = file => `===== ${file.title}（${file.path}） =====`;

async function buildMarkdown(manifest, files, loadRaw, stamp, title) {
  const paths = resourcePaths(files);
  const parts = [
    `# ${title}`, "", `生成日期：${stamp}`, "",
    "本文件收录下列技能正文与公共规约。先读 AGENTS，再按任务读取相应篇；总启按分身报法从本文件技能目录报名，已有具体任务直接办理。",
    "配套脚本、Excel模板及参考资料不嵌入本文，使用下方资源入口取得并保留仓库相对路径。原始业务文件仍由主人提供。", "",
    "## 技能目录（由清单生成）", "", businessCatalog(manifest), "",
    "## 本文件收录", "",
    ...files.map((file, index) => `${index+1}. 〔${file.group}〕${file.title} —— ${marker(file)}`), "",
    "## 配套资源", "",
    `[完整清单与资源关联](${remoteUrl(manifest, "manifest.json")})`,
    ...paths.map(path => `- [${path}](${remoteUrl(manifest, path)})`),
    ...(paths.length ? [] : ["本次收录篇没有另列配套资源；按具体业务需要取得原始资料。"]), "",
  ];
  for (const file of files) {
    parts.push(marker(file), "", String(await loadRaw(file.path)).trimEnd(), "");
  }
  return parts.join("\n").trimEnd() + "\n";
}

export function buildSkillMarkdown(manifest, file, loadRaw, stamp) {
  const rules = manifest.files.find(entry => entry.id === "AGENTS");
  const files = file.id === "AGENTS" ? [rules] : [rules, file];
  return buildMarkdown(manifest, files, loadRaw, stamp, file.title);
}

export function buildPackMarkdown(manifest, loadRaw, stamp) {
  return buildMarkdown(manifest, packOrderedFiles(manifest), loadRaw, stamp, `${manifest.name}合集`);
}

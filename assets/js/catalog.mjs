/** 清单模型：名称、分组和资源关系都来自 manifest，不访问 DOM。 */
export function validateManifest(manifest) {
  if (!manifest || !Array.isArray(manifest.files) || !manifest.files.length) {
    throw new Error("清单必须包含非空 files 列表。");
  }
  const ids = new Set();
  const paths = new Set();
  for (const file of manifest.files) {
    for (const field of ["id", "title", "path", "group"]) {
      if (typeof file[field] !== "string" || !file[field].trim()) {
        throw new Error(`清单条目缺少 ${field}。`);
      }
    }
    if (ids.has(file.id) || paths.has(file.path)) throw new Error(`清单条目重复：${file.id}`);
    ids.add(file.id);
    paths.add(file.path);
    if (file.resources !== undefined && (!Array.isArray(file.resources) || file.resources.some(path => typeof path !== "string" || !path.trim()))) {
      throw new Error(`配套资源必须为路径列表：${file.id}`);
    }
  }
  for (const id of ["AGENTS", "fenshen"]) {
    if (!ids.has(id)) throw new Error(`清单缺少公共入口：${id}`);
  }
  if (!/^https?:\/\//.test(manifest.remoteSkillBase || "")) throw new Error("缺少远端资源地址 remoteSkillBase。");
  if (manifest.history !== undefined) {
    if (!Array.isArray(manifest.history)) throw new Error("history 必须为列表。");
    for (const entry of manifest.history) {
      if (!entry || typeof entry.path !== "string" || !entry.path.trim()) {
        throw new Error("history 条目须含 path。");
      }
    }
  }
  return manifest;
}

export const listedFiles = manifest => manifest.files.filter(file => file.listed !== false);
export const businessFiles = manifest => listedFiles(manifest).filter(file => !["AGENTS", "fenshen"].includes(file.id));

export function groupedFiles(files) {
  const groups = new Map();
  for (const file of files) {
    const group = groups.get(file.group) || [];
    group.push(file);
    groups.set(file.group, group);
  }
  return groups;
}

export function packOrderedFiles(manifest) {
  const common = ["AGENTS", "fenshen"].map(id => manifest.files.find(file => file.id === id));
  const others = manifest.files.filter(file => !common.includes(file));
  return [...common, ...[...groupedFiles(others).values()].flat()];
}

export function resourcePaths(files) {
  return [...new Set(files.flatMap(file => file.resources || []))];
}

export function businessCatalog(manifest) {
  let number = 0;
  return [...groupedFiles(businessFiles(manifest))].flatMap(([group, files]) => [
    `〔${group}〕`, ...files.map(file => `${++number}. ${file.title}`),
  ]).join("\n");
}

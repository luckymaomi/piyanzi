/** 只保护目录扩展与下载交付，不测试DOM布局或正文措辞。 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { validateManifest, businessCatalog, packOrderedFiles, resourcePaths } from "../assets/js/catalog.mjs";
import { localPackPrompt, buildSkillMarkdown, buildPackMarkdown } from "../assets/js/knowledge-pack.mjs";

const root = new URL("../", import.meta.url);
const manifest = validateManifest(JSON.parse(await readFile(new URL("manifest.json", root), "utf8")));
const load = path => readFile(new URL(path, root), "utf8");

test("新增清单项直接进入技能目录与合集，无需修改分身或页面", async () => {
  const extra = { id: "new-skill", title: "新增技能", path: "core/new-skill.md", group: "新分类" };
  const extended = validateManifest({ ...manifest, files: [...manifest.files, extra] });
  assert.ok(businessCatalog(extended).includes(extra.title));
  assert.ok(packOrderedFiles(extended).includes(extra));
  const pack = await buildPackMarkdown(extended, path => path === extra.path ? "新增正文" : load(path), "2026-10-26");
  assert.ok(pack.includes("新增正文"));
  assert.equal(new Set(packOrderedFiles(extended).map(file => file.id)).size, extended.files.length);
});

test("顶栏口令为克隆仓库并加载；合集带怎么用与目录；单篇只下原文", async () => {
  assert.equal(
    localPackPrompt(),
    "克隆 https://github.com/luckymaomi/piyanzi ，并加载皮燕子",
  );
  const file = manifest.files.find(entry => entry.id === "waiji-daifei-pifu-hebing");

  const pack = await buildPackMarkdown(manifest, load, "2026-10-26");
  assert.ok(pack.includes("## 怎么用"));
  assert.ok(pack.includes("## 技能目录"));
  assert.ok(pack.includes(businessCatalog(manifest).split("\n")[1]));

  const body = (await load(file.path)).trimEnd() + "\n";
  const markdown = await buildSkillMarkdown(file, load);
  assert.equal(markdown, body);
  assert.ok(!markdown.includes("## 怎么用"));
  assert.ok(!markdown.includes(await load("AGENTS.md")));
});

test("清单拒绝重复入口；所有配套资源均可读取；合集收录全部正文", async () => {
  assert.throws(() => validateManifest({ ...manifest, files: [...manifest.files, manifest.files[0]] }));
  for (const path of resourcePaths(manifest.files)) {
    assert.ok((await readFile(new URL(path, root))).length > 0, path);
  }
  const pack = await buildPackMarkdown(manifest, load, "2026-10-26");
  for (const file of manifest.files) assert.ok(pack.includes((await load(file.path)).trimEnd()));
});

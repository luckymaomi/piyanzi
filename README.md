<div align="center">

# 皮燕子

[项目主页](https://luckymaomi.github.io/piyanzi/) · [GitHub](https://github.com/luckymaomi/piyanzi)

<p>
  <img alt="Static site" src="https://img.shields.io/badge/Architecture-static%20GitHub%20Pages-0f766e">
  <a href="https://www.python.org/"><img alt="Python 3" src="https://img.shields.io/badge/Python-3-3776AB"></a>
  <a href="https://marked.js.org/"><img alt="marked" src="https://img.shields.io/badge/Markdown-marked-222222"></a>
  <a href="./LICENSE"><img alt="MIT License" src="https://img.shields.io/github/license/luckymaomi/piyanzi?color=0f766e"></a>
</p>
</div>

皮燕子是业务 Skill 合集：网页浏览侧栏选篇，下载单篇或整包合集 Markdown，再把本地文件交给 Agent。主路径是「下载 → 本地附文」，不是远程拉取链。

职责分离：`AGENTS.md` 管公共纪律，`manifest.json` 是技能目录的唯一来源，`core/fenshen.md` 只管身份与岗位背景，各业务篇维护各自流程。下载件自洽（含公共规约与文内技能目录）；技能增减只改清单与对应业务篇，不必改分身。目录分组及配套资源也由清单维护。

## 技能目录

当前名称与入口直接读取 [manifest.json](./manifest.json)，浏览页自动生成导航。新增技能只需写 `core/技能名.md`（含 name、description、报装、综述）并加入清单，无需改分身、规约或本页的目录副本。

## 本地预览

仓库根目录执行：

```powershell
python index.py
```

默认打开 `http://localhost:4570/index.html`。常用参数：`--port`、`--no-open`、`--check`。

网页运行所需的 Bootstrap、marked 15.0.11 与 DOMPurify 3.2.6 均随 `assets/vendor/` 提供，本地浏览无需CDN；第三方许可与资源一同保留。

静态站仅需 Python 3.10+，不需要安装依赖。Excel 工具另执行：

```powershell
python -m pip install -r requirements.txt
```

`python -B -X utf8 index.py --check` 检查清单字段与重复入口、技能注册、配套文件和页面本地资源引用。`node --test scripts/test_site.mjs` 使用 Node 内置测试验证目录扩展、单篇与合集交付；不需安装 npm 依赖，不额外引入测试框架或CI。

## 工作文件与依赖

必要辅助脚本统一放在 `scripts/`，目前为进度查询与回填脚本 `scripts/update_progress.py`；网页启动入口 `index.py` 留在根目录。最终业务产物保留在根目录，Excel和本轮记录等不入库。

合集／单篇下载件自带「怎么用」、技能目录与正文；顶栏复制短口令默认是「皮燕子启动」，右侧下载整包。单篇页可另下本篇并复制「加载××」。配套模板与脚本只列仓库相对路径。前端在 `catalog.mjs`、`knowledge-pack.mjs`、`app.js`。

外籍批复技能以业务原则和本轮表格语义为依据，不附固定 Python 执行脚本；可使用 watchdog 的“外籍航线批复录入”APP，并从原始输入独立核验结果。

填表脚本仅作辅助。使用前先调研本轮真实表格结构，字段映射、名单与目标格以实表和主人确认的口径为准，不直接套用历史样例。

## 开源协议与贡献

本项目遵循 [MIT License](./LICENSE) 开源协议。

欢迎提交 Issue 或 Pull Request 改进 Skill、修复问题、补充文档。贡献时尽量说明问题场景、输入样例、期望结果和验证方式；改能力请改 `core/` 下对应 Skill 文件的报装 / 综述 / 细则，技能目录只改 `manifest.json`，公共纪律改 `AGENTS.md`，岗位身份只改 `core/fenshen.md`。

## 目前

服务于：南货航飞行部、中国南方航空货运有限公司。

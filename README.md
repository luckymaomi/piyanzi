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

皮燕子是业务 Skill 合集：网页可浏览、搜索、复制单篇启动指令、下载 Markdown，也可下载全部文件的单文件合集。

职责分离：`AGENTS.md` 管公共纪律，`manifest.json` 是技能目录的唯一来源，`core/fenshen.md` 只管身份与岗位背景，各业务篇维护各自流程。技能按需读取，分身独立启动，不加载其他技能。网页复制指令先取公共规约与清单，再读当前篇；本轮已读的规约沿用。联网地址统一由清单的 `remoteSkillBase` 与 `path` 生成。目录分组及配套资源也由清单维护。

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

单篇 Markdown 下载包含公共规约与当前正文，合集包含全部登记正文；两者都带由清单生成的技能目录和配套资源链接。Excel 模板、辅助脚本与参考资料需另取，不嵌在 Markdown 中；网页正文上方也提供对应下载入口。前端的目录模型、知识包生成和页面交互分别维护在 `catalog.mjs`、`knowledge-pack.mjs`、`app.js`。

外籍批复技能以业务原则和本轮表格语义为依据，不附固定 Python 执行脚本；可使用 watchdog 的“外籍航线批复录入”APP，并从原始输入独立核验结果。

填表脚本仅作辅助。使用前先调研本轮真实表格结构，字段映射、名单与目标格以实表和主人确认的口径为准，不直接套用历史样例。

## 开源协议与贡献

本项目遵循 [MIT License](./LICENSE) 开源协议。

欢迎提交 Issue 或 Pull Request 改进 Skill、修复问题、补充文档。贡献时尽量说明问题场景、输入样例、期望结果和验证方式；改能力请改 `core/` 下对应 Skill 文件的报装 / 综述 / 细则，技能目录只改 `manifest.json`，公共纪律改 `AGENTS.md`，岗位身份只改 `core/fenshen.md`。

## 目前

服务于：南货航飞行部、中国南方航空货运有限公司。

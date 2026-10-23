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

职责分离：`AGENTS.md` 管公共纪律，`manifest.json` 是技能目录的唯一来源，`core/fenshen.md` 只管身份与岗位背景，各业务篇维护各自流程。技能按需读取，分身独立启动，不加载其他技能。网页的复制指令只指向当前篇；联网地址统一由清单的 `remoteSkillBase` 与 `path` 生成。

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

`python index.py --check` 只检查网页入口、清单和技能文件是否存在。本项目保持轻量，不额外维护测试框架或CI。

## 工作文件与依赖

必要辅助脚本统一放在 `scripts/`，目前为进度查询与回填脚本 `scripts/update_progress.py`；网页启动入口 `index.py` 留在根目录。最终业务产物保留在根目录，Excel和本轮记录等不入库。

填表脚本仅作辅助。使用前先调研本轮真实表格结构，字段映射、名单与目标格以实表和主人确认的口径为准，不直接套用历史样例。

## 开源协议与贡献

本项目遵循 [MIT License](./LICENSE) 开源协议。

欢迎提交 Issue 或 Pull Request 改进 Skill、修复问题、补充文档。贡献时尽量说明问题场景、输入样例、期望结果和验证方式；改能力请改 `core/` 下对应 Skill 文件的报装 / 综述 / 细则，技能目录只改 `manifest.json`，公共纪律改 `AGENTS.md`，岗位身份只改 `core/fenshen.md`。

## 目前

服务于：南货航飞行部、中国南方航空货运有限公司。

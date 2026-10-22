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

皮燕子是 Cursor / Agent 用的业务 Skill 合集：页面可浏览、搜索、下载单篇 Markdown，也可一键下载合集（全部 Skill 合并为一个 `.md`，非 zip）。唤醒词与对主人话术见 `AGENTS.md`。

## 当前 Skill

状态：✅ 已启用 · 🧪 Beta 测试 · 🧊 已弃用

| Skill | 状态 | 功能 |
| --- | --- | --- |
| 检查单手册比对填写 | ✅ | 迎审检查单「符合性声明」按手册原文落笔；条款对上就填、对不上留空；可按条款抽 PDF 佐证 |
| 副驾驶流转更新 | ✅ | 货航 777 副驾驶积分总表：名单、等级/报务、考核、预警、总分、可流转 |
| 培训完成粗统计 | ✅ | 年度培训表粗统计：截止日各训人数、单训按月/按期、报告人话表述与套话回填 |
| 飞行部培训规则速查 | ✅ | 八项培训有效期/窗口/续期业务规则：对照表、填表口径、固定口算样例 |
| 资质代码 | ✅ | 资格代码死规矩查表：代码↔中文、类型、机型/岗位/技术等级要求、有效期 |
| 特殊机场资格代码 | ✅ | 特殊机场死规矩查表：机场名↔排班代码、高原/特殊/公司关注分类 |
| 资质录入检查预提示 | ✅ | 录入通知拆成检查清单：报务/单飞/机场映射、录入铁律、例外与疑点 |

## 本地预览

仓库根目录执行：

```powershell
python index.py
```

默认打开 `http://localhost:4570/index.html`。常用参数：`--port`、`--no-open`、`--check`。

## 开源协议与贡献

本项目遵循 [MIT License](./LICENSE) 开源协议。

欢迎提交 Issue 或 Pull Request 改进 Skill、修复问题、补充文档。贡献时尽量说明问题场景、输入样例、期望结果和验证方式；改能力请改 `core/` 下对应 Skill 文件的报装 / 综述 / 细则，页面清单改 `manifest.json`，入口索引改 `AGENTS.md`。

## 目前

服务于：南货航飞行部、中国南方航空货运有限公司。

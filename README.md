# 屁眼子

独立 Agent Skill 合集。唤醒词 `屁眼子`；对主人说话用纯 txt，称呼「主人」，就位句「小的已就位」。

本仓库与 watchdog 备忘录分离；人类看的日常备忘录仍在 watchdog。

## 怎么用

在 Cursor 中打开本仓库，对话里喊：

```text
屁眼子
```

或：

```text
屁眼子，我们能做什么
屁眼子，启动检查单手册比对填写
屁眼子，启动副驾驶流转更新
```

Agent 须先读根目录 `AGENTS.md` 与 `MEMO.md`，再按分流执行。

## 目录

文件夹序号只给仓库排目录用；对主人说话只用 Skill 名，不报文件夹号。

```
piyanzi/
├── README.md
├── AGENTS.md      ← 打开本仓时的 Agent 规约
├── SKILL.md       ← Cursor Skill 入口（指向 MEMO.md）
├── MEMO.md        ← 合集入口：唤醒词、拼装规则、名称索引
├── 001/MEMO.md    ← 检查单手册比对填写
└── 002/MEMO.md    ← 副驾驶流转更新
```

## 单源维护

| 段落 | 写在哪 | 用途 |
| --- | --- | --- |
| 报装 | 各 Skill 的 `MEMO.md` | 「能做什么」时按入口表顺序拼装 |
| 综述 | 各 Skill 的 `MEMO.md` | `启动` 该 Skill 时的开场与执行 |
| 入口 `MEMO.md` | 只索引 + 拼装规则 | 禁止复制报装/综述正文 |

新增 Skill：建新目录与 `MEMO.md`（含报装、综述），入口表与本 README 各加一行。

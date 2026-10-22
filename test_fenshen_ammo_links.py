# -*- coding: utf-8 -*-
"""
校验分身文首「弹药链接」与 manifest.json 一致：
- 顺序：AGENTS → listed Skills（与 manifest.files 顺序一致）
- 每行仅裸 raw URL，禁止同行中文/括号后缀
新增 Skill 后：改 manifest + 补 fenshen 链接，再跑本脚本。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "manifest.json"
FENSHEN = ROOT / "core" / "fenshen.md"
SECTION = "## 弹药链接（全量装载）"
URL_RE = re.compile(r"^https://raw\.githubusercontent\.com/\S+$")
# 同行若出现 CJK / 全角括号，视为坏链后缀
BAD_SUFFIX_RE = re.compile(r"[\u4e00-\u9fff（）()]")


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def expected_urls(manifest: dict) -> list[str]:
    base = str(manifest.get("remoteSkillBase") or "").rstrip("/") + "/"
    files = manifest.get("files") or []
    out: list[str] = []
    for f in files:
        path = str(f.get("path") or "").lstrip("./")
        if not path:
            continue
        is_agents = f.get("id") == "AGENTS" or path == "AGENTS.md"
        listed = f.get("listed") is not False
        if is_agents or listed:
            out.append(f"{base}{path}")
    return out


def parse_ammo_urls(text: str) -> list[str]:
    if SECTION not in text:
        raise ValueError(f"缺少章节：{SECTION}")
    after = text.split(SECTION, 1)[1]
    # 下一一级标题截断
    next_h2 = re.search(r"\n## ", after)
    block = after[: next_h2.start()] if next_h2 else after
    urls: list[str] = []
    bad_lines: list[str] = []
    for raw in block.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # 允许说明段落，只收集 http 开头行
        if not line.startswith("http"):
            continue
        if BAD_SUFFIX_RE.search(line) or not URL_RE.match(line):
            bad_lines.append(line)
            continue
        urls.append(line)
    if bad_lines:
        raise ValueError(
            "弹药链接行只能是裸 URL（勿加中文或括号后缀）：\n  - "
            + "\n  - ".join(bad_lines)
        )
    return urls


def main() -> int:
    if not MANIFEST.exists():
        print(f"[fail] 缺少 {MANIFEST}", file=sys.stderr)
        return 1
    if not FENSHEN.exists():
        print(f"[fail] 缺少 {FENSHEN}", file=sys.stderr)
        return 1

    manifest = load_manifest()
    expect = expected_urls(manifest)
    try:
        got = parse_ammo_urls(FENSHEN.read_text(encoding="utf-8"))
    except ValueError as e:
        print(f"[fail] {e}", file=sys.stderr)
        return 1

    ok = True
    if got != expect:
        ok = False
        print("[fail] 分身「弹药链接」与 manifest 不一致。", file=sys.stderr)
        print(f"  manifest 期望 {len(expect)} 条，分身实际 {len(got)} 条。", file=sys.stderr)
        exp_set, got_set = set(expect), set(got)
        missing = [u for u in expect if u not in got_set]
        extra = [u for u in got if u not in exp_set]
        if missing:
            print("  分身缺（请补进弹药链接）：", file=sys.stderr)
            for u in missing:
                print(f"    {u}", file=sys.stderr)
        if extra:
            print("  分身多（manifest 无或未 listed）：", file=sys.stderr)
            for u in extra:
                print(f"    {u}", file=sys.stderr)
        if not missing and not extra:
            print("  集合相同但顺序不同；请按 manifest.files 顺序重排。", file=sys.stderr)
            print("  期望：", file=sys.stderr)
            for u in expect:
                print(f"    {u}", file=sys.stderr)
            print("  实际：", file=sys.stderr)
            for u in got:
                print(f"    {u}", file=sys.stderr)

    if ok:
        print(f"[ok] 弹药链接 {len(got)} 条，与 manifest 一致（裸 URL、无中文后缀）。")
        return 0
    print(
        "[hint] 改完 manifest 后：更新 core/fenshen.md「弹药链接」，再跑 "
        "python test_fenshen_ammo_links.py",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
"""目前 CD 类副驾驶运行周期：晋升降本，FOA1→FOC/FOD 首次生效。Excel + Markdown。"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from statistics import mean, median

import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
import openpyxl.utils

sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(r"C:\Users\Administrator\Desktop\技术等级运行资格")
SP = BASE / "南货航飞行实力表20261023R2.xlsx"
TG = BASE / "技术等级导出.xlsx"
ROOT = Path(__file__).resolve().parents[1]
CUTOFF = date(2026, 10, 23)
OUT_X = ROOT / "CD副驾驶_运行周期_20261023.xlsx"
OUT_MD = ROOT / "CD副驾驶_运行周期_说明_20261023.md"


def to_date(v):
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()[:10]
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def load(path, sheet=None):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[sheet] if sheet else wb[wb.sheetnames[0]]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    h = [str(x).strip() if x is not None else "" for x in rows[0]]
    return {x: i for i, x in enumerate(h) if x}, rows[1:]


def grade_from_tech(tech):
    t = tech or ""
    if "划转副驾驶" in t:
        return "划转副驾驶"
    if "E类" in t and "副驾驶" in t:
        return "E"
    if "D类" in t:
        return "D"
    if "C类" in t:
        return "C"
    if "B类" in t:
        return "B"
    if "A2" in t:
        return "A2"
    if "A1" in t:
        return "A1"
    return "其他"


def yuan_bucket(yuan):
    y = yuan or ""
    if "返聘" in y:
        return "返聘"
    if any(k in y for k in ("总队777", "上海", "新疆")):
        return "同机型划转"
    return "晋升降本"


def hdr(ws, n):
    fill = PatternFill("solid", fgColor="D9E2F3")
    for c in range(1, n + 1):
        cell = ws.cell(1, c)
        cell.font = Font(bold=True)
        cell.fill = fill
    ws.freeze_panes = "A2"
    if ws.max_row >= 1:
        ws.auto_filter.ref = f"A1:{openpyxl.utils.get_column_letter(n)}{max(ws.max_row, 1)}"


def stats(xs):
    if not xs:
        return None
    return dict(
        平均=round(mean(xs), 2),
        中位数=float(median(xs)),
        最快=min(xs),
        最慢=max(xs),
        n=len(xs),
    )


def main():
    pi, prow = load(SP, "人员信息")
    ti, trow = load(TG)

    people = {}
    for r in prow:
        emp = str(r[pi["员工号"]] or "").strip()
        if not emp:
            continue
        tech = str(r[pi["技术信息"]] or "")
        if "副驾驶" not in tech:
            continue
        people[emp] = dict(
            员工号=emp,
            姓名=r[pi["姓名"]],
            分部=r[pi["分部"]],
            技术信息=tech,
            原单位=r[pi["原单位"]],
            现档=grade_from_tech(tech),
            册=yuan_bucket(str(r[pi["原单位"]] or "")),
        )

    codes = ["FOA1", "FOA2", "FOB", "FOC", "FOD"]
    first = defaultdict(dict)
    for r in trow:
        emp = str(r[ti["员工号"]] or "").strip()
        if emp not in people:
            continue
        code = str(r[ti["技术等级代码"]] or "").strip().upper()
        if code not in codes:
            continue
        if str(r[ti["机型"]] or "").strip() != "777":
            continue
        d = to_date(r[ti["生效日期"]])
        if not d:
            continue
        if code not in first[emp] or d < first[emp][code]:
            first[emp][code] = d

    rows = []
    for emp, p in people.items():
        row = {**p}
        for c in codes:
            row[c] = first[emp].get(c)
        s, c, d = row.get("FOA1"), row.get("FOC"), row.get("FOD")
        b = row.get("FOB")
        row["运行到C天"] = (c - s).days if s and c and c >= s else None
        row["运行到D天"] = (d - s).days if s and d and d >= s else None
        row["B到C天"] = (c - b).days if b and c and c >= b else None
        if row["现档"] in ("C", "D") and s:
            row["现档已运行天"] = (CUTOFF - s).days
        else:
            row["现档已运行天"] = None
        rows.append(row)

    jin = [r for r in rows if r["册"] == "晋升降本"]
    jin_cd = [r for r in jin if r["现档"] in ("C", "D")]
    all_cd = [r for r in rows if r["现档"] in ("C", "D")]

    # 主口径：晋升降本 运行→C / 运行→D（有终点样本，不限现档必须是C/D——通常到C的人现档已是C/D）
    foc_jin = [r["运行到C天"] for r in jin if r["运行到C天"] is not None]
    fod_jin = [r["运行到D天"] for r in jin if r["运行到D天"] is not None]
    bc_jin = [r["B到C天"] for r in jin if r["B到C天"] is not None]
    # 现势已是CD的人：运行起点到现在（在途感）与已有周期
    foc_cd_now = [r["运行到C天"] for r in jin_cd if r["运行到C天"] is not None]
    fod_cd_now = [r["运行到D天"] for r in jin_cd if r["运行到D天"] is not None]

    foc_all = [r["运行到C天"] for r in rows if r["运行到C天"] is not None]
    fod_all = [r["运行到D天"] for r in rows if r["运行到D天"] is not None]

    s_foc = stats(foc_jin)
    s_fod = stats(fod_jin)
    s_bc = stats(bc_jin)
    s_foc_all = stats(foc_all)
    s_fod_all = stats(fod_all)

    # 在途：晋升降本未到C
    zaitu = []
    for r in jin:
        if r["现档"] in ("C", "D"):
            continue
        s = r.get("FOA1")
        if not s:
            zaitu.append({**r, "已运行天": None, "说明": "无FOA1"})
            continue
        zaitu.append({**r, "已运行天": (CUTOFF - s).days, "说明": "未到C"})

    wb = Workbook()
    ws = wb.active
    ws.title = "00_口径"
    for a, b in [
        ("任务", "目前 CD 类副驾驶运行周期"),
        ("主口径", "仅晋升降本；起点=777 FOA1首次生效；终点=FOC/FOD首次生效（生效日，非检查日）"),
        ("实力表", str(SP)),
        ("技术等级", str(TG)),
        ("截止日", str(CUTOFF)),
        ("对照", "全副驾驶含同机型划转的运行→C/D 仅作对照，不主报"),
        ("现势CD", f"全表{len(all_cd)}（C{sum(1 for r in all_cd if r['现档']=='C')}+D{sum(1 for r in all_cd if r['现档']=='D')}）；晋升降本CD{len(jin_cd)}"),
    ]:
        ws.append([a, b])
    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["B"].width = 100

    ws = wb.create_sheet("01_周期汇总")
    ws.append(["样本册", "指标", "平均天", "中位数天", "最快", "最慢", "有效样本n", "说明"])
    def add(name, key, st, note):
        if not st:
            ws.append([name, key, "", "", "", "", 0, note])
        else:
            ws.append([name, key, st["平均"], st["中位数"], st["最快"], st["最慢"], st["n"], note])

    add("晋升降本（主）", "运行→C（FOA1→FOC）", s_foc, "主报")
    add("晋升降本（主）", "运行→D（FOA1→FOD）", s_fod, "主报；样本通常很少")
    add("晋升降本", "B→C（FOB→FOC）", s_bc, "辅报")
    add("全副驾驶（对照）", "运行→C", s_foc_all, "含同机型，均值偏长，不主报")
    add("全副驾驶（对照）", "运行→D", s_fod_all, "对照")
    ws.append([])
    ws.append(["现势结构", "副驾合计", len(people), "晋升降本", len(jin), "同机型", sum(1 for r in rows if r["册"] == "同机型划转")])
    ws.append(["现势CD", "合计", len(all_cd), "C", sum(1 for r in all_cd if r["现档"] == "C"), "D", sum(1 for r in all_cd if r["现档"] == "D")])
    ws.append(["晋升降本现势档", str(dict(Counter(r["现档"] for r in jin)))])
    ws.append(["晋升降本未到C人数", len(zaitu)])

    ws = wb.create_sheet("02_晋升降本周期样本")
    headers = ["员工号", "姓名", "分部", "现档", "原单位", "FOA1", "FOA2", "FOB", "FOC", "FOD", "运行到C天", "运行到D天", "B到C天"]
    ws.append(headers)
    for r in sorted(jin, key=lambda x: (x["现档"], x["员工号"])):
        if r.get("运行到C天") is None and r.get("运行到D天") is None:
            continue
        ws.append([r.get(h) for h in headers])
    if ws.max_row > 1:
        hdr(ws, len(headers))

    ws = wb.create_sheet("03_晋升降本现势CD")
    headers3 = ["员工号", "姓名", "分部", "现档", "原单位", "FOA1", "FOC", "FOD", "运行到C天", "运行到D天", "现档已运行天"]
    ws.append(headers3)
    for r in sorted(jin_cd, key=lambda x: (x["现档"], x["员工号"])):
        ws.append([r.get(h) for h in headers3])
    if ws.max_row > 1:
        hdr(ws, len(headers3))

    ws = wb.create_sheet("04_晋升降本未到C在途")
    headers4 = ["员工号", "姓名", "分部", "现档", "原单位", "FOA1", "已运行天", "说明"]
    ws.append(headers4)
    for r in sorted(zaitu, key=lambda x: (-(x.get("已运行天") or -1), x["员工号"])):
        ws.append([r.get(h) for h in headers4])
    if ws.max_row > 1:
        hdr(ws, len(headers4))

    ws = wb.create_sheet("05_全表现势CD对照")
    headers5 = ["员工号", "姓名", "册", "分部", "现档", "原单位", "FOA1", "FOC", "FOD", "运行到C天", "运行到D天"]
    ws.append(headers5)
    for r in sorted(all_cd, key=lambda x: (x["册"], x["现档"], x["员工号"])):
        ws.append([r.get(h) for h in headers5])
    if ws.max_row > 1:
        hdr(ws, len(headers5))

    wb.save(OUT_X)

    def line(st):
        if not st:
            return "无有效样本"
        return f"平均 {st['平均']} 天，中位 {st['中位数']} 天，最快 {st['最快']}，最慢 {st['最慢']}，n={st['n']}"

    md = f"""# 目前 CD 类副驾驶运行周期

## 0. 本轮做了什么

统计货航副驾驶从进入运行到取得 C / D 的周期（生效日）。  
交付：`{OUT_X.name}` + 本说明。

| 项 | 值 |
| --- | --- |
| 截止日 | {CUTOFF} |
| 实力表 | `{SP}` |
| 技术等级 | `{TG}` |

---

## 1. 清洗后是什么样

| 项 | 数量 |
| --- | ---: |
| 副驾驶合计 | {len(people)} |
| 晋升降本 | {len(jin)} |
| 同机型划转 | {sum(1 for r in rows if r['册']=='同机型划转')} |
| 现势 CD（全表） | {len(all_cd)}（C{sum(1 for r in all_cd if r['现档']=='C')} + D{sum(1 for r in all_cd if r['现档']=='D')}） |
| 现势 CD（晋升降本） | {len(jin_cd)} |
| 晋升降本未到 C | {len(zaitu)} |

777 同码取首次生效；成长周期主样本 = **晋升降本**。

---

## 2. 按什么口径统计了什么

**主口径（建议对外）**

1. 样本：晋升降本副驾驶。  
2. 起点：777 **FOA1 首次生效** = 进入货航运行。  
3. 终点：**FOC / FOD 首次生效**（不是检查日）。  

| 指标 | 结果 |
| --- | --- |
| 运行→C | {line(s_foc)} |
| 运行→D | {line(s_fod)} |
| B→C（辅） | {line(s_bc)} |

**对照（不主报）**：全副驾驶（含同机型）运行→C {line(s_foc_all)}；运行→D {line(s_fod_all)}。同机型历史 A1 早，均值会明显偏长。

明细见 Excel：02 周期样本、03 现势 CD、04 未到 C 在途、05 全表 CD 对照。

---

## 3. 结论（可贴汇报）

统计范围为晋升降本副驾驶。从进入货航运行到取得 C 类副驾驶，平均为 {s_foc['平均'] if s_foc else '—'} 天，中位数为 {s_foc['中位数'] if s_foc else '—'} 天，共统计 {s_foc['n'] if s_foc else 0} 人{"（样本较少，宜作量级参考）" if s_foc and s_foc["n"] < 15 else ""}。从进入货航运行到取得 D 类副驾驶，平均为 {s_fod['平均'] if s_fod else '—'} 天，中位数为 {s_fod['中位数'] if s_fod else '—'} 天，共统计 {s_fod['n'] if s_fod else 0} 人{"，样本仅 "+str(s_fod["n"])+" 人，仅供参考" if s_fod and s_fod["n"] < 5 else ""}。辅报：从 B 类副驾驶到取得 C 类副驾驶，平均为 {s_bc['平均'] if s_bc else '—'} 天，中位数为 {s_bc['中位数'] if s_bc else '—'} 天，共统计 {s_bc['n'] if s_bc else 0} 人。

现势全表 CD 类副驾驶 {len(all_cd)} 人，其中晋升降本仅 {len(jin_cd)} 人，CD 存量仍以同机型划转为主。晋升降本尚未取得 C 类的在途 {len(zaitu)} 人，名单见 Excel。

---

## 4. 附件

1. `{OUT_X}`  
2. 脚本：`scripts/cd_fo_run_cycle.py`  
"""
    OUT_MD.write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()

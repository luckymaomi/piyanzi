# -*- coding: utf-8 -*-
"""CD运行周期 + 2027预测；输出 Excel + Markdown（交付规范）。"""
from __future__ import annotations

import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import mean, median

import openpyxl
from openpyxl import Workbook

sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(r"C:\Users\Administrator\Desktop\技术等级运行资格")
SP = BASE / "南货航飞行实力表20261023R2.xlsx"
TG = BASE / "技术等级导出.xlsx"
ROOT = Path(__file__).resolve().parents[1]
OUT_X = ROOT / "CD副驾驶_运行周期与2027预测_20261023.xlsx"
OUT_MD = ROOT / "CD副驾驶_运行周期与2027预测_20261023.md"
CUTOFF = date(2026, 10, 23)
END2027 = date(2027, 12, 31)


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
        yuan = str(r[pi["原单位"]] or "")
        if "返聘" in yuan:
            bucket = "返聘"
        elif any(k in yuan for k in ("总队777", "上海", "新疆")):
            bucket = "同机型划转"
        else:
            bucket = "晋升降本"
        people[emp] = dict(
            员工号=emp,
            姓名=r[pi["姓名"]],
            技术信息=tech,
            原单位=yuan,
            册=bucket,
            现档=grade_from_tech(tech),
            分部=r[pi["分部"]],
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

    clean_rows = []
    for emp, p in people.items():
        row = {**p}
        for c in codes:
            row[c] = first[emp].get(c)
        s, c, d = row.get("FOA1"), row.get("FOC"), row.get("FOD")
        b = row.get("FOB")
        row["运行到C天"] = (c - s).days if s and c and c >= s else None
        row["运行到D天"] = (d - s).days if s and d and d >= s else None
        row["B到C天"] = (c - b).days if b and c and c >= b else None
        clean_rows.append(row)

    jin = [r for r in clean_rows if r["册"] == "晋升降本"]
    foc_days = [r["运行到C天"] for r in jin if r["运行到C天"] is not None]
    fod_days = [r["运行到D天"] for r in jin if r["运行到D天"] is not None]
    bc_days = [r["B到C天"] for r in jin if r["B到C天"] is not None]
    bc_all = [r["B到C天"] for r in clean_rows if r["B到C天"] is not None]
    a2c = []
    for r in clean_rows:
        s, e = r.get("FOA2"), r.get("FOC")
        if s and e and e >= s:
            a2c.append((e - s).days)

    med_bc = float(median(bc_all)) if bc_all else 405.0
    med_a2c = float(median(a2c)) if a2c else 1043.0
    horizon = (END2027 - CUTOFF).days

    c_now = sum(1 for r in clean_rows if r["现档"] == "C")
    d_now = sum(1 for r in clean_rows if r["现档"] == "D")
    cd_now = c_now + d_now
    jin_cd = sum(1 for r in clean_rows if r["册"] == "晋升降本" and r["现档"] in ("C", "D"))
    hz_cd = sum(1 for r in clean_rows if r["册"] == "同机型划转" and r["现档"] in ("C", "D"))
    b_now = sum(1 for r in clean_rows if r["现档"] == "B")
    a2_now = sum(1 for r in clean_rows if r["现档"] == "A2")

    # B→C：必须有 FOB，且 FOB+中位 <= 2027-12-31
    reach_b = []
    for r in clean_rows:
        if r["现档"] != "B":
            continue
        b = r.get("FOB")
        if not b:
            continue
        est = b + timedelta(days=int(med_bc))
        if est <= END2027:
            reach_b.append(r)
    # A2→C：有 FOA2，FOA2+中位 <= 期末（中位约3年，多数到不了）
    reach_a2 = []
    for r in clean_rows:
        if r["现档"] != "A2":
            continue
        s = r.get("FOA2")
        if not s:
            continue
        est = s + timedelta(days=int(med_a2c))
        if est <= END2027:
            reach_a2.append(r)

    promote_base = len(reach_b) + len(reach_a2)

    scenarios = []
    for name, back_rate, imp_rate, q4_add, promo_scale in [
        ("保守", 0.80, 0.05, 3, 0.75),
        ("中性", 0.60, 0.15, 6, 1.0),
        ("乐观", 0.45, 0.25, 8, 1.0),
    ]:
        cd_2026 = cd_now + q4_add
        promote = int(round(promote_base * promo_scale))
        back_cd = int(round(25 * back_rate))
        imp_cd = int(round(36 * imp_rate))
        cd_2027 = cd_2026 - back_cd + promote + imp_cd
        scenarios.append(
            dict(
                情景=name,
                估2026末CD=cd_2026,
                回流扣CD=back_cd,
                内部晋升入CD=promote,
                引进带入CD=imp_cd,
                估2027末CD=cd_2027,
                假设=f"回流CD占比{int(back_rate*100)}%;引进CD占比{int(imp_rate*100)}%;Q4增CD{q4_add};晋升人数≈{promote}(B有FOB且FOB+中位≤期末)",
            )
        )

    # Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "00_交付说明"
    rows0 = [
        ("标题", "CD副驾驶运行周期与2027年底数量预测"),
        ("数据截止", str(CUTOFF)),
        ("实力表", str(SP)),
        ("技术等级", str(TG)),
        ("训练汇报", r"C:\Users\Administrator\Desktop\2026年三季度训练汇报.docx"),
        (
            "清洗摘要",
            f"副驾{len(people)}；晋升降本{len(jin)}；同机型{sum(1 for r in clean_rows if r['册']=='同机型划转')}；现势C{c_now}+D{d_now}=CD{cd_now}",
        ),
        (
            "周期口径",
            "主口径=晋升降本；起点777 FOA1首次生效；终点FOC/FOD首次生效（生效日，非检查日）。",
        ),
        (
            "预测口径",
            "汇报：2026末副驾235、2027末246、年回流约25、2027引进36。CD用情景：存量±Q4、减回流CD、加内部B/A2晋升、加引进CD。",
        ),
        ("交付规范", "先清洗结果 → 再口径与统计表 → Excel与Markdown同步。"),
    ]
    ws.append(["项", "内容"])
    for a, b in rows0:
        ws.append([a, b])
    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["B"].width = 100

    ws = wb.create_sheet("01_清洗后明细")
    headers = [
        "员工号",
        "姓名",
        "分部",
        "册",
        "现档",
        "原单位",
        "技术信息",
        "FOA1",
        "FOA2",
        "FOB",
        "FOC",
        "FOD",
        "运行到C天",
        "运行到D天",
        "B到C天",
    ]
    ws.append(headers)
    for r in sorted(clean_rows, key=lambda x: (x["册"], x["现档"], x["员工号"])):
        ws.append([r.get(h) for h in headers])

    ws = wb.create_sheet("02_运行周期统计")
    ws.append(["样本册", "指标", "平均天", "中位数天", "最快", "最慢", "有效样本n", "口径说明"])

    def add_stat(bucket, key, rows, note):
        xs = [r[key] for r in rows if r.get(key) is not None]
        if not xs:
            ws.append([bucket, key, "", "", "", "", 0, note])
            return
        ws.append(
            [bucket, key, round(mean(xs), 2), float(median(xs)), min(xs), max(xs), len(xs), note]
        )

    add_stat("晋升降本", "运行到C天", jin, "主口径 FOA1→FOC")
    add_stat("晋升降本", "运行到D天", jin, "主口径 FOA1→FOD（样本少）")
    add_stat("晋升降本", "B到C天", jin, "FOB→FOC")
    add_stat("全副驾驶", "运行到C天", clean_rows, "对照含同机型，不主报")
    add_stat("全副驾驶", "B到C天", clean_rows, "预测用B→C中位")
    ws.append([])
    ws.append(["现势C", c_now, "现势D", d_now, "现势CD", cd_now, "副驾合计", len(people)])
    ws.append(["晋升降本CD", jin_cd, "同机型CD", hz_cd])
    ws.append(["距2027-12-31天", horizon, "B→C中位(全量)", med_bc, "A2→C中位", med_a2c])
    ws.append(["现B人数", b_now, "其中FOB+中位≤期末可到C", len(reach_b)])
    ws.append(["现A2人数", a2_now, "其中FOA2+中位≤期末可到C", len(reach_a2)])

    ws = wb.create_sheet("03_晋升降本周期样本")
    ws.append(["员工号", "姓名", "现档", "FOA1", "FOC", "FOD", "运行到C天", "运行到D天", "B到C天"])
    for r in jin:
        if r.get("运行到C天") is None and r.get("运行到D天") is None:
            continue
        ws.append(
            [
                r["员工号"],
                r["姓名"],
                r["现档"],
                r.get("FOA1"),
                r.get("FOC"),
                r.get("FOD"),
                r.get("运行到C天"),
                r.get("运行到D天"),
                r.get("B到C天"),
            ]
        )

    ws = wb.create_sheet("04_2027预测")
    ws.append(["项", "值"])
    ws.append(["汇报2026末副驾", 235])
    ws.append(["汇报2027末副驾", 246])
    ws.append(["汇报年回流约", 25])
    ws.append(["汇报2027引进", 36])
    ws.append(["本表现势副驾", len(people)])
    ws.append(["本表现势CD", cd_now])
    ws.append(["内部可晋升入CD基数", promote_base])
    ws.append([])
    ws.append(["情景", "估2026末CD", "回流扣CD", "内部晋升入CD", "引进带入CD", "估2027末CD", "假设"])
    for s in scenarios:
        ws.append(
            [
                s["情景"],
                s["估2026末CD"],
                s["回流扣CD"],
                s["内部晋升入CD"],
                s["引进带入CD"],
                s["估2027末CD"],
                s["假设"],
            ]
        )

    wb.save(OUT_X)

    lo, mid, hi = scenarios[0]["估2027末CD"], scenarios[1]["估2027末CD"], scenarios[2]["估2027末CD"]

    def fmt_stat(xs):
        if not xs:
            return "—", "—", "—", "—", 0
        return round(mean(xs), 2), float(median(xs)), min(xs), max(xs), len(xs)

    a1c = fmt_stat(foc_days)
    a1d = fmt_stat(fod_days)
    bcj = fmt_stat(bc_days)

    md = f"""# CD类副驾驶：运行周期与2027年底数量

## 0. 本轮做了什么

1. **清洗**：实力表「人员信息」副驾驶名单 + 技术等级 777 首次生效（FOA1～FOD）；按原单位分晋升降本 / 同机型划转。  
2. **统计**：CD 运行周期（生效日）；现势 CD 人数。  
3. **预测**：对照《2026年三季度训练汇报》人机比与回流/引进假设，给出 2027 年底 CD 情景。  
4. **同步交付**：本 Markdown + `{OUT_X.name}`。

| 项 | 路径/值 |
| --- | --- |
| 数据截止 | {CUTOFF} |
| 实力表 | `{SP}` |
| 技术等级 | `{TG}` |
| 训练汇报 | `C:\\Users\\Administrator\\Desktop\\2026年三季度训练汇报.docx` |

---

## 1. 清洗后是什么样

| 项 | 数量 |
| --- | ---: |
| 副驾驶合计 | {len(people)} |
| 晋升降本 | {len(jin)} |
| 同机型划转 | {sum(1 for r in clean_rows if r['册']=='同机型划转')} |
| 现势 C | {c_now} |
| 现势 D | {d_now} |
| **现势 CD** | **{cd_now}** |
| 晋升降本 CD | {jin_cd} |
| 同机型划转 CD | {hz_cd} |
| 现势 B / A2 | {b_now} / {a2_now} |

完整一人一行见 Excel「01_清洗后明细」。

---

## 2. 按什么口径统计了什么

### 2.1 目前 CD 类副驾驶运行周期

**主口径（建议写进汇报）**

1. 样本：仅 **晋升降本**（同机型不进成长均值）。  
2. 起点：777 **FOA1 首次生效** = 进入货航运行。  
3. 终点：**FOC / FOD 首次生效**（不是检查日）。  

| 指标 | 平均天 | 中位天 | 最快 | 最慢 | n |
| --- | ---: | ---: | ---: | ---: | ---: |
| 运行→C | {a1c[0]} | {a1c[1]} | {a1c[2]} | {a1c[3]} | {a1c[4]} |
| 运行→D | {a1d[0]} | {a1d[1]} | {a1d[2]} | {a1d[3]} | {a1d[4]} |
| B→C（晋升降本） | {bcj[0]} | {bcj[1]} | {bcj[2]} | {bcj[3]} | {bcj[4]} |

人话：本单位从跑起来到 C，大约 **2.6～3 年量级**（中位约 {a1c[1]} 天）；样本只有 {a1c[4]} 人，宜作量级。现势 CD 里多数是 **同机型划转带来**，不是本单位从 A1 养出来的。

### 2.2 预计 2027 年底 CD 数量——怎么预测、可不可信

汇报已锁定的是 **副驾总人数**（2026 末≈235，2027 末≈246），不是 CD。CD 要另估，关键三刀：

1. **回流约 25 人/年**：导回总队升机长，偏抽顶尖 → **偏抽 CD**。总副驾可以升，CD 未必升。  
2. **引进约 36 人**：短期多为低档；带多少现成 CD 不确定。  
3. **内部晋升**：现 B 里「已有 FOB，且 FOB+全量 B→C 中位（{med_bc:.0f} 天）≤2027-12-31」约 **{len(reach_b)}** 人；A2 同理约 **{len(reach_a2)}** 人（A2→C 中位约 {med_a2c:.0f} 天，多数赶不及）。

| 情景 | 估 2027 末 CD | 假设要点 |
| --- | ---: | --- |
| 保守 | **{lo}** | 回流 80% 来自 CD；引进几乎不带 CD；晋升打七五折 |
| **中性（建议主报）** | **{mid}** | 回流 60% 抽 CD；引进约 15% 带 CD；晋升按上面可到人数 |
| 乐观 | **{hi}** | 回流少抽 CD；引进/划转带较多 CD |

**判断**：第二个数 **可以给，但必须情景化**。不宜假装单点精确。若补充「回流名单是否已是 CD、引进人员到岗等级」，区间才能收成单值。

建议对外句：  
按三季度汇报人机比与年回流约一成测算，2027 年底 CD 类副驾驶约 **{mid}** 人（情景约 **{lo}～{hi}**）。现势 CD **{cd_now}** 人（C{c_now}+D{d_now}）。精确值取决于回流是否优先导走顶尖副驾，以及引进到岗时的技术等级结构。

---

## 3. 结论

1. **运行周期（晋升降本）**：运行→C 平均约 **{a1c[0]}** 天，中位 **{a1c[1]}** 天（n={a1c[4]}）；运行→D 样本极少（n={a1d[4]}）。  
2. **现势 CD**：**{cd_now}** 人。  
3. **2027 年底 CD**：主报中性约 **{mid}**，区间 **{lo}～{hi}**。

---

## 4. 附件

- Excel：`{OUT_X}`  
  - 00 交付说明  
  - 01 清洗后明细  
  - 02 运行周期统计  
  - 03 晋升降本周期样本  
  - 04 2027 预测  
"""
    OUT_MD.write_text(md, encoding="utf-8")
    print(md[:1500])
    print("...")
    print("saved", OUT_X)
    print("saved", OUT_MD)
    print("现势CD", cd_now, "周期n", a1c[4], "预测中性", mid, "区间", lo, hi)
    print("B可到C", len(reach_b), "A2可到C", len(reach_a2))


if __name__ == "__main__":
    main()

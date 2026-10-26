"""外籍带飞批复：开放+临开合并，拆去程/回程并多机场展开。

本文件仅为辅助脚本，不是业务规则真源。规则以 core 技能篇与主人当轮口径为准。
依赖：openpyxl。运行 python scripts/waiji_daifei_merge.py --help。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.datetime import to_excel

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE = ROOT / "templates" / "外籍带飞批复合并-模板.xlsx"


def default_output_path(season_label: str, effective: date, expiry: date, directory: Path | None = None) -> Path:
    """最终交付名：主名 +（由皮燕子合并去程回程生效…至…）.xlsx"""
    label = (season_label or "").strip() or "外籍带飞"
    # 去掉末尾已带的「外籍带飞…」重复词，只保留航季标签
    for suffix in ("外籍带飞开放临开合并", "外籍带飞批复合并", "外籍带飞"):
        if label.endswith(suffix):
            label = label[: -len(suffix)].strip(" _-")
            break
    if not label:
        label = "外籍带飞"
    name = (
        f"{label}外籍带飞开放临开合并"
        f"（由皮燕子合并去程回程生效{effective.isoformat()}至{expiry.isoformat()}）.xlsx"
    )
    return (directory or ROOT) / name


def infer_season_label(*paths: Path) -> str:
    """从源文件名里抠 2026夏秋 / 2025冬春 一类标签。"""
    for path in paths:
        name = path.name
        m = re.search(r"(20\d{2}\s*[夏冬]秋?|20\d{2}\s*冬春)", name)
        if m:
            return re.sub(r"\s+", "", m.group(1))
        m = re.search(r"(20\d{2})(夏秋|冬春)", name)
        if m:
            return m.group(1) + m.group(2)
    return ""

BLUE_FONT = Font(color="0000FF", name="宋体", size=11)
NORMAL_FONT = Font(name="宋体", size=11)
HEADER_FONT = Font(name="宋体", size=11, bold=True)
THIN = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)
WRAP = Alignment(wrap_text=True, vertical="center")

SHEET_MERGE = "开放与临开合并"
SHEET_GO = "去程"
SHEET_BACK = "回程"
SHEET_APT = "机场列表"
SHEET_RU = "俄罗斯机场列表"


def sha256(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_json(path: Path | str, value) -> None:
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def cell_str(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return str(value).strip()


def norm_tw(value) -> str:
    s = cell_str(value)
    return s if s else "否"


def parse_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = cell_str(value)
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"无法解析日期：{value!r}，请用 YYYY-MM-DD")


def read_source_rows(path: Path, validate: bool = True) -> list[dict]:
    """按字段读取；公司/航空公司同义，无表头时用标准七列。"""
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active
    def header_key(value):
        name = re.sub(r"\s+", "", cell_str(value))
        return "公司" if name == "航空公司" else name

    columns = list(range(7))
    start = 1
    header_found = False
    for r in range(1, min(20, ws.max_row) + 1):
        names = [header_key(ws.cell(r, c).value) for c in range(1, ws.max_column + 1)]
        if "公司" in names and "去程" in names:
            header_found = True
            find = lambda name: names.index(name) if name in names else -1
            stations = [i for i, name in enumerate(names) if name == "航站"]
            columns = [find("序号"), find("公司"), find("航站A"), find("航站B"), find("去程"), find("回程"), find("是否有台湾地区飞行员")]
            if columns[2] < 0:
                columns[2] = stations[0] if stations else -1
            if columns[3] < 0:
                columns[3] = stations[1] if len(stations) > 1 else -1
            if any(c < 0 for c in columns[1:]):
                raise ValueError(f"{path.name} 第{r}行缺少必要表头")
            start = r + 1
            break

    rows: list[dict] = []
    for r in range(start, ws.max_row + 1):
        raw = [ws.cell(r, c).value for c in range(1, ws.max_column + 1)]
        if not any(cell_str(value) for value in raw):
            continue
        if not header_found and sum(bool(cell_str(v)) for v in raw) == 1 and re.search(r"批复|临开|临时|航季", cell_str(raw[0])):
            continue
        values = [cell_str(raw[c]) if c >= 0 and c < len(raw) else "" for c in columns]
        seq, company, st_a, st_b, go, back, tw = values
        if header_key(company) == "公司" and header_key(go) == "去程":
            continue
        bad_cell = any(c >= 0 and ws.cell(r, c + 1).data_type == "e" for c in columns)
        if not bad_cell and not any(values[1:]) and re.match(r"^(执行日期|相关要求|说明|备注)([：:]|\s)", seq):
            continue
        bad_date = any(c >= 0 and c < len(raw) and isinstance(raw[c], (date, datetime)) for c in columns[1:])
        input_error = f"{path.name} 第{r}行公司或航站缺失，或存在错误/日期单元格" if bad_cell or bad_date or not company or not st_a or not st_b else ""
        company_error = columns[1] >= 0 and ws.cell(r, columns[1] + 1).data_type == "e"
        if validate and input_error:
            raise ValueError(input_error)
        rows.append(
            {
                "company": company,
                "station_a": st_a,
                "station_b": st_b,
                "go": go,
                "back": back,
                "tw": norm_tw(tw),
                "source": path.name,
                "source_row": r,
                "input_error": input_error,
                "company_unknown": not company or company_error or isinstance(raw[columns[1]], (date, datetime)),
            }
        )
    wb.close()
    return rows


def build_multi_airport_map(ws_apt) -> dict[str, list[str]]:
    """基地名 → [伦敦1, 伦敦2, …]，按尾数排序。仅收录有编号变体的城市。"""
    numbered: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for r in range(2, ws_apt.max_row + 1):
        name = cell_str(ws_apt.cell(r, 1).value)
        if not name:
            continue
        m = re.fullmatch(r"(.+?)(\d+)$", name)
        if not m:
            continue
        base, num = m.group(1), int(m.group(2))
        numbered[base].append((num, name))
    out: dict[str, list[str]] = {}
    for base, items in numbered.items():
        items.sort(key=lambda x: x[0])
        if len(items) >= 2:
            out[base] = [n for _, n in items]
        elif len(items) == 1:
            # 仅一个编号也视为展开目标（与机场列表一致）
            out[base] = [n for _, n in items]
    return out


def expand_station(name: str, multi: dict[str, list[str]]) -> list[str]:
    if name in multi:
        return list(multi[name])
    return [name]


def expand_od(row: dict, multi: dict[str, list[str]]) -> list[tuple[str, str, bool]]:
    """返回 (航站A展开名, 航站B展开名, 是否因多机场展开)。笛卡尔积。"""
    as_ = expand_station(row["station_a"], multi)
    bs = expand_station(row["station_b"], multi)
    expanded = len(as_) > 1 or len(bs) > 1 or (
        row["station_a"] in multi or row["station_b"] in multi
    )
    return [(a, b, expanded) for a in as_ for b in bs]


def apply_row_style(ws, row_idx: int, max_col: int, code_col: int | None = None, blue_code: bool = False):
    for c in range(1, max_col + 1):
        cell = ws.cell(row_idx, c)
        cell.border = THIN
        cell.alignment = WRAP
        if code_col and c == code_col and blue_code and cell.value:
            cell.font = BLUE_FONT
        else:
            cell.font = NORMAL_FONT


def write_merge_sheet(ws, rows: list[dict]) -> None:
    if ws.max_row > 1:
        ws.delete_rows(2, ws.max_row - 1)
    for i, row in enumerate(rows, start=1):
        r = i + 1
        ws.cell(r, 1).value = i
        ws.cell(r, 2).value = row["company"]
        ws.cell(r, 3).value = row["station_a"]
        ws.cell(r, 4).value = row["station_b"]
        ws.cell(r, 5).value = row["go"] or None
        ws.cell(r, 6).value = row["back"] or None
        ws.cell(r, 7).value = row["tw"]
        apply_row_style(ws, r, 7)


def write_leg_sheet(
    ws,
    items: list[dict],
    *,
    swap: bool,
    code_key: str,
    effective: date,
    expiry: date,
    airport_sheet: str = SHEET_APT,
    ru_sheet: str = SHEET_RU,
) -> None:
    if ws.max_row > 1:
        ws.delete_rows(2, ws.max_row - 1)
    eff_serial = to_excel(datetime(effective.year, effective.month, effective.day))
    exp_serial = to_excel(datetime(expiry.year, expiry.month, expiry.day))
    for i, item in enumerate(items, start=1):
        r = i + 1
        st_left = item["left"]
        st_right = item["right"]
        ws.cell(r, 1).value = i
        ws.cell(r, 2).value = item["company"]
        ws.cell(r, 3).value = st_left
        ws.cell(r, 4).value = st_right
        # PORT / 俄罗斯：保留模板同款 VLOOKUP
        ws.cell(r, 5).value = f'=VLOOKUP(C{r},{airport_sheet}!A:B,2,FALSE)'
        ws.cell(r, 6).value = f'=VLOOKUP(D{r},{airport_sheet}!A:B,2,FALSE)'
        code = item.get(code_key) or None
        ws.cell(r, 7).value = code
        ws.cell(r, 8).value = item["tw"]
        ws.cell(r, 9).value = eff_serial
        ws.cell(r, 9).number_format = "YYYY-MM-DD"
        ws.cell(r, 10).value = exp_serial
        ws.cell(r, 10).number_format = "YYYY-MM-DD"
        ws.cell(r, 11).value = f'=VLOOKUP(E{r},{ru_sheet}!A:C,3,FALSE)'
        ws.cell(r, 12).value = f'=VLOOKUP(F{r},{ru_sheet}!A:C,3,FALSE)'
        apply_row_style(ws, r, 12, code_col=7, blue_code=bool(item.get("multi") and code))


def build_legs(merged: list[dict], multi: dict[str, list[str]]) -> tuple[list[dict], list[dict]]:
    go_items: list[dict] = []
    back_items: list[dict] = []
    for row in merged:
        pairs = expand_od(row, multi)
        go = cell_str(row["go"])
        back = cell_str(row["back"])
        for a, b, multi_flag in (pairs if go else []):
            go_items.append(
                {
                    "company": row["company"],
                    "left": a,
                    "right": b,
                    "go": go,
                    "tw": row["tw"],
                    "multi": multi_flag,
                    "od": (row["station_a"], row["station_b"]),
                }
            )
        if back:
            for a, b, multi_flag in pairs:
                # 回程：航站B在前、航站A在后（相对展开后的 A/B）
                back_items.append(
                    {
                        "company": row["company"],
                        "left": b,
                        "right": a,
                        "back": back,
                        "tw": row["tw"],
                        "multi": multi_flag,
                        "od": (row["station_a"], row["station_b"]),
                    }
                )
    return go_items, back_items


def run_merge(
    open_path: Path,
    temp_path: Path,
    template_path: Path,
    output_path: Path,
    effective: date,
    expiry: date,
    airlines: list[str] | tuple[str, ...] = ("CSG",),
) -> dict:
    selected = list(dict.fromkeys(cell_str(code).upper() for code in airlines if cell_str(code)))
    if not selected:
        raise ValueError("请至少指定一个航司；货航代码为CSG")
    raw_open = read_source_rows(open_path, validate=False)
    raw_temp = read_source_rows(temp_path, validate=False)
    for row in raw_open + raw_temp:
        if row["company_unknown"]:
            raise ValueError(row["input_error"] or "公司为空或无法识别，不能确定批复归属")
    open_rows = [row for row in raw_open if row["company"].upper() in selected]
    temp_rows = [row for row in raw_temp if row["company"].upper() in selected]
    merged = open_rows + temp_rows
    for row in merged:
        if row["input_error"]:
            raise ValueError(row["input_error"])
    if not merged:
        raise ValueError(f"所选航司{','.join(selected)}在两份源表中没有可处理记录")

    shutil.copy2(template_path, output_path)
    wb = openpyxl.load_workbook(output_path)
    for need in (SHEET_MERGE, SHEET_GO, SHEET_BACK, SHEET_APT, SHEET_RU):
        if need not in wb.sheetnames:
            raise RuntimeError(f"模板缺工作表：{need}；现有={wb.sheetnames}")

    multi = build_multi_airport_map(wb[SHEET_APT])
    go_items, back_items = build_legs(merged, multi)

    write_merge_sheet(wb[SHEET_MERGE], merged)
    write_leg_sheet(
        wb[SHEET_GO],
        go_items,
        swap=False,
        code_key="go",
        effective=effective,
        expiry=expiry,
    )
    write_leg_sheet(
        wb[SHEET_BACK],
        back_items,
        swap=True,
        code_key="back",
        effective=effective,
        expiry=expiry,
    )
    wb.save(output_path)

    airport_names = {cell_str(wb[SHEET_APT].cell(r, 1).value) for r in range(2, wb[SHEET_APT].max_row + 1)}
    unknown_details = [
        {"source": row["source"], "source_row": row["source_row"], "station": station}
        for row in merged
        for station in dict.fromkeys(expand_station(row["station_a"], multi) + expand_station(row["station_b"], multi))
        if station not in airport_names
    ]
    report = {
        "open_path": str(open_path),
        "open_sha256": sha256(open_path),
        "temp_path": str(temp_path),
        "temp_sha256": sha256(temp_path),
        "template_path": str(template_path),
        "template_sha256": sha256(template_path),
        "output_path": str(output_path),
        "output_sha256": sha256(output_path),
        "effective": effective.isoformat(),
        "expiry": expiry.isoformat(),
        "airlines": selected,
        "raw_open_rows": len(raw_open),
        "raw_temp_rows": len(raw_temp),
        "excluded_rows": len(raw_open) + len(raw_temp) - len(merged),
        "airline_counts": {
            code: {
                "open": sum(row["company"].upper() == code for row in raw_open),
                "temporary": sum(row["company"].upper() == code for row in raw_temp),
            }
            for code in sorted({row["company"].upper() for row in raw_open + raw_temp})
        },
        "open_rows": len(open_rows),
        "temp_rows": len(temp_rows),
        "merged_rows": len(merged),
        "go_rows": len(go_items),
        "back_rows": len(back_items),
        "go_skipped_blank": sum(1 for r in merged if not r["go"]),
        "back_skipped_blank": sum(1 for r in merged if not r["back"]),
        "both_blank": sum(1 for r in merged if not r["go"] and not r["back"]),
        "unknown_airports": sorted({item["station"] for item in unknown_details}),
        "unknown_airport_rows": unknown_details,
        "multi_airport_bases": {k: v for k, v in sorted(multi.items())},
        "go_blank_codes": sum(1 for x in go_items if not x.get("go")),
        "back_blank_codes": sum(1 for x in back_items if not x.get("back")),
    }
    return report


def load_od_set_from_merge_sheet(path: Path, sheet_hint: str | None = None) -> list[tuple]:
    wb = openpyxl.load_workbook(path, data_only=True)
    if sheet_hint and sheet_hint in wb.sheetnames:
        ws = wb[sheet_hint]
    else:
        # 优先名含合并，否则第一张非去程回程机场
        ws = None
        for sn in wb.sheetnames:
            if "合并" in sn or "开放" in sn:
                ws = wb[sn]
                break
        if ws is None:
            ws = wb[wb.sheetnames[0]]
    # detect header
    start = 2
    if cell_str(ws.cell(1, 1).value) == "序号":
        start = 2
    out = []
    for r in range(start, ws.max_row + 1):
        if ws.cell(r, 3).value is None and ws.cell(r, 2).value is None:
            continue
        out.append(
            (
                cell_str(ws.cell(r, 2).value),
                cell_str(ws.cell(r, 3).value),
                cell_str(ws.cell(r, 4).value),
                cell_str(ws.cell(r, 5).value),
                cell_str(ws.cell(r, 6).value),
                norm_tw(ws.cell(r, 7).value),
            )
        )
    return out


def load_leg_pairs(path: Path, sheet_name: str, code_col: int = 7) -> list[tuple]:
    wb = openpyxl.load_workbook(path, data_only=False)
    if sheet_name not in wb.sheetnames:
        raise RuntimeError(f"{path.name} 无表 {sheet_name}")
    ws = wb[sheet_name]
    out = []
    for r in range(2, ws.max_row + 1):
        if ws.cell(r, 3).value is None and ws.cell(r, 2).value is None:
            continue
        out.append(
            (
                cell_str(ws.cell(r, 2).value),
                cell_str(ws.cell(r, 3).value),
                cell_str(ws.cell(r, 4).value),
                cell_str(ws.cell(r, code_col).value),
            )
        )
    return out


def compare_outputs(generated: Path, reference: Path) -> dict:
    """与旧版合并表比对：合并OD必须一致；去/回程在「全挂航路码」口径下允许与旧懒填差异。"""
    gen_od = load_od_set_from_merge_sheet(generated, SHEET_MERGE)
    # 旧表第一张名可能不同
    ref_wb = openpyxl.load_workbook(reference, data_only=True)
    ref_od = load_od_set_from_merge_sheet(reference, ref_wb.sheetnames[0])

    gen_set = set(gen_od)
    ref_set = set(ref_od)
    only_gen = sorted(gen_set - ref_set)
    only_ref = sorted(ref_set - gen_set)

    gen_go = load_leg_pairs(generated, SHEET_GO)
    ref_go = load_leg_pairs(reference, "去程")
    gen_bk = load_leg_pairs(generated, SHEET_BACK)
    ref_bk = load_leg_pairs(reference, "回程")

    def pair_key(t):
        return (t[0], t[1], t[2])  # company, left, right

    gen_go_map = {pair_key(x): x[3] for x in gen_go}
    ref_go_map = {pair_key(x): x[3] for x in ref_go}
    gen_bk_map = {pair_key(x): x[3] for x in gen_bk}
    ref_bk_map = {pair_key(x): x[3] for x in ref_bk}

    go_keys_gen, go_keys_ref = set(gen_go_map), set(ref_go_map)
    bk_keys_gen, bk_keys_ref = set(gen_bk_map), set(ref_bk_map)

    # 航路码：旧表空、新表有（全挂）记为 expected_upgrade
    go_upgraded = []
    go_conflict = []
    for k in sorted(go_keys_gen & go_keys_ref):
        g, r = gen_go_map[k], ref_go_map[k]
        if g == r:
            continue
        if r == "" and g != "":
            go_upgraded.append({"pair": k, "new": g, "old": r})
        elif g == "" and r != "":
            go_conflict.append({"pair": k, "new": g, "old": r, "note": "新空旧有"})
        else:
            go_conflict.append({"pair": k, "new": g, "old": r, "note": "码不一致"})

    bk_upgraded = []
    bk_conflict = []
    for k in sorted(bk_keys_gen & bk_keys_ref):
        g, r = gen_bk_map[k], ref_bk_map[k]
        if g == r:
            continue
        if r == "" and g != "":
            bk_upgraded.append({"pair": k, "new": g, "old": r})
        elif g == "" and r != "":
            bk_conflict.append({"pair": k, "new": g, "old": r, "note": "新空旧有"})
        else:
            bk_conflict.append({"pair": k, "new": g, "old": r, "note": "码不一致"})

    # 旧回程里源OD回程为空却仍展开出的空码行：新逻辑不应再有「无码回程」——
    # 但多机场占位在新逻辑下码是全挂的，不会空。
    summary = {
        "merged_od_count_gen": len(gen_od),
        "merged_od_count_ref": len(ref_od),
        "merged_od_match": len(only_gen) == 0 and len(only_ref) == 0,
        "only_in_generated": only_gen[:50],
        "only_in_reference": only_ref[:50],
        "go_row_count_gen": len(gen_go),
        "go_row_count_ref": len(ref_go),
        "back_row_count_gen": len(gen_bk),
        "back_row_count_ref": len(ref_bk),
        "go_pairs_only_gen": sorted(go_keys_gen - go_keys_ref)[:50],
        "go_pairs_only_ref": sorted(go_keys_ref - go_keys_gen)[:50],
        "back_pairs_only_gen": sorted(bk_keys_gen - bk_keys_ref)[:50],
        "back_pairs_only_ref": sorted(bk_keys_ref - bk_keys_gen)[:50],
        "go_code_upgraded_blank_to_full": len(go_upgraded),
        "back_code_upgraded_blank_to_full": len(bk_upgraded),
        "go_code_conflicts": go_conflict[:30],
        "back_code_conflicts": bk_conflict[:30],
        "go_upgrade_samples": go_upgraded[:15],
        "back_upgrade_samples": bk_upgraded[:15],
    }
    # 判定：合并OD一致，且无航路码冲突（升级空白→全挂不算冲突）
    summary["pass"] = bool(
        summary["merged_od_match"]
        and not go_conflict
        and not bk_conflict
        and go_keys_gen == go_keys_ref
        and bk_keys_gen == bk_keys_ref
    )
    return summary


def write_compare_report(path: Path, merge_report: dict, cmp: dict) -> None:
    lines = []
    lines.append("外籍带飞批复合并 · 实跑比对报告")
    lines.append("")
    lines.append("一、输入")
    lines.append(f"1. 开放：{merge_report['open_path']}")
    lines.append(f"2. 临开：{merge_report['temp_path']}")
    lines.append(f"3. 模板：{merge_report['template_path']}")
    lines.append(f"4. 生效/失效：{merge_report['effective']} ~ {merge_report['expiry']}")
    lines.append(f"5. 航司范围：{'、'.join(merge_report.get('airlines', [])) or '未提供合并报告，需核实范围'}")
    lines.append(f"6. 原始开放{merge_report.get('raw_open_rows', '?')}+临开{merge_report.get('raw_temp_rows', '?')}；排除未选航司{merge_report.get('excluded_rows', '?')}条")
    lines.append("")
    lines.append("二、产出规模")
    lines.append(
        f"1. 合并OD：开放{merge_report['open_rows']}+临开{merge_report['temp_rows']}="
        f"{merge_report['merged_rows']}；去程源空跳过{merge_report.get('go_skipped_blank', '?')}条；"
        f"回程源空跳过{merge_report['back_skipped_blank']}条；双向源空{merge_report.get('both_blank', '?')}条"
    )
    lines.append(f"2. 去程展开行：{merge_report['go_rows']}（其中去程码空{merge_report['go_blank_codes']}）")
    lines.append(f"3. 回程展开行：{merge_report['back_rows']}（其中回程码空{merge_report['back_blank_codes']}）")
    lines.append(f"4. 输出文件：{merge_report['output_path']}")
    lines.append(f"5. 输出SHA256：{merge_report['output_sha256']}")
    lines.append("")
    lines.append("三、与旧合并表比对")
    lines.append(f"1. 合并OD一致：{'是' if cmp['merged_od_match'] else '否'}（新{cmp['merged_od_count_gen']} / 旧{cmp['merged_od_count_ref']}）")
    if cmp["only_in_generated"]:
        lines.append(f"   仅新表有：{cmp['only_in_generated'][:10]}")
    if cmp["only_in_reference"]:
        lines.append(f"   仅旧表有：{cmp['only_in_reference'][:10]}")
    lines.append(
        f"2. 去程航站对一致：{'是' if not cmp['go_pairs_only_gen'] and not cmp['go_pairs_only_ref'] else '否'}"
        f"（新{cmp['go_row_count_gen']} / 旧{cmp['go_row_count_ref']}）"
    )
    lines.append(
        f"3. 回程航站对一致：{'是' if not cmp['back_pairs_only_gen'] and not cmp['back_pairs_only_ref'] else '否'}"
        f"（新{cmp['back_row_count_gen']} / 旧{cmp['back_row_count_ref']}）"
    )
    lines.append(
        f"4. 航路码「旧空→新全挂」升级：去程{cmp['go_code_upgraded_blank_to_full']}处，"
        f"回程{cmp['back_code_upgraded_blank_to_full']}处（预期差异，蓝色高亮）"
    )
    lines.append(f"5. 航路码冲突（非升级）：去程{len(cmp['go_code_conflicts'])}，回程{len(cmp['back_code_conflicts'])}")
    if cmp["go_code_conflicts"]:
        lines.append(f"   去程冲突样例：{cmp['go_code_conflicts'][:5]}")
    if cmp["back_code_conflicts"]:
        lines.append(f"   回程冲突样例：{cmp['back_code_conflicts'][:5]}")
    lines.append("")
    lines.append(f"四、结论：{'通过' if cmp['pass'] else '未通过——见上差异'}")
    lines.append("口径：合并OD与去/回程航站对须与旧表一致；多机场行航路码由「只挂首行」改为「全挂+蓝字」，不算失败。")
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="外籍带飞批复开放+临开合并并拆去程/回程")
    sub = p.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("merge", help="合并并生成去程/回程表")
    m.add_argument("--open", required=True, help="开放部分 xlsx")
    m.add_argument("--temp", required=True, help="临开部分 xlsx")
    m.add_argument("--template", default=str(DEFAULT_TEMPLATE), help="仓内模板")
    m.add_argument("--output", default="", help="输出 xlsx；省略则按最终文件名写入仓库根目录")
    m.add_argument("--season", default="", help="航季标签，如 2026夏秋；省略则尝试从源文件名推断")
    m.add_argument("--effective", required=True, help="生效日期 YYYY-MM-DD")
    m.add_argument("--expiry", required=True, help="失效日期 YYYY-MM-DD")
    m.add_argument("--airline", action="append", required=True, help="已确认的航司代码，货航为CSG；多航司重复传入")
    m.add_argument("--report-json", default="", help="可选：机器可读报告 json")

    c = sub.add_parser("compare", help="与旧合并表比对")
    c.add_argument("--generated", required=True)
    c.add_argument("--reference", required=True)
    c.add_argument("--report-txt", required=True)
    c.add_argument("--merge-report-json", default="", help="merge 步骤的 json，写入报告头部")

    a = sub.add_parser("run", help="merge + compare 一键")
    a.add_argument("--open", required=True)
    a.add_argument("--temp", required=True)
    a.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    a.add_argument("--output", default="", help="省略则按最终文件名写入仓库根目录")
    a.add_argument("--season", default="", help="航季标签，如 2026夏秋")
    a.add_argument("--reference", required=True, help="旧版合并表，用于比对")
    a.add_argument("--effective", required=True)
    a.add_argument("--expiry", required=True)
    a.add_argument("--airline", action="append", required=True, help="已确认的航司代码，货航为CSG；多航司重复传入")
    a.add_argument("--report-txt", default="", help="省略则与结果簿同目录、同主名+_比对报告.txt")
    a.add_argument("--report-json", default="")

    args = p.parse_args(argv)

    def resolve_output(ns) -> Path:
        effective = parse_date(ns.effective)
        expiry = parse_date(ns.expiry)
        if getattr(ns, "output", None):
            return Path(ns.output)
        season = getattr(ns, "season", "") or infer_season_label(Path(ns.open), Path(ns.temp))
        return default_output_path(season, effective, expiry)

    if args.cmd == "merge":
        out = resolve_output(args)
        report = run_merge(
            Path(args.open),
            Path(args.temp),
            Path(args.template),
            out,
            parse_date(args.effective),
            parse_date(args.expiry),
            airlines=args.airline,
        )
        if args.report_json:
            save_json(args.report_json, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "compare":
        merge_report = {}
        if args.merge_report_json:
            merge_report = json.loads(Path(args.merge_report_json).read_text(encoding="utf-8"))
        cmp = compare_outputs(Path(args.generated), Path(args.reference))
        write_compare_report(Path(args.report_txt), merge_report or {
            "open_path": "", "temp_path": "", "template_path": "",
            "effective": "", "expiry": "", "open_rows": "?", "temp_rows": "?",
            "merged_rows": cmp["merged_od_count_gen"], "back_skipped_blank": "?",
            "go_rows": cmp["go_row_count_gen"], "back_rows": cmp["back_row_count_gen"],
            "go_blank_codes": "?", "back_blank_codes": "?",
            "output_path": args.generated, "output_sha256": sha256(args.generated),
        }, cmp)
        print(json.dumps(cmp, ensure_ascii=False, indent=2))
        return 0 if cmp["pass"] else 1

    if args.cmd == "run":
        out = resolve_output(args)
        report = run_merge(
            Path(args.open),
            Path(args.temp),
            Path(args.template),
            out,
            parse_date(args.effective),
            parse_date(args.expiry),
            airlines=args.airline,
        )
        jpath = Path(args.report_json) if args.report_json else out.with_name(out.stem + "_实跑.json")
        save_json(jpath, report)
        cmp = compare_outputs(out, Path(args.reference))
        save_json(jpath.with_name(jpath.stem + "_compare.json"), cmp)
        report_txt = Path(args.report_txt) if args.report_txt else out.with_name(out.stem + "_比对报告.txt")
        write_compare_report(report_txt, report, cmp)
        print(json.dumps({"merge": report, "compare": cmp}, ensure_ascii=False, indent=2))
        return 0 if cmp["pass"] else 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())

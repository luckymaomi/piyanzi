"""外籍批复核心语义回归；直接运行，无额外测试框架依赖。"""
import sys
sys.dont_write_bytecode = True
import tempfile
import unittest
from datetime import date
from pathlib import Path

import openpyxl
import waiji_daifei_merge as app


class ApprovalTests(unittest.TestCase):
    def test_header_alias_and_first_data_row(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.xlsx"
            workbook = openpyxl.Workbook()
            sheet = workbook.active
            sheet.append(["冬春批复"])
            sheet.append(["序号", "航空\n公司", "航站", "航站", "去程", "回程", "是否有台湾\n地区飞行员"])
            sheet.append([1, "CSG", "广州", "伦敦", "", "任意非空文本", "否"])
            sheet.append(["执行日期：2026年10月25日-2027年3月27日。"])
            workbook.save(path)
            rows = app.read_source_rows(path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["source_row"], 3)
            self.assertEqual(rows[0]["company"], "CSG")
            workbook = openpyxl.Workbook()
            workbook.active.append([1, "CSG", "广州", "伦敦", "G", "B"])
            workbook.save(path)
            self.assertEqual(len(app.read_source_rows(path)), 1)

    def test_independent_directions_and_opaque_codes(self):
        route = "NIXAL-ZGGG-01R,SARIN-ZGGG-01,MORIT-ZGGG-01"
        base = {"company": "CSG", "station_a": "广州", "station_b": "伦敦", "tw": "否"}
        rows = [dict(base, go=g, back=b) for g, b in [("任意非空\n文本", route), (" \t", route), (route, "\n"), ("", "")]]
        go, back = app.build_legs(rows, {"伦敦": ["伦敦1", "伦敦2", "伦敦3"]})
        self.assertEqual([r["go"] for r in go], ["任意非空\n文本"] * 3 + [route] * 3)
        self.assertEqual([r["back"] for r in back], [route] * 6)
        self.assertEqual(back[0]["left"], "伦敦1")
        self.assertEqual(back[0]["right"], "广州")

    def test_export_preserves_od_and_has_no_empty_direction_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            paths = [directory / "open.xlsx", directory / "temporary.xlsx"]
            for i, path in enumerate(paths):
                workbook = openpyxl.Workbook()
                sheet = workbook.active
                sheet.append(["序号", "公司", "航站", "航站", "去程", "回程", "是否有台湾地区飞行员"])
                sheet.append([1, "CSG", "广州", "伦敦", "" if i == 0 else " ", "B" if i == 0 else "", "否"])
                workbook.save(path)
            output = directory / "result.xlsx"
            report = app.run_merge(*paths, app.DEFAULT_TEMPLATE, output, date(2026, 10, 25), date(2027, 3, 27))
            workbook = openpyxl.load_workbook(output)
            self.assertEqual(workbook[app.SHEET_MERGE].max_row, 3)
            self.assertEqual(workbook[app.SHEET_GO].max_row, 1)
            self.assertEqual(workbook[app.SHEET_BACK].max_row, 4)
            self.assertEqual(report["go_skipped_blank"], 2)
            self.assertEqual(report["both_blank"], 1)
            self.assertEqual(report["back_skipped_blank"], 1)


if __name__ == "__main__":
    unittest.main()

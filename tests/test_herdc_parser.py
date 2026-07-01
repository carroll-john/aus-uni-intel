from pathlib import Path

from openpyxl import Workbook

from uni_intel.ingestion.parsers.herdc import HerdcResearchIncomeParser


def test_herdc_parser_reads_summary_by_category(tmp_path: Path) -> None:
    workbook = Workbook()
    default = workbook.active
    workbook.remove(default)
    ws = workbook.create_sheet("1. Summary by Category")
    ws.append([])
    ws.append(["Table"])
    ws.append(
        [
            "HEP Code",
            "Higher Education Provider",
            "Year ",
            "State/Territory",
            "Cohort",
            "Category 1",
            "Category 2",
            "Category 3",
            "Category 4",
            "Total",
        ]
    )
    ws.append([1000, "Monash University", 2024, "VIC", "Go8", 1, 2, 3, 4, 10])
    path = tmp_path / "herdc.xlsx"
    workbook.save(path)

    rows = HerdcResearchIncomeParser().parse(path)

    assert len(rows) == 5
    assert rows[-1].metric_id == "herdc_research_income_total"
    assert rows[-1].numeric_value == 10
    assert rows[-1].dimensions["cohort"] == "Go8"

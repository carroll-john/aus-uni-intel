from pathlib import Path
from zipfile import ZipFile

from openpyxl import Workbook

from uni_intel.ingestion.parsers.qilt import QiltSesParser, parse_qilt_value


def test_parse_qilt_value_with_confidence_interval() -> None:
    assert parse_qilt_value("80.5 (79.7, 81.3)") == (80.5, 79.7, 81.3)


def test_parse_qilt_value_suppressed() -> None:
    assert parse_qilt_value("n/a") is None


def test_qilt_parser_reads_2021_style_xlsx_zip(tmp_path: Path) -> None:
    workbook_path = tmp_path / "national.xlsx"
    _write_qilt_workbook(workbook_path)
    archive_path = tmp_path / "qilt.zip"
    with ZipFile(archive_path, "w") as archive:
        archive.write(workbook_path, "2021 SES National Report Tables.xlsx")

    rows = QiltSesParser(reporting_year=2021).parse(archive_path)

    assert {row.reporting_year for row in rows} == {2021}
    assert {row.source_table for row in rows} == {
        "FOCUS_UG_UNI_1Y_INST_CI",
        "FOCUS_PGC_UNI_1Y_INST_CI",
    }
    assert any(
        row.metric_id == "qilt_peer_engagement_positive_rating"
        and row.dimensions["source_line_item"] == "Learner Engagement"
        for row in rows
    )
    assert any(row.source_provider_name == "The University of Sydney" for row in rows)


def _write_qilt_workbook(path: Path) -> None:
    workbook = Workbook()
    default = workbook.active
    workbook.remove(default)
    headers = [
        "",
        "",
        "Skills Development",
        "Learner Engagement",
        "Teaching Quality",
        "Student Support",
        "Learning Resources",
        "Quality of entire educational experience",
    ]
    values = [
        "",
        "The University of Sydney",
        "80.1 (79.0, 81.2)",
        "60.2 (59.0, 61.4)",
        "78.3 (77.1, 79.5)",
        "75.4 (74.1, 76.7)",
        "82.5 (81.2, 83.8)",
        "70.6 (69.4, 71.8)",
    ]
    for sheet_name in ["FOCUS_UG_UNI_1Y_INST_CI", "FOCUS_PGC_UNI_1Y_INST_CI"]:
        sheet = workbook.create_sheet(sheet_name)
        sheet.append(["Student experience"])
        sheet.append(["Back to INDEX"])
        sheet.append(["", "", "", "", "", "", "", ""])
        sheet.append(headers)
        sheet.append(values)
    workbook.save(path)

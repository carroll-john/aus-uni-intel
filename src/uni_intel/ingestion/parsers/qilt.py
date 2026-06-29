from __future__ import annotations

import re
import zipfile
from io import BytesIO
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET


class QiltParseError(ValueError):
    pass


@dataclass(frozen=True)
class QiltRawRow:
    row_number: int
    source_table: str
    source_provider_name: str
    metric_id: str
    reporting_year: int
    raw_value: str
    numeric_value: float
    ci_lower: float | None
    ci_upper: float | None
    dimensions: dict[str, object]


ODS_NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
}
TABLE = f"{{{ODS_NS['table']}}}"
TEXT = f"{{{ODS_NS['text']}}}"
OFFICE = f"{{{ODS_NS['office']}}}"

QILT_COLUMNS = {
    "Skills Development": "qilt_skills_development_positive_rating",
    "Peer Engagement *": "qilt_peer_engagement_positive_rating",
    "Teaching Quality and Engagement": "qilt_teaching_quality_engagement_positive_rating",
    "Student Support and Services *": "qilt_student_support_services_positive_rating",
    "Learning Resources": "qilt_learning_resources_positive_rating",
    "Quality of entire educational\xa0experience": "qilt_overall_educational_experience_positive_rating",
    "Quality of entire educational experience": "qilt_overall_educational_experience_positive_rating",
}

QILT_PROVIDER_TABLES = {
    "FOCUS_UG_UNI_1Y_INST_CI": "undergraduate",
    "FOCUS_PGC_UNI_1Y_INST_CI": "postgraduate coursework",
}


class QiltSesParser:
    def parse(self, path: Path | str) -> list[QiltRawRow]:
        root = _load_ods_content(Path(path))
        parsed: list[QiltRawRow] = []
        for table_name, course_level in QILT_PROVIDER_TABLES.items():
            table_rows = _table_rows(root, table_name)
            if not table_rows:
                raise QiltParseError(f"ODS table {table_name} not found")
            if len(table_rows) < 5:
                raise QiltParseError(f"ODS table {table_name} has no provider rows")

            headers = table_rows[3]
            metric_columns: list[tuple[int, str, str]] = []
            for index, header in enumerate(headers):
                if header in QILT_COLUMNS:
                    metric_columns.append((index, QILT_COLUMNS[header], str(header).replace(" *", "")))

            for row_number, row in enumerate(table_rows[4:], start=5):
                provider = row[1] if len(row) > 1 else None
                if not provider or not isinstance(provider, str):
                    continue
                for column_index, metric_id, line_item in metric_columns:
                    raw_value = row[column_index] if len(row) > column_index else None
                    parsed_value = parse_qilt_value(raw_value)
                    if parsed_value is None:
                        continue
                    value, ci_lower, ci_upper = parsed_value
                    parsed.append(
                        QiltRawRow(
                            row_number=row_number,
                            source_table=table_name,
                            source_provider_name=provider,
                            metric_id=metric_id,
                            reporting_year=2024,
                            raw_value=str(raw_value),
                            numeric_value=value,
                            ci_lower=ci_lower,
                            ci_upper=ci_upper,
                            dimensions={
                                "course_level": course_level,
                                "provider_type": "universities",
                                "confidence_interval": "90%",
                                "ci_lower": ci_lower,
                                "ci_upper": ci_upper,
                                "source_line_item": line_item,
                            },
                        )
                    )
        return parsed


def parse_qilt_value(value: object) -> tuple[float, float | None, float | None] | None:
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in {"", "n/a", "np", "suppressed"}:
        return None
    match = re.match(r"^([0-9]+(?:\.[0-9]+)?)(?:\s*\(([0-9.]+),\s*([0-9.]+)\))?$", text)
    if not match:
        raise QiltParseError(f"Invalid QILT value: {value}")
    estimate = float(match.group(1))
    lower = float(match.group(2)) if match.group(2) else None
    upper = float(match.group(3)) if match.group(3) else None
    return estimate, lower, upper


def _load_ods_content(path: Path) -> ET.Element:
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            ods_names = [name for name in archive.namelist() if name.lower().endswith(".ods")]
            if not ods_names:
                raise QiltParseError("QILT ZIP did not contain an ODS file")
            with archive.open(ods_names[0]) as ods_handle:
                ods_bytes = ods_handle.read()
        with zipfile.ZipFile(BytesIO(ods_bytes)) as ods_archive:
            return ET.fromstring(ods_archive.read("content.xml"))

    with zipfile.ZipFile(path) as archive:
        return ET.fromstring(archive.read("content.xml"))


def _table_rows(root: ET.Element, table_name: str) -> list[list[object | None]]:
    for table in root.findall(f".//{TABLE}table"):
        if table.attrib.get(f"{TABLE}name") == table_name:
            rows: list[list[object | None]] = []
            for row in table.findall(f"{TABLE}table-row"):
                repeat = int(row.attrib.get(f"{TABLE}number-rows-repeated", "1"))
                values: list[object | None] = []
                for cell in row.findall(f"{TABLE}table-cell"):
                    column_repeat = min(
                        int(cell.attrib.get(f"{TABLE}number-columns-repeated", "1")),
                        64,
                    )
                    values.extend([_cell_value(cell)] * column_repeat)
                for _ in range(min(repeat, 1)):
                    rows.append(values)
            return rows
    return []


def _cell_value(cell: ET.Element) -> object | None:
    value = cell.attrib.get(f"{OFFICE}value")
    if value is not None:
        try:
            return float(value)
        except ValueError:
            return value
    string_value = cell.attrib.get(f"{OFFICE}string-value")
    if string_value is not None:
        return string_value
    parts: list[str] = []
    for paragraph in cell.findall(f".//{TEXT}p"):
        text = "".join(paragraph.itertext()).strip()
        if text:
            parts.append(text)
    return " ".join(parts) if parts else None

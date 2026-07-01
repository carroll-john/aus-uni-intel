from pathlib import Path

import duckdb

from uni_intel.config import SCHEMA_PATH
from uni_intel.ingestion.calculations import calculate_metrics

OPERATING_RESULT = "finance_operating_result_from_continuing_operations"
TOTAL_REVENUE = "finance_total_revenues_from_continuing_operations_including_deferred_superannuation"
RESEARCH = "herdc_research_income_total"
ENROLMENTS = "student_total_enrolments"

_SOURCE_METRICS = {
    OPERATING_RESULT: ("Operating result", "Finance"),
    TOTAL_REVENUE: ("Total revenue", "Finance"),
    RESEARCH: ("Research income", "Research"),
    ENROLMENTS: ("Total enrolments", "Students"),
}


def _build_source_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "calc.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.execute(
            """
            INSERT INTO providers (provider_id, provider_name, provider_type)
            VALUES ('university_of_sydney', 'The University of Sydney', 'university')
            """
        )
        conn.execute(
            """
            INSERT INTO source_files (
                source_file_id, dataset_id, source_name, source_url, local_path,
                file_format, reporting_year, downloaded_at, checksum_sha256, row_count
            ) VALUES ('sf1', 'ds1', 'Src', 'https://x', '/tmp/x', 'xlsx', 2024, CURRENT_TIMESTAMP, 'c', 4)
            """
        )
        for metric_id, (name, group) in _SOURCE_METRICS.items():
            conn.execute(
                """
                INSERT INTO metrics (metric_id, metric_name, metric_group, unit, value_type, definition, source_agency, source_dataset)
                VALUES (?, ?, ?, 'number', 'number', 'def', 'Dept', 'Dataset')
                """,
                [metric_id, name, group],
            )
        facts = [
            (OPERATING_RESULT, "Total Institution", 100.0),
            (TOTAL_REVENUE, "Total Institution", 1000.0),
            (RESEARCH, "HERDC", 500000.0),
            (ENROLMENTS, "Student", 50000.0),
        ]
        for metric_id, scope, value in facts:
            conn.execute(
                """
                INSERT INTO facts (
                    fact_id, provider_id, metric_id, source_file_id, reporting_year,
                    dimension_scope, value, unit, source_row_number, source_provider_name,
                    source_line_item, dimensions_json
                ) VALUES (?, 'university_of_sydney', ?, 'sf1', 2024, ?, ?, 'u', 1, 'Src', 'Line', '{}')
                """,
                [f"{metric_id}-2024", metric_id, scope, value],
            )
    finally:
        conn.close()
    return db_path


def test_calculate_metrics_derives_expected_values(tmp_path: Path) -> None:
    db_path = _build_source_db(tmp_path)

    result = calculate_metrics(db_path)
    # Re-running is idempotent (delete-then-insert per source_file_id).
    calculate_metrics(db_path)

    assert result["facts_loaded"] == 3

    conn = duckdb.connect(str(db_path))
    try:
        values = dict(
            conn.execute(
                "SELECT metric_id, value FROM facts WHERE source_file_id = 'calculated_metrics_local'"
            ).fetchall()
        )
        assert (
            conn.execute("SELECT COUNT(*) FROM facts WHERE source_file_id = 'calculated_metrics_local'").fetchone()[0]
            == 3
        )
    finally:
        conn.close()

    assert values["calc_operating_margin"] == 10.0
    assert values["calc_research_income_share_of_revenue"] == 50.0
    assert values["calc_research_income_per_enrolment"] == 10.0

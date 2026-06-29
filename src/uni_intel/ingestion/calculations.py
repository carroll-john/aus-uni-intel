from __future__ import annotations

import hashlib
import json
from pathlib import Path

from uni_intel.config import DB_PATH
from uni_intel.db import connect, init_schema
from uni_intel.ingestion.common import (
    SourceDataset,
    SourceFileMetadata,
    json_dumps,
    new_run_id,
    stable_fact_id,
    upsert_metric_dependencies,
    upsert_metrics,
    upsert_source_dataset,
    upsert_source_file,
)
from uni_intel.ingestion.metrics import CALCULATED_METRICS


DATASET_ID = "calculated_metrics"
SOURCE_FILE_ID = "calculated_metrics_local"


DEPENDENCIES = {
    "calc_operating_margin": [
        ("finance_operating_result_from_continuing_operations", "numerator"),
        (
            "finance_total_revenues_from_continuing_operations_including_deferred_superannuation",
            "denominator",
        ),
    ],
    "calc_research_income_share_of_revenue": [
        ("herdc_research_income_total", "numerator"),
        (
            "finance_total_revenues_from_continuing_operations_including_deferred_superannuation",
            "denominator",
        ),
    ],
    "calc_research_income_per_enrolment": [
        ("herdc_research_income_total", "numerator"),
        ("student_total_enrolments", "denominator"),
    ],
}


def calculate_metrics(db_path: Path = DB_PATH) -> dict[str, object]:
    run_id = new_run_id()
    checksum = hashlib.sha256(
        json.dumps(CALCULATED_METRICS, sort_keys=True).encode("utf-8")
    ).hexdigest()
    conn = connect(db_path)
    try:
        init_schema(conn)
        upsert_source_dataset(
            conn,
            SourceDataset(
                DATASET_ID,
                "Calculated metrics",
                "Local calculation from source-backed canonical facts",
                "local://calculated-metrics",
                "Calculated facts generated from source-backed facts in the DuckDB warehouse.",
            ),
        )
        upsert_source_file(
            conn,
            SourceFileMetadata(
                SOURCE_FILE_ID,
                DATASET_ID,
                "Calculated metrics",
                "local://calculated-metrics",
                Path("local://calculated-metrics"),
                "calculation",
                None,
                checksum,
                len(CALCULATED_METRICS),
                "Derived locally",
                None,
                "Synthetic source record for calculated canonical facts.",
            ),
        )
        upsert_metrics(conn, CALCULATED_METRICS)
        for metric_id, dependencies in DEPENDENCIES.items():
            upsert_metric_dependencies(conn, metric_id, dependencies)

        conn.execute("DELETE FROM facts WHERE source_file_id = ?", [SOURCE_FILE_ID])
        operating = _insert_operating_margin(conn)
        research_share = _insert_research_share(conn)
        research_per_enrolment = _insert_research_per_enrolment(conn)
    finally:
        conn.close()
    return {
        "run_id": run_id,
        "source_file_id": SOURCE_FILE_ID,
        "facts_loaded": operating + research_share + research_per_enrolment,
        "metrics": {
            "calc_operating_margin": operating,
            "calc_research_income_share_of_revenue": research_share,
            "calc_research_income_per_enrolment": research_per_enrolment,
        },
    }


def _insert_operating_margin(conn) -> int:
    rows = conn.execute(
        """
        SELECT revenue.provider_id, revenue.reporting_year, revenue.dimension_scope,
               result.value AS operating_result, revenue.value AS revenue_value
        FROM facts revenue
        JOIN facts result
          ON result.provider_id = revenue.provider_id
         AND result.reporting_year = revenue.reporting_year
         AND result.dimension_scope = revenue.dimension_scope
        WHERE revenue.metric_id = 'finance_total_revenues_from_continuing_operations_including_deferred_superannuation'
          AND result.metric_id = 'finance_operating_result_from_continuing_operations'
          AND revenue.value != 0
        """
    ).fetchall()
    fact_rows = []
    for provider_id, year, scope, operating_result, revenue_value in rows:
        dimensions_json = json_dumps({"calculation": "operating_margin"})
        value = 100 * float(operating_result) / float(revenue_value)
        fact_rows.append(_fact_tuple(provider_id, "calc_operating_margin", year, scope, value, "percent", dimensions_json))
    _insert_fact_rows(conn, fact_rows)
    return len(fact_rows)


def _insert_research_share(conn) -> int:
    rows = conn.execute(
        """
        SELECT research.provider_id, research.reporting_year,
               research.value AS research_income, revenue.value AS revenue_value
        FROM facts research
        JOIN facts revenue
          ON revenue.provider_id = research.provider_id
         AND revenue.reporting_year = research.reporting_year
        WHERE research.metric_id = 'herdc_research_income_total'
          AND revenue.metric_id = 'finance_total_revenues_from_continuing_operations_including_deferred_superannuation'
          AND revenue.dimension_scope = 'Total Institution'
          AND revenue.value != 0
        """
    ).fetchall()
    fact_rows = []
    for provider_id, year, research_income, revenue_value in rows:
        dimensions_json = json_dumps({"calculation": "research_income_share_of_revenue"})
        value = 100 * float(research_income) / (float(revenue_value) * 1000)
        fact_rows.append(_fact_tuple(provider_id, "calc_research_income_share_of_revenue", year, "Calculated", value, "percent", dimensions_json))
    _insert_fact_rows(conn, fact_rows)
    return len(fact_rows)


def _insert_research_per_enrolment(conn) -> int:
    rows = conn.execute(
        """
        SELECT research.provider_id, research.reporting_year,
               research.value AS research_income, enrolments.value AS enrolments
        FROM facts research
        JOIN facts enrolments
          ON enrolments.provider_id = research.provider_id
         AND enrolments.reporting_year = research.reporting_year
        WHERE research.metric_id = 'herdc_research_income_total'
          AND enrolments.metric_id = 'student_total_enrolments'
          AND enrolments.value != 0
        """
    ).fetchall()
    fact_rows = []
    for provider_id, year, research_income, enrolments in rows:
        dimensions_json = json_dumps({"calculation": "research_income_per_enrolment"})
        value = float(research_income) / float(enrolments)
        fact_rows.append(_fact_tuple(provider_id, "calc_research_income_per_enrolment", year, "Calculated", value, "AUD per student", dimensions_json))
    _insert_fact_rows(conn, fact_rows)
    return len(fact_rows)


def _fact_tuple(
    provider_id: str,
    metric_id: str,
    year: int,
    scope: str,
    value: float,
    unit: str,
    dimensions_json: str,
) -> tuple[object, ...]:
    return (
        stable_fact_id(SOURCE_FILE_ID, provider_id, metric_id, year, scope, dimensions_json),
        provider_id,
        metric_id,
        SOURCE_FILE_ID,
        year,
        f"{year}-01-01",
        f"{year}-12-31",
        scope,
        value,
        unit,
        0,
        "Calculated metric",
        "Calculated metric",
        dimensions_json,
    )


def _insert_fact_rows(conn, rows: list[tuple[object, ...]]) -> None:
    if not rows:
        return
    conn.executemany(
        """
        INSERT INTO facts (
            fact_id, provider_id, metric_id, source_file_id, reporting_year,
            period_start, period_end, dimension_scope, value, unit,
            source_row_number, source_provider_name, source_line_item,
            dimensions_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


if __name__ == "__main__":
    print(json.dumps(calculate_metrics(), indent=2))

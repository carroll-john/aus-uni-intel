from __future__ import annotations

from typing import Any

import duckdb

from uni_intel.api.repositories.base import rows_to_dicts, single_value


def summary(conn: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    return {
        "latest_year": single_value(conn, "SELECT MAX(reporting_year) FROM facts"),
        "providers": single_value(
            conn,
            "SELECT COUNT(*) FROM providers WHERE provider_type = 'university' AND is_public = TRUE",
        ),
        "metrics": single_value(conn, "SELECT COUNT(*) FROM metrics"),
        "facts": single_value(conn, "SELECT COUNT(*) FROM facts"),
        "sources": single_value(conn, "SELECT COUNT(*) FROM source_files"),
    }


def kpis(conn: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    return rows_to_dicts(
        conn,
        """
        WITH kpi(metric_id, label, scope, aggregator) AS (
            VALUES
            ('finance_total_revenues_from_continuing_operations_including_deferred_superannuation', 'Sector revenue', 'Total Institution', 'sector'),
            ('student_total_enrolments', 'Student enrolments', 'Student', 'sum'),
            ('herdc_research_income_total', 'Research income', 'HERDC', 'sum'),
            ('qilt_overall_educational_experience_positive_rating', 'Average undergraduate experience', 'QILT undergraduate', 'avg')
        )
        SELECT k.label AS metric_name, f.metric_id, m.unit, f.reporting_year,
               k.scope AS dimension_scope,
               CASE
                 WHEN k.aggregator = 'sector' THEN MAX(CASE WHEN f.provider_id = 'sector_all_pub2' THEN f.value END)
                 WHEN k.aggregator = 'avg' THEN AVG(CASE WHEN p.provider_type = 'university' THEN f.value END)
                 ELSE SUM(CASE WHEN p.provider_type = 'university' THEN f.value ELSE 0 END)
               END AS value
        FROM kpi k
        JOIN facts f ON f.metric_id = k.metric_id AND f.dimension_scope = k.scope
        JOIN metrics m ON m.metric_id = f.metric_id
        JOIN providers p ON p.provider_id = f.provider_id
        WHERE f.reporting_year = (SELECT MAX(reporting_year) FROM facts WHERE metric_id = k.metric_id)
        GROUP BY k.label, f.metric_id, m.unit, f.reporting_year, k.aggregator, k.scope
        ORDER BY k.label
        """,
    )


def top_rankings(conn: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    return rows_to_dicts(
        conn,
        """
        WITH rank_metric(metric_id, scope) AS (
            VALUES
            ('finance_total_revenues_from_continuing_operations_including_deferred_superannuation', 'Total Institution'),
            ('herdc_research_income_total', 'HERDC'),
            ('student_total_enrolments', 'Student')
        )
        SELECT p.provider_id, p.provider_name, f.metric_id, m.metric_name,
               f.value, f.unit, f.reporting_year, f.dimension_scope
        FROM rank_metric r
        JOIN facts f ON f.metric_id = r.metric_id AND f.dimension_scope = r.scope
        JOIN providers p ON p.provider_id = f.provider_id
        JOIN metrics m ON m.metric_id = f.metric_id
        WHERE p.provider_type = 'university'
          AND f.reporting_year = (SELECT MAX(reporting_year) FROM facts WHERE facts.metric_id = f.metric_id)
        QUALIFY ROW_NUMBER() OVER (PARTITION BY f.metric_id ORDER BY f.value DESC) <= 5
        ORDER BY f.metric_id, f.value DESC
        """,
    )


def latest_quality(conn: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    return rows_to_dicts(
        conn,
        """
        SELECT check_name, status, severity, observed_value, expected_value,
               details, created_at
        FROM data_quality_checks
        ORDER BY created_at DESC
        LIMIT 12
        """,
    )

from __future__ import annotations

import duckdb

from uni_intel.api.repositories.base import rows_to_dicts, single_value

_METRIC_COLUMNS = """
    metric_id, metric_name, metric_group, unit, value_type,
    definition, source_agency, source_dataset, source_table,
    source_line_item, is_calculated, calculation_method
"""


def list_metrics(conn: duckdb.DuckDBPyConnection) -> list[dict[str, object]]:
    return rows_to_dicts(
        conn,
        f"""
        SELECT {_METRIC_COLUMNS}
        FROM metrics
        ORDER BY metric_group, metric_name
        """,
    )


def live_metrics_by_id(
    conn: duckdb.DuckDBPyConnection,
    metric_ids: list[str],
) -> dict[str, dict[str, object]]:
    if not metric_ids:
        return {}
    placeholders = ", ".join("?" for _ in metric_ids)
    rows = rows_to_dicts(
        conn,
        f"""
        SELECT {_METRIC_COLUMNS}
        FROM metrics
        WHERE metric_id IN ({placeholders})
        """,
        list(metric_ids),
    )
    return {str(row["metric_id"]): row for row in rows}


def canonical_metric_name(conn: duckdb.DuckDBPyConnection, metric_id: str) -> str | None:
    value = single_value(conn, "SELECT metric_name FROM metrics WHERE metric_id = ?", [metric_id])
    return str(value) if value is not None else None


def distinct_years(
    conn: duckdb.DuckDBPyConnection,
    metric_ids: list[str] | None = None,
) -> list[dict[str, object]]:
    if metric_ids:
        placeholders = ", ".join("?" for _ in metric_ids)
        return rows_to_dicts(
            conn,
            f"SELECT DISTINCT reporting_year FROM facts WHERE metric_id IN ({placeholders}) ORDER BY reporting_year",
            list(metric_ids),
        )
    return rows_to_dicts(conn, "SELECT DISTINCT reporting_year FROM facts ORDER BY reporting_year")


def distinct_scopes(
    conn: duckdb.DuckDBPyConnection,
    metric_ids: list[str] | None = None,
) -> list[dict[str, object]]:
    if metric_ids:
        placeholders = ", ".join("?" for _ in metric_ids)
        return rows_to_dicts(
            conn,
            f"""
            SELECT DISTINCT dimension_scope
            FROM facts
            WHERE metric_id IN ({placeholders})
            ORDER BY dimension_scope
            """,
            list(metric_ids),
        )
    return rows_to_dicts(conn, "SELECT DISTINCT dimension_scope FROM facts ORDER BY dimension_scope")

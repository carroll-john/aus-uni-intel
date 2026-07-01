from __future__ import annotations

from typing import Any

import duckdb

from uni_intel.api.analytics import canonical_scope_qualifier, metric_filter_sql
from uni_intel.api.repositories.base import rows_to_dicts


def rankings(
    conn: duckdb.DuckDBPyConnection,
    metric_ids: list[str],
    *,
    year: int | None,
    scope: str | None,
    mission_group: str | None,
    state: str | None,
    limit: int,
    order: str,
) -> list[dict[str, Any]]:
    direction = "ASC" if order == "asc" else "DESC"
    filters = [metric_filter_sql(metric_ids), "p.provider_type = 'university'"]
    params: list[object] = list(metric_ids)
    if year is not None:
        filters.append("f.reporting_year = ?")
        params.append(year)
    if scope is not None:
        filters.append("f.dimension_scope = ?")
        params.append(scope)
    if mission_group is not None:
        filters.append("p.mission_group = ?")
        params.append(mission_group)
    if state is not None:
        filters.append("p.state = ?")
        params.append(state)
    scope_qualifier = canonical_scope_qualifier(scope, ["f.provider_id", "f.metric_id", "f.reporting_year"])
    params.append(limit)
    return rows_to_dicts(
        conn,
        f"""
        SELECT p.provider_id, p.provider_name, p.state, f.metric_id,
               m.metric_name, f.value, f.unit, f.reporting_year,
               f.dimension_scope, m.definition, m.source_dataset,
               m.is_calculated, m.calculation_method
        FROM facts f
        JOIN providers p USING (provider_id)
        JOIN metrics m USING (metric_id)
        WHERE {" AND ".join(filters)}
        {scope_qualifier}
        ORDER BY f.value {direction}
        LIMIT ?
        """,
        params,
    )


def benchmarks(
    conn: duckdb.DuckDBPyConnection,
    metric_ids: list[str],
    *,
    group_by: str,
    year: int | None,
    scope: str | None,
    mission_group: str | None,
    state: str | None,
) -> list[dict[str, Any]]:
    group_column = "p.mission_group" if group_by == "mission_group" else "p.state"
    filters = [
        metric_filter_sql(metric_ids),
        "p.provider_type = 'university'",
        f"{group_column} IS NOT NULL",
        f"{group_column} <> ''",
    ]
    params: list[object] = list(metric_ids)
    if year is not None:
        filters.append("f.reporting_year = ?")
        params.append(year)
    if scope is not None:
        filters.append("f.dimension_scope = ?")
        params.append(scope)
    if mission_group is not None:
        filters.append("p.mission_group = ?")
        params.append(mission_group)
    if state is not None:
        filters.append("p.state = ?")
        params.append(state)
    scope_qualifier = canonical_scope_qualifier(scope, ["f.provider_id", "f.reporting_year"])
    return rows_to_dicts(
        conn,
        f"""
        WITH base AS (
            SELECT {group_column} AS group_value,
                   f.reporting_year AS reporting_year,
                   f.value AS value,
                   f.unit AS unit
            FROM facts f
            JOIN providers p USING (provider_id)
            JOIN metrics m USING (metric_id)
            WHERE {" AND ".join(filters)}
            {scope_qualifier}
        )
        SELECT group_value,
               reporting_year,
               AVG(value) AS average,
               MEDIAN(value) AS median,
               MIN(value) AS minimum,
               MAX(value) AS maximum,
               COUNT(*) AS provider_count,
               ANY_VALUE(unit) AS unit
        FROM base
        GROUP BY group_value, reporting_year
        ORDER BY reporting_year, group_value
        """,
        params,
    )


def compare(
    conn: duckdb.DuckDBPyConnection,
    provider_list: list[str],
    query_metric_list: list[str],
    *,
    year: int | None,
    scope: str | None,
) -> list[dict[str, Any]]:
    provider_placeholders = ", ".join("?" for _ in provider_list)
    metric_placeholders = ", ".join("?" for _ in query_metric_list)
    filters = [
        f"f.provider_id IN ({provider_placeholders})",
        f"f.metric_id IN ({metric_placeholders})",
    ]
    params: list[object] = [*provider_list, *query_metric_list]
    if year is not None:
        filters.append("f.reporting_year = ?")
        params.append(year)
    if scope is not None:
        filters.append("f.dimension_scope = ?")
        params.append(scope)
    scope_qualifier = canonical_scope_qualifier(scope, ["f.provider_id", "f.metric_id", "f.reporting_year"])
    return rows_to_dicts(
        conn,
        f"""
        SELECT p.provider_id, p.provider_name, f.metric_id, m.metric_name,
               f.value, f.unit, f.reporting_year, f.dimension_scope
        FROM facts f
        JOIN providers p USING (provider_id)
        JOIN metrics m USING (metric_id)
        WHERE {" AND ".join(filters)}
        {scope_qualifier}
        ORDER BY p.provider_name, m.metric_name
        """,
        params,
    )


def trends(
    conn: duckdb.DuckDBPyConnection,
    metric_ids: list[str],
    *,
    provider_id: str | None,
    scope: str | None,
) -> list[dict[str, Any]]:
    filters = [metric_filter_sql(metric_ids)]
    params: list[object] = list(metric_ids)
    if provider_id:
        filters.append("f.provider_id = ?")
        params.append(provider_id)
    if scope:
        filters.append("f.dimension_scope = ?")
        params.append(scope)
    scope_qualifier = canonical_scope_qualifier(scope, ["f.provider_id", "f.metric_id", "f.reporting_year"])
    return rows_to_dicts(
        conn,
        f"""
        SELECT f.reporting_year, p.provider_id, p.provider_name, f.metric_id,
               m.metric_name, f.dimension_scope, f.value, f.unit
        FROM facts f
        JOIN providers p USING (provider_id)
        JOIN metrics m USING (metric_id)
        WHERE {" AND ".join(filters)}
        {scope_qualifier}
        ORDER BY p.provider_name, f.reporting_year
        """,
        params,
    )

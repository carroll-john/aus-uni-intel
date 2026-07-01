from __future__ import annotations

import duckdb

from uni_intel.api.analytics import canonical_scope_qualifier, metric_filter_sql
from uni_intel.api.repositories.base import rows_to_dicts

_PROVIDER_COLUMNS = """
    provider_id, provider_name, state, provider_type, is_public,
    website, mission_group, table_classification
"""


def list_providers(conn: duckdb.DuckDBPyConnection) -> list[dict[str, object]]:
    return rows_to_dicts(
        conn,
        f"""
        SELECT {_PROVIDER_COLUMNS}
        FROM providers
        ORDER BY provider_type, provider_name
        """,
    )


def get_provider(conn: duckdb.DuckDBPyConnection, provider_id: str) -> dict[str, object] | None:
    rows = rows_to_dicts(
        conn,
        f"SELECT {_PROVIDER_COLUMNS} FROM providers WHERE provider_id = ?",
        [provider_id],
    )
    return rows[0] if rows else None


def provider_facts(
    conn: duckdb.DuckDBPyConnection,
    provider_id: str,
    year: int | None,
    scope: str | None,
) -> list[dict[str, object]]:
    filters = ["f.provider_id = ?"]
    params: list[object] = [provider_id]
    if year is not None:
        filters.append("f.reporting_year = ?")
        params.append(year)
    if scope is not None:
        filters.append("f.dimension_scope = ?")
        params.append(scope)
    return rows_to_dicts(
        conn,
        f"""
        SELECT f.reporting_year, f.dimension_scope, f.metric_id, m.metric_name,
               m.metric_group, f.value, f.unit, f.source_provider_name,
               f.source_line_item, f.dimensions_json, m.definition,
               m.source_agency, m.source_dataset, m.source_table,
               m.is_calculated, m.calculation_method
        FROM facts f
        JOIN metrics m USING (metric_id)
        WHERE {" AND ".join(filters)}
        ORDER BY m.metric_group, m.metric_name
        """,
        params,
    )


def metric_insight_rows(
    conn: duckdb.DuckDBPyConnection,
    metric_ids: list[str],
    scope: str | None,
) -> list[dict[str, object]]:
    filters = [metric_filter_sql(metric_ids), "p.provider_type = 'university'"]
    params: list[object] = list(metric_ids)
    if scope is not None:
        filters.append("f.dimension_scope = ?")
        params.append(scope)
    scope_qualifier = canonical_scope_qualifier(scope, ["f.provider_id", "f.reporting_year"])
    return rows_to_dicts(
        conn,
        f"""
        SELECT p.provider_id, p.provider_name, p.state, p.mission_group,
               p.table_classification, f.metric_id, m.metric_name,
               m.metric_group, f.reporting_year, f.dimension_scope,
               f.value, f.unit, m.definition, m.source_agency,
               m.source_dataset, m.source_table, m.source_line_item,
               m.is_calculated, m.calculation_method, s.source_name,
               s.source_url, s.license, s.publication_date
        FROM facts f
        JOIN providers p USING (provider_id)
        JOIN metrics m USING (metric_id)
        JOIN source_files s USING (source_file_id)
        WHERE {" AND ".join(filters)}
        {scope_qualifier}
        ORDER BY f.reporting_year, p.provider_name
        """,
        params,
    )

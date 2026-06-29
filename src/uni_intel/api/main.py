from __future__ import annotations

import gzip
import os
from pathlib import Path
import shutil

import duckdb
from fastapi import FastAPI, HTTPException, Query

from uni_intel.api.metric_catalog import CURATED_METRIC_CATALOG, CatalogMetric
from uni_intel.config import DB_ARCHIVE_PATH, DB_PATH

app = FastAPI(title="Australian University Intelligence API")

TOTAL_REVENUE_METRIC_ID = "finance_total_revenues_from_continuing_operations_including_deferred_superannuation"
LEGACY_TOTAL_REVENUE_METRIC_ID = "finance_total_revenues_from_continuing_operations"
OVERSEAS_FEE_INCOME_METRIC_ID = "finance_international_students"
LEGACY_OVERSEAS_FEE_INCOME_METRIC_ID = "finance_fee_paying_overseas_students"
METRIC_HISTORY_ALIASES = {
    TOTAL_REVENUE_METRIC_ID: [TOTAL_REVENUE_METRIC_ID, LEGACY_TOTAL_REVENUE_METRIC_ID],
    OVERSEAS_FEE_INCOME_METRIC_ID: [
        OVERSEAS_FEE_INCOME_METRIC_ID,
        LEGACY_OVERSEAS_FEE_INCOME_METRIC_ID,
    ],
}


def _connect() -> duckdb.DuckDBPyConnection:
    path = _resolve_db_path()
    return duckdb.connect(str(path), read_only=True)


def _resolve_db_path() -> Path:
    path = Path(DB_PATH)
    if path.exists():
        return path

    archive_path = Path(DB_ARCHIVE_PATH)
    runtime_path = Path(os.environ.get("UNI_INTEL_RUNTIME_DB_PATH", "/tmp/university_intel.duckdb"))
    if archive_path.exists():
        if not runtime_path.exists():
            runtime_path.parent.mkdir(parents=True, exist_ok=True)
            with gzip.open(archive_path, "rb") as source, runtime_path.open("wb") as target:
                shutil.copyfileobj(source, target)
        return runtime_path

    raise HTTPException(
        status_code=503,
        detail="DuckDB warehouse not found. Run `make ingest-all` first.",
    )


def _rows_to_dicts(conn: duckdb.DuckDBPyConnection, query: str, params: list[object] | None = None):
    result = conn.execute(query, params or [])
    columns = [desc[0] for desc in result.description]
    return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]


def _single_value(conn: duckdb.DuckDBPyConnection, query: str, params: list[object] | None = None):
    row = conn.execute(query, params or []).fetchone()
    return row[0] if row else None


def _metric_ids_for_query(metric_id: str) -> list[str]:
    return METRIC_HISTORY_ALIASES.get(metric_id, [metric_id])


def _metric_filter_sql(metric_ids: list[str]) -> str:
    placeholders = ", ".join("?" for _ in metric_ids)
    return f"f.metric_id IN ({placeholders})"


def _canonical_metric_name(conn: duckdb.DuckDBPyConnection, metric_id: str) -> str | None:
    return _single_value(conn, "SELECT metric_name FROM metrics WHERE metric_id = ?", [metric_id])


def _normalize_metric_rows(
    rows: list[dict[str, object]],
    requested_metric_id: str,
    canonical_metric_name: str | None,
) -> list[dict[str, object]]:
    alias_metric_ids = METRIC_HISTORY_ALIASES.get(requested_metric_id)
    if not alias_metric_ids:
        return rows

    for row in rows:
        if row.get("metric_id") not in alias_metric_ids:
            continue
        row["metric_id"] = requested_metric_id
        if canonical_metric_name:
            row["metric_name"] = canonical_metric_name
    return rows


def _canonical_scope_qualifier(scope: str | None, partition_columns: list[str]) -> str:
    if scope is not None:
        return ""

    partition_sql = ", ".join(partition_columns)
    return f"""
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY {partition_sql}
            ORDER BY
                CASE
                    WHEN f.dimension_scope = 'Total Institution' THEN 0
                    WHEN f.dimension_scope = 'Student' THEN 0
                    WHEN f.dimension_scope = 'HERDC' THEN 0
                    WHEN f.dimension_scope = 'QILT undergraduate' THEN 0
                    WHEN f.dimension_scope = 'Calculated' THEN 0
                    WHEN f.dimension_scope = 'HED' THEN 1
                    WHEN f.dimension_scope LIKE 'QILT %' THEN 1
                    ELSE 2
                END,
                f.dimension_scope
        ) = 1
        """


@app.get("/overview")
def overview():
    conn = _connect()
    try:
        latest_year = _single_value(conn, "SELECT MAX(reporting_year) FROM facts")
        summary = {
            "latest_year": latest_year,
            "providers": _single_value(
                conn,
                "SELECT COUNT(*) FROM providers WHERE provider_type = 'university' AND is_public = TRUE",
            ),
            "metrics": _single_value(conn, "SELECT COUNT(*) FROM metrics"),
            "facts": _single_value(conn, "SELECT COUNT(*) FROM facts"),
            "sources": _single_value(conn, "SELECT COUNT(*) FROM source_files"),
        }
        kpis = _rows_to_dicts(
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
        top_rankings = _rows_to_dicts(
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
            """
        )
        latest_quality = _rows_to_dicts(
            conn,
            """
            SELECT check_name, status, severity, observed_value, expected_value,
                   details, created_at
            FROM data_quality_checks
            ORDER BY created_at DESC
            LIMIT 12
            """,
        )
        return {"summary": summary, "kpis": kpis, "top_rankings": top_rankings, "quality": latest_quality}
    finally:
        conn.close()


@app.get("/providers")
def providers():
    conn = _connect()
    try:
        return _rows_to_dicts(
            conn,
            """
            SELECT provider_id, provider_name, state, provider_type, is_public, website
            FROM providers
            ORDER BY provider_type, provider_name
            """,
        )
    finally:
        conn.close()


@app.get("/metrics")
def metrics():
    conn = _connect()
    try:
        return _rows_to_dicts(
            conn,
            """
            SELECT metric_id, metric_name, metric_group, unit, value_type,
                   definition, source_agency, source_dataset, source_table,
                   source_line_item, is_calculated, calculation_method
            FROM metrics
            ORDER BY metric_group, metric_name
            """,
        )
    finally:
        conn.close()


@app.get("/metric-catalog")
def metric_catalog(include_missing: bool = Query(False)):
    conn = _connect()
    try:
        metric_ids = [item.metric_id for item in CURATED_METRIC_CATALOG if item.metric_id]
        live_metrics = {}
        if metric_ids:
            placeholders = ", ".join("?" for _ in metric_ids)
            rows = _rows_to_dicts(
                conn,
                f"""
                SELECT metric_id, metric_name, metric_group, unit, value_type,
                       definition, source_agency, source_dataset, source_table,
                       source_line_item, is_calculated, calculation_method
                FROM metrics
                WHERE metric_id IN ({placeholders})
                """,
                metric_ids,
            )
            live_metrics = {row["metric_id"]: row for row in rows}

        catalog_rows = []
        for item in CURATED_METRIC_CATALOG:
            live = live_metrics.get(item.metric_id)
            if item.source_status == "available" and live is None and not include_missing:
                continue
            if item.source_status != "available" and not include_missing:
                continue
            catalog_rows.append(_catalog_row(item, live))
        return catalog_rows
    finally:
        conn.close()


def _catalog_row(item: CatalogMetric, live: dict[str, object] | None) -> dict[str, object]:
    if live:
        return {
            **live,
            "metric_name": item.label,
            "raw_metric_name": live["metric_name"],
            "metric_group": item.catalog_group,
            "raw_metric_group": live["metric_group"],
            "catalog_group": item.catalog_group,
            "catalog_item_id": item.item_id,
            "preferred_scope": item.preferred_scope,
            "source_status": item.source_status,
            "source_note": item.source_note,
            "selectable": True,
        }
    return {
        "metric_id": None,
        "metric_name": item.label,
        "raw_metric_name": None,
        "metric_group": item.catalog_group,
        "raw_metric_group": None,
        "catalog_group": item.catalog_group,
        "catalog_item_id": item.item_id,
        "preferred_scope": item.preferred_scope,
        "source_status": "missing" if item.source_status == "available" else item.source_status,
        "source_note": item.source_note,
        "unit": "",
        "value_type": "",
        "definition": item.source_note,
        "source_agency": "",
        "source_dataset": "Not available yet",
        "source_table": None,
        "source_line_item": None,
        "is_calculated": item.source_status == "calculated_needed",
        "calculation_method": None,
        "selectable": False,
    }


@app.get("/years")
def years(metric_id: str | None = None):
    conn = _connect()
    try:
        if metric_id:
            metric_ids = _metric_ids_for_query(metric_id)
            placeholders = ", ".join("?" for _ in metric_ids)
            return _rows_to_dicts(
                conn,
                f"SELECT DISTINCT reporting_year FROM facts WHERE metric_id IN ({placeholders}) ORDER BY reporting_year",
                metric_ids,
            )
        return _rows_to_dicts(
            conn,
            "SELECT DISTINCT reporting_year FROM facts ORDER BY reporting_year",
        )
    finally:
        conn.close()


@app.get("/scopes")
def scopes(metric_id: str | None = None):
    conn = _connect()
    try:
        if metric_id:
            metric_ids = _metric_ids_for_query(metric_id)
            placeholders = ", ".join("?" for _ in metric_ids)
            return _rows_to_dicts(
                conn,
                f"""
                SELECT DISTINCT dimension_scope
                FROM facts
                WHERE metric_id IN ({placeholders})
                ORDER BY dimension_scope
                """,
                metric_ids,
            )
        return _rows_to_dicts(
            conn,
            "SELECT DISTINCT dimension_scope FROM facts ORDER BY dimension_scope",
        )
    finally:
        conn.close()


@app.get("/provider/{provider_id}/profile")
def provider_profile(
    provider_id: str,
    year: int | None = Query(None),
    scope: str | None = Query(None),
):
    conn = _connect()
    try:
        provider = _rows_to_dicts(
            conn,
            """
            SELECT provider_id, provider_name, state, provider_type, is_public, website
            FROM providers
            WHERE provider_id = ?
            """,
            [provider_id],
        )
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        filters = ["f.provider_id = ?"]
        params: list[object] = [provider_id]
        if year is not None:
            filters.append("f.reporting_year = ?")
            params.append(year)
        if scope is not None:
            filters.append("f.dimension_scope = ?")
            params.append(scope)
        facts = _rows_to_dicts(
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
        return {"provider": provider[0], "facts": facts}
    finally:
        conn.close()


@app.get("/rankings")
def rankings(
    metric_id: str,
    year: int | None = Query(None),
    scope: str | None = Query(None),
    limit: int = Query(25, ge=1, le=100),
    order: str = Query("desc", pattern="^(asc|desc)$"),
):
    conn = _connect()
    try:
        direction = "ASC" if order == "asc" else "DESC"
        metric_ids = _metric_ids_for_query(metric_id)
        filters = [_metric_filter_sql(metric_ids), "p.provider_type = 'university'"]
        params: list[object] = list(metric_ids)
        if year is not None:
            filters.append("f.reporting_year = ?")
            params.append(year)
        if scope is not None:
            filters.append("f.dimension_scope = ?")
            params.append(scope)
        scope_qualifier = _canonical_scope_qualifier(scope, ["f.provider_id", "f.metric_id", "f.reporting_year"])
        params.append(limit)
        rows = _rows_to_dicts(
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
        return _normalize_metric_rows(rows, metric_id, _canonical_metric_name(conn, metric_id))
    finally:
        conn.close()


@app.get("/compare")
def compare(
    provider_ids: str = Query(..., description="Comma-separated provider IDs"),
    metric_ids: str = Query(..., description="Comma-separated metric IDs"),
    year: int | None = Query(None),
    scope: str | None = Query(None),
):
    provider_list = [item.strip() for item in provider_ids.split(",") if item.strip()]
    metric_list = [item.strip() for item in metric_ids.split(",") if item.strip()]
    if not provider_list or not metric_list:
        raise HTTPException(status_code=400, detail="provider_ids and metric_ids are required")

    provider_placeholders = ", ".join("?" for _ in provider_list)
    query_metric_list = [alias for metric_id in metric_list for alias in _metric_ids_for_query(metric_id)]
    metric_placeholders = ", ".join("?" for _ in query_metric_list)
    filters = [
        f"f.provider_id IN ({provider_placeholders})",
        f"f.metric_id IN ({metric_placeholders})",
    ]
    params: list[object] = provider_list + query_metric_list
    if year is not None:
        filters.append("f.reporting_year = ?")
        params.append(year)
    if scope is not None:
        filters.append("f.dimension_scope = ?")
        params.append(scope)
    scope_qualifier = _canonical_scope_qualifier(scope, ["f.provider_id", "f.metric_id", "f.reporting_year"])

    conn = _connect()
    try:
        rows = _rows_to_dicts(
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
        for requested_metric_id in metric_list:
            rows = _normalize_metric_rows(rows, requested_metric_id, _canonical_metric_name(conn, requested_metric_id))
        return rows
    finally:
        conn.close()


@app.get("/sources")
def sources():
    conn = _connect()
    try:
        return _rows_to_dicts(
            conn,
            """
            SELECT source_file_id, dataset_id, source_name, source_url, local_path,
                   file_format, reporting_year, downloaded_at, checksum_sha256,
                   row_count, license, publication_date, notes
            FROM source_files
            ORDER BY downloaded_at DESC
            """,
        )
    finally:
        conn.close()


@app.get("/trends")
def trends(
    metric_id: str,
    provider_id: str | None = None,
    scope: str | None = None,
):
    conn = _connect()
    try:
        metric_ids = _metric_ids_for_query(metric_id)
        filters = [_metric_filter_sql(metric_ids)]
        params: list[object] = list(metric_ids)
        if provider_id:
            filters.append("f.provider_id = ?")
            params.append(provider_id)
        if scope:
            filters.append("f.dimension_scope = ?")
            params.append(scope)
        scope_qualifier = _canonical_scope_qualifier(scope, ["f.provider_id", "f.metric_id", "f.reporting_year"])
        rows = _rows_to_dicts(
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
        return _normalize_metric_rows(rows, metric_id, _canonical_metric_name(conn, metric_id))
    finally:
        conn.close()


@app.get("/quality")
def quality(limit: int = Query(100, ge=1, le=500)):
    conn = _connect()
    try:
        return _rows_to_dicts(
            conn,
            """
            SELECT q.run_id, q.source_file_id, s.source_name, q.check_name,
                   q.status, q.severity, q.observed_value, q.expected_value,
                   q.details, q.created_at
            FROM data_quality_checks q
            LEFT JOIN source_files s ON s.source_file_id = q.source_file_id
            ORDER BY q.created_at DESC
            LIMIT ?
            """,
            [limit],
        )
    finally:
        conn.close()

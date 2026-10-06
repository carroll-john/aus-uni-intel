"""Read-only Data Picture Studio queries.

Reuse the refactored route handlers with an explicit warehouse cursor and
explicit optional arguments, avoiding FastAPI dependency and Query sentinels
in direct calls. Additional provenance queries share the same DB resolution.
"""

from __future__ import annotations

from contextlib import closing
from typing import Any

from uni_intel.api import analytics
from uni_intel.api.deps import connect_read_only
from uni_intel.api.repositories.base import rows_to_dicts
from uni_intel.api.routers import benchmarks, compare, metrics, providers, rankings, sources, trends


def get_providers() -> list[dict[str, Any]]:
    with closing(connect_read_only()) as conn:
        return providers.providers(conn=conn)


def get_metric_catalog(*, include_missing: bool = True) -> list[dict[str, Any]]:
    with closing(connect_read_only()) as conn:
        return metrics.metric_catalog(include_missing=include_missing, conn=conn)


def get_years(*, metric_id: str | None = None) -> list[dict[str, Any]]:
    with closing(connect_read_only()) as conn:
        return metrics.years(metric_id=metric_id, conn=conn)


def get_rankings(
    metric_id: str,
    *,
    year: int | None = None,
    scope: str | None = None,
    mission_group: str | None = None,
    state: str | None = None,
    limit: int = 25,
    order: str = "desc",
) -> list[dict[str, Any]]:
    with closing(connect_read_only()) as conn:
        return rankings.rankings(
            metric_id=metric_id,
            year=year,
            scope=scope,
            mission_group=mission_group,
            state=state,
            limit=limit,
            order=order,
            conn=conn,
        )


def get_benchmarks(
    metric_id: str,
    *,
    year: int | None = None,
    scope: str | None = None,
    group_by: str = "mission_group",
    mission_group: str | None = None,
    state: str | None = None,
) -> dict[str, Any]:
    with closing(connect_read_only()) as conn:
        return benchmarks.benchmarks(
            metric_id=metric_id,
            year=year,
            scope=scope,
            group_by=group_by,
            mission_group=mission_group,
            state=state,
            conn=conn,
        )


def get_compare(
    provider_ids: list[str],
    metric_ids: list[str],
    *,
    year: int | None = None,
    scope: str | None = None,
) -> list[dict[str, Any]]:
    with closing(connect_read_only()) as conn:
        return compare.compare(
            provider_ids=",".join(provider_ids), metric_ids=",".join(metric_ids), year=year, scope=scope, conn=conn
        )


def get_trends(
    metric_id: str,
    *,
    provider_id: str | None = None,
    scope: str | None = None,
) -> list[dict[str, Any]]:
    with closing(connect_read_only()) as conn:
        return trends.trends(metric_id=metric_id, provider_id=provider_id, scope=scope, conn=conn)


def get_quality(*, limit: int = 100) -> list[dict[str, Any]]:
    with closing(connect_read_only()) as conn:
        return sources.quality(limit=limit, conn=conn)


def get_sources() -> list[dict[str, Any]]:
    with closing(connect_read_only()) as conn:
        return sources.sources(conn=conn)


def get_source_trace_for_metric(
    metric_id: str,
    *,
    year: int | None = None,
) -> list[dict[str, Any]]:
    """Distinct source files (with dataset name) backing a metric's facts.

    Not exposed by any existing endpoint in this exact joined/deduped shape,
    so this runs its own small parameterized, read-only query rather than
    stitching it together from several endpoint calls.
    """
    metric_ids = analytics.metric_ids_for_query(metric_id)  # noqa: SLF001
    filters = ["f.metric_id IN ({})".format(", ".join("?" for _ in metric_ids))]
    params: list[object] = list(metric_ids)
    if year is not None:
        filters.append("f.reporting_year = ?")
        params.append(year)

    conn = connect_read_only()
    try:
        return rows_to_dicts(
            conn,
            f"""
            SELECT DISTINCT s.source_file_id, s.source_name, s.source_url,
                   d.dataset_name, s.license, s.publication_date, f.reporting_year
            FROM facts f
            JOIN source_files s USING (source_file_id)
            LEFT JOIN source_datasets d ON d.dataset_id = s.dataset_id
            WHERE {" AND ".join(filters)}
            ORDER BY f.reporting_year DESC, s.source_name
            """,
            params,
        )
    finally:
        conn.close()


def get_quality_for_metric(
    metric_id: str,
    *,
    year: int | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Quality checks tied to the source files that back a metric's facts."""
    metric_ids = analytics.metric_ids_for_query(metric_id)  # noqa: SLF001
    filters = ["f.metric_id IN ({})".format(", ".join("?" for _ in metric_ids))]
    params: list[object] = list(metric_ids)
    if year is not None:
        filters.append("f.reporting_year = ?")
        params.append(year)
    params.append(limit)

    conn = connect_read_only()
    try:
        return rows_to_dicts(
            conn,
            f"""
            SELECT DISTINCT q.check_name, q.status, q.severity, q.observed_value,
                   q.expected_value, q.details, q.created_at
            FROM data_quality_checks q
            JOIN source_files s ON s.source_file_id = q.source_file_id
            JOIN facts f ON f.source_file_id = s.source_file_id
            WHERE {" AND ".join(filters)}
            ORDER BY q.created_at DESC
            LIMIT ?
            """,
            params,
        )
    finally:
        conn.close()


def get_latest_year(*, metric_id: str | None = None) -> int | None:
    years = get_years(metric_id=metric_id)
    if not years:
        return None
    return max(int(row["reporting_year"]) for row in years)

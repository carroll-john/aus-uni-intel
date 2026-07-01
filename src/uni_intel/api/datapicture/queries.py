"""Read-only data access for the Data Picture Studio.

Every function here either (a) calls straight into the plain Python
functions that back the existing ``/rankings``, ``/benchmarks``, ``/compare``,
``/trends``, ``/metric-catalog``, ``/quality`` and ``/sources`` routes in
``uni_intel.api.main`` -- reusing their SQL instead of duplicating it -- or
(b) runs a small, additional, parameterized, read-only lookup needed for
provenance (source trace / quality-for-metric) that those routes do not
already expose in the shape this feature needs.

FastAPI route decorators return the wrapped function unchanged, so calling
``api_main.rankings(...)`` etc. directly is a normal Python function call,
not an HTTP round trip. Every optional parameter is always passed explicitly
here: several of those functions default optional parameters to a FastAPI
``Query(...)`` sentinel object (not ``None``), which would be misinterpreted
as a real value if omitted from a direct call.
"""

from __future__ import annotations

import duckdb

from uni_intel.api import main as api_main


def connect_read_only() -> duckdb.DuckDBPyConnection:
    """Open a fresh read-only connection using the same resolution as the API."""
    return api_main._connect()  # noqa: SLF001 - intentional reuse of the API's DB resolution


def get_providers() -> list[dict[str, object]]:
    return api_main.providers()


def get_metric_catalog(*, include_missing: bool = True) -> list[dict[str, object]]:
    return api_main.metric_catalog(include_missing=include_missing)


def get_years(*, metric_id: str | None = None) -> list[dict[str, object]]:
    return api_main.years(metric_id=metric_id)


def get_rankings(
    metric_id: str,
    *,
    year: int | None = None,
    scope: str | None = None,
    mission_group: str | None = None,
    state: str | None = None,
    limit: int = 25,
    order: str = "desc",
) -> list[dict[str, object]]:
    return api_main.rankings(
        metric_id=metric_id,
        year=year,
        scope=scope,
        mission_group=mission_group,
        state=state,
        limit=limit,
        order=order,
    )


def get_benchmarks(
    metric_id: str,
    *,
    year: int | None = None,
    scope: str | None = None,
    group_by: str = "mission_group",
    mission_group: str | None = None,
    state: str | None = None,
) -> dict[str, object]:
    return api_main.benchmarks(
        metric_id=metric_id,
        year=year,
        scope=scope,
        group_by=group_by,
        mission_group=mission_group,
        state=state,
    )


def get_compare(
    provider_ids: list[str],
    metric_ids: list[str],
    *,
    year: int | None = None,
    scope: str | None = None,
) -> list[dict[str, object]]:
    return api_main.compare(
        provider_ids=",".join(provider_ids),
        metric_ids=",".join(metric_ids),
        year=year,
        scope=scope,
    )


def get_trends(
    metric_id: str,
    *,
    provider_id: str | None = None,
    scope: str | None = None,
) -> list[dict[str, object]]:
    return api_main.trends(metric_id=metric_id, provider_id=provider_id, scope=scope)


def get_quality(*, limit: int = 100) -> list[dict[str, object]]:
    return api_main.quality(limit=limit)


def get_sources() -> list[dict[str, object]]:
    return api_main.sources()


def get_source_trace_for_metric(
    metric_id: str,
    *,
    year: int | None = None,
) -> list[dict[str, object]]:
    """Distinct source files (with dataset name) backing a metric's facts.

    Not exposed by any existing endpoint in this exact joined/deduped shape,
    so this runs its own small parameterized, read-only query rather than
    stitching it together from several endpoint calls.
    """
    metric_ids = api_main._metric_ids_for_query(metric_id)  # noqa: SLF001
    filters = ["f.metric_id IN ({})".format(", ".join("?" for _ in metric_ids))]
    params: list[object] = list(metric_ids)
    if year is not None:
        filters.append("f.reporting_year = ?")
        params.append(year)

    conn = connect_read_only()
    try:
        return api_main._rows_to_dicts(  # noqa: SLF001
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
) -> list[dict[str, object]]:
    """Quality checks tied to the source files that back a metric's facts."""
    metric_ids = api_main._metric_ids_for_query(metric_id)  # noqa: SLF001
    filters = ["f.metric_id IN ({})".format(", ".join("?" for _ in metric_ids))]
    params: list[object] = list(metric_ids)
    if year is not None:
        filters.append("f.reporting_year = ?")
        params.append(year)
    params.append(limit)

    conn = connect_read_only()
    try:
        return api_main._rows_to_dicts(  # noqa: SLF001
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

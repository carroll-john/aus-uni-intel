from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends, Query

from uni_intel.api import analytics
from uni_intel.api.deps import get_conn
from uni_intel.api.metric_catalog import CURATED_METRIC_CATALOG, build_catalog_rows
from uni_intel.api.repositories import metrics as repo
from uni_intel.api.schemas import CatalogEntry, Metric, ScopeRow, YearRow

router = APIRouter()


@router.get("/metrics", response_model=list[Metric])
def metrics(conn: duckdb.DuckDBPyConnection = Depends(get_conn)) -> list[dict[str, object]]:
    return repo.list_metrics(conn)


@router.get("/metric-catalog", response_model=list[CatalogEntry])
def metric_catalog(
    include_missing: bool = Query(False),
    conn: duckdb.DuckDBPyConnection = Depends(get_conn),
) -> list[dict[str, object]]:
    metric_ids = [item.metric_id for item in CURATED_METRIC_CATALOG if item.metric_id]
    live_metrics = repo.live_metrics_by_id(conn, metric_ids)
    return build_catalog_rows(live_metrics, include_missing)


@router.get("/years", response_model=list[YearRow])
def years(
    metric_id: str | None = None,
    conn: duckdb.DuckDBPyConnection = Depends(get_conn),
) -> list[dict[str, object]]:
    metric_ids = analytics.metric_ids_for_query(metric_id) if metric_id else None
    return repo.distinct_years(conn, metric_ids)


@router.get("/scopes", response_model=list[ScopeRow])
def scopes(
    metric_id: str | None = None,
    conn: duckdb.DuckDBPyConnection = Depends(get_conn),
) -> list[dict[str, object]]:
    metric_ids = analytics.metric_ids_for_query(metric_id) if metric_id else None
    return repo.distinct_scopes(conn, metric_ids)

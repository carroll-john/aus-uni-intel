from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query

from uni_intel.api import analytics
from uni_intel.api.deps import get_conn
from uni_intel.api.repositories import facts as repo
from uni_intel.api.repositories import metrics as metrics_repo
from uni_intel.api.schemas import CompareRow

router = APIRouter()


@router.get("/compare", response_model=list[CompareRow])
def compare(
    provider_ids: str = Query(..., description="Comma-separated provider IDs"),
    metric_ids: str = Query(..., description="Comma-separated metric IDs"),
    year: int | None = Query(None),
    scope: str | None = Query(None),
    conn: duckdb.DuckDBPyConnection = Depends(get_conn),
) -> list[dict[str, object]]:
    provider_list = [item.strip() for item in provider_ids.split(",") if item.strip()]
    metric_list = [item.strip() for item in metric_ids.split(",") if item.strip()]
    if not provider_list or not metric_list:
        raise HTTPException(status_code=400, detail="provider_ids and metric_ids are required")
    if len(provider_list) > analytics.MAX_COMPARE_PROVIDERS or len(metric_list) > analytics.MAX_COMPARE_METRICS:
        raise HTTPException(status_code=400, detail="Too many providers or metrics")

    query_metric_list = [alias for metric_id in metric_list for alias in analytics.metric_ids_for_query(metric_id)]
    rows = repo.compare(conn, provider_list, query_metric_list, year=year, scope=scope)
    for requested_metric_id in metric_list:
        rows = analytics.normalize_metric_rows(
            rows, requested_metric_id, metrics_repo.canonical_metric_name(conn, requested_metric_id)
        )
    return rows

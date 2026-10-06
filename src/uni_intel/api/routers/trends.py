from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends

from uni_intel.api import analytics
from uni_intel.api.deps import get_conn
from uni_intel.api.repositories import facts as repo
from uni_intel.api.repositories import metrics as metrics_repo
from uni_intel.api.schemas import TrendRow

router = APIRouter()


@router.get("/trends", response_model=list[TrendRow])
def trends(
    metric_id: str,
    provider_id: str | None = None,
    scope: str | None = None,
    conn: duckdb.DuckDBPyConnection = Depends(get_conn),
) -> list[dict[str, object]]:
    metric_ids = analytics.metric_ids_for_query(metric_id)
    rows = repo.trends(conn, metric_ids, provider_id=provider_id, scope=scope)
    return analytics.normalize_metric_rows(rows, metric_id, metrics_repo.canonical_metric_name(conn, metric_id))

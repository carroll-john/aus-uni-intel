from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends, Query

from uni_intel.api import analytics
from uni_intel.api.deps import get_conn
from uni_intel.api.repositories import facts as repo
from uni_intel.api.repositories import metrics as metrics_repo
from uni_intel.api.schemas import RankingRow

router = APIRouter()


@router.get("/rankings", response_model=list[RankingRow])
def rankings(
    metric_id: str,
    year: int | None = Query(None),
    scope: str | None = Query(None),
    mission_group: str | None = Query(None),
    state: str | None = Query(None),
    limit: int = Query(25, ge=1, le=100),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    conn: duckdb.DuckDBPyConnection = Depends(get_conn),
) -> list[dict[str, object]]:
    metric_ids = analytics.metric_ids_for_query(metric_id)
    rows = repo.rankings(
        conn,
        metric_ids,
        year=year,
        scope=scope,
        mission_group=mission_group,
        state=state,
        limit=limit,
        order=order,
    )
    return analytics.normalize_metric_rows(rows, metric_id, metrics_repo.canonical_metric_name(conn, metric_id))

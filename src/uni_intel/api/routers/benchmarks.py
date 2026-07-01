from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends, Query

from uni_intel.api import analytics
from uni_intel.api.deps import get_conn
from uni_intel.api.repositories import facts as repo
from uni_intel.api.schemas import BenchmarkResponse

router = APIRouter()


@router.get("/benchmarks", response_model=BenchmarkResponse)
def benchmarks(
    metric_id: str,
    year: int | None = Query(None),
    scope: str | None = Query(None),
    group_by: str = Query("mission_group", pattern="^(mission_group|state)$"),
    mission_group: str | None = Query(None),
    state: str | None = Query(None),
    conn: duckdb.DuckDBPyConnection = Depends(get_conn),
) -> dict[str, object]:
    """Peer-group averages for a metric, grouped by mission group or state.

    Powers the rankings reference line and the compare benchmark series. When no
    scope is supplied each provider contributes its canonical scope only, so a
    dual-sector provider is not double-counted in the group average.
    """
    metric_ids = analytics.metric_ids_for_query(metric_id)
    rows = repo.benchmarks(
        conn,
        metric_ids,
        group_by=group_by,
        year=year,
        scope=scope,
        mission_group=mission_group,
        state=state,
    )
    return {"group_by": group_by, "rows": rows}

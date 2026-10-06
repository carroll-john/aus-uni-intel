from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends

from uni_intel.api.deps import get_conn
from uni_intel.api.repositories import overview as repo

router = APIRouter()


@router.get("/overview")
def overview(conn: duckdb.DuckDBPyConnection = Depends(get_conn)) -> dict[str, object]:
    return {
        "summary": repo.summary(conn),
        "kpis": repo.kpis(conn),
        "top_rankings": repo.top_rankings(conn),
        "quality": repo.latest_quality(conn),
    }

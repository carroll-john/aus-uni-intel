from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends, Query

from uni_intel.api.deps import get_conn
from uni_intel.api.repositories import sources as repo
from uni_intel.api.schemas import QualityCheckRow, SourceFile

router = APIRouter()


@router.get("/sources", response_model=list[SourceFile])
def sources(conn: duckdb.DuckDBPyConnection = Depends(get_conn)) -> list[dict[str, object]]:
    return repo.list_sources(conn)


@router.get("/quality", response_model=list[QualityCheckRow])
def quality(
    limit: int = Query(100, ge=1, le=500),
    conn: duckdb.DuckDBPyConnection = Depends(get_conn),
) -> list[dict[str, object]]:
    return repo.list_quality_checks(conn, limit)

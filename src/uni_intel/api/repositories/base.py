from __future__ import annotations

from typing import Any

import duckdb

# DuckDB result values are dynamically typed; model rows as dict[str, Any] so
# callers can coerce (int/float/str) without per-call casts.
Row = dict[str, Any]


def rows_to_dicts(
    conn: duckdb.DuckDBPyConnection,
    query: str,
    params: list[object] | None = None,
) -> list[Row]:
    result = conn.execute(query, params or [])
    columns = [desc[0] for desc in (result.description or [])]
    return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]


def single_value(
    conn: duckdb.DuckDBPyConnection,
    query: str,
    params: list[object] | None = None,
) -> Any:
    row = conn.execute(query, params or []).fetchone()
    return row[0] if row else None

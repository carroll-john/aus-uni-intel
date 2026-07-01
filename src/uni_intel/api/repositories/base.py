from __future__ import annotations

import duckdb


def rows_to_dicts(
    conn: duckdb.DuckDBPyConnection,
    query: str,
    params: list[object] | None = None,
) -> list[dict[str, object]]:
    result = conn.execute(query, params or [])
    columns = [desc[0] for desc in (result.description or [])]
    return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]


def single_value(
    conn: duckdb.DuckDBPyConnection,
    query: str,
    params: list[object] | None = None,
) -> object:
    row = conn.execute(query, params or []).fetchone()
    return row[0] if row else None

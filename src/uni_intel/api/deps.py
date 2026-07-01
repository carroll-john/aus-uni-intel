"""FastAPI dependencies and request-scoped warehouse configuration.

``DB_PATH`` / ``DB_ARCHIVE_PATH`` live here (not in the routers) so tests can
monkeypatch a temporary warehouse and every router picks it up via
:func:`get_conn`.

A read-only DuckDB connection is opened once per resolved warehouse path and
reused across requests; each request gets an independent cursor. This avoids
re-opening the database (and re-resolving/inflating the archive) on every warm
request.
"""

from __future__ import annotations

from collections.abc import Iterator

import duckdb
from fastapi import HTTPException

from uni_intel.config import DB_ARCHIVE_PATH as _CONFIG_ARCHIVE_PATH
from uni_intel.config import DB_PATH as _CONFIG_DB_PATH
from uni_intel.db import WarehouseNotFoundError, resolve_db_path

DB_PATH = _CONFIG_DB_PATH
DB_ARCHIVE_PATH = _CONFIG_ARCHIVE_PATH

_CONNECTION_CACHE: dict[str, duckdb.DuckDBPyConnection] = {}


def _base_connection() -> duckdb.DuckDBPyConnection:
    path = resolve_db_path(DB_PATH, DB_ARCHIVE_PATH)
    key = str(path)
    conn = _CONNECTION_CACHE.get(key)
    if conn is None:
        conn = duckdb.connect(key, read_only=True)
        _CONNECTION_CACHE[key] = conn
    return conn


def get_conn() -> Iterator[duckdb.DuckDBPyConnection]:
    """Yield a read-only cursor over the warehouse, translating a missing
    warehouse into an HTTP 503."""
    try:
        base = _base_connection()
    except WarehouseNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    cursor = base.cursor()
    try:
        yield cursor
    finally:
        cursor.close()

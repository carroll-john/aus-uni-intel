"""FastAPI dependencies and request-scoped warehouse configuration.

``DB_PATH`` / ``DB_ARCHIVE_PATH`` live here (not in the routers) so tests can
monkeypatch a temporary warehouse and every router picks it up via
:func:`get_conn`.
"""

from __future__ import annotations

from collections.abc import Iterator

import duckdb
from fastapi import HTTPException

from uni_intel.config import DB_ARCHIVE_PATH as _CONFIG_ARCHIVE_PATH
from uni_intel.config import DB_PATH as _CONFIG_DB_PATH
from uni_intel.db import WarehouseNotFoundError, read_only_connection

DB_PATH = _CONFIG_DB_PATH
DB_ARCHIVE_PATH = _CONFIG_ARCHIVE_PATH


def get_conn() -> Iterator[duckdb.DuckDBPyConnection]:
    """Yield a read-only warehouse connection, translating a missing warehouse
    into an HTTP 503."""
    try:
        with read_only_connection(DB_PATH, DB_ARCHIVE_PATH) as conn:
            yield conn
    except WarehouseNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

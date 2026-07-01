from __future__ import annotations

import gzip
import os
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import duckdb

from uni_intel.config import DB_ARCHIVE_PATH, DB_PATH, SCHEMA_PATH, WAREHOUSE_DIR

DEFAULT_RUNTIME_DB_PATH = "/tmp/university_intel.duckdb"


class WarehouseNotFoundError(RuntimeError):
    """Raised when no DuckDB warehouse (file or gzip archive) can be located."""


def connect(db_path: Path | str = DB_PATH) -> duckdb.DuckDBPyConnection:
    """Open a read-write connection for ingestion, creating parent dirs."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))


def init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
    apply_lightweight_migrations(conn)


def apply_lightweight_migrations(conn: duckdb.DuckDBPyConnection) -> None:
    """Keep existing local DuckDB files compatible with additive schema changes."""
    for statement in [
        "ALTER TABLE facts ADD COLUMN IF NOT EXISTS dimensions_json TEXT DEFAULT '{}'",
        "ALTER TABLE providers ADD COLUMN IF NOT EXISTS mission_group TEXT",
        "ALTER TABLE providers ADD COLUMN IF NOT EXISTS table_classification TEXT",
    ]:
        conn.execute(statement)


def ensure_warehouse_dirs() -> None:
    WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)


def resolve_db_path(
    db_path: Path | str = DB_PATH,
    archive_path: Path | str = DB_ARCHIVE_PATH,
    runtime_path: Path | str | None = None,
) -> Path:
    """Locate a readable warehouse file.

    Prefers an existing uncompressed DuckDB file. Otherwise inflates the gzip
    archive into a runtime location once (used by serverless deployments where the
    committed archive is inflated into ``/tmp`` on cold start). Raises
    :class:`WarehouseNotFoundError` if neither is available.
    """
    path = Path(db_path)
    if path.exists():
        return path

    archive = Path(archive_path)
    runtime = Path(runtime_path or os.environ.get("UNI_INTEL_RUNTIME_DB_PATH", DEFAULT_RUNTIME_DB_PATH))
    if archive.exists():
        if not runtime.exists():
            runtime.parent.mkdir(parents=True, exist_ok=True)
            with gzip.open(archive, "rb") as source, runtime.open("wb") as target:
                shutil.copyfileobj(source, target)
        return runtime

    raise WarehouseNotFoundError("DuckDB warehouse not found. Run `make ingest-all` first.")


@contextmanager
def read_only_connection(
    db_path: Path | str = DB_PATH,
    archive_path: Path | str = DB_ARCHIVE_PATH,
) -> Iterator[duckdb.DuckDBPyConnection]:
    """Yield a read-only DuckDB connection, closing it on exit."""
    path = resolve_db_path(db_path, archive_path)
    conn = duckdb.connect(str(path), read_only=True)
    try:
        yield conn
    finally:
        conn.close()

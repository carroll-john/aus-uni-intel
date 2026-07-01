from __future__ import annotations

import gzip
import os
import shutil
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import duckdb

from uni_intel.config import DB_ARCHIVE_PATH, DB_PATH, SCHEMA_PATH, WAREHOUSE_DIR

DEFAULT_RUNTIME_DB_PATH = "/tmp/university_intel.duckdb"
DB_URL_ENV = "UNI_INTEL_DB_URL"
DOWNLOAD_TIMEOUT_SECONDS = 60


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


def _inflate_archive(archive: Path, runtime: Path) -> None:
    runtime.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(archive, "rb") as source, runtime.open("wb") as target:
        shutil.copyfileobj(source, target)


def resolve_db_path(
    db_path: Path | str = DB_PATH,
    archive_path: Path | str = DB_ARCHIVE_PATH,
    runtime_path: Path | str | None = None,
    db_url: str | None = None,
) -> Path:
    """Locate a readable warehouse file.

    Resolution order:

    1. An existing uncompressed DuckDB file at ``db_path`` (local development).
    2. A previously inflated runtime file (warm serverless invocation).
    3. The committed gzip archive, inflated once into the runtime path.
    4. A remote gzip archive named by ``db_url`` / ``UNI_INTEL_DB_URL`` (lets the
       archive be hosted off-git without changing this code path). Downloaded and
       inflated once into the runtime path.

    Raises :class:`WarehouseNotFoundError` if none are available.
    """
    path = Path(db_path)
    if path.exists():
        return path

    runtime = Path(runtime_path or os.environ.get("UNI_INTEL_RUNTIME_DB_PATH", DEFAULT_RUNTIME_DB_PATH))
    if runtime.exists():
        return runtime

    archive = Path(archive_path)
    if archive.exists():
        _inflate_archive(archive, runtime)
        return runtime

    url = db_url if db_url is not None else os.environ.get(DB_URL_ENV)
    if url:
        runtime.parent.mkdir(parents=True, exist_ok=True)
        downloaded_archive = runtime.with_suffix(runtime.suffix + ".gz")
        with (
            urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response,
            downloaded_archive.open("wb") as handle,
        ):
            shutil.copyfileobj(response, handle)
        _inflate_archive(downloaded_archive, runtime)
        return runtime

    raise WarehouseNotFoundError(
        "DuckDB warehouse not found. Run `make ingest-all`, ship the gzip archive, or set UNI_INTEL_DB_URL."
    )


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

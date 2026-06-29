from pathlib import Path

import duckdb

from uni_intel.config import DB_PATH, SCHEMA_PATH, WAREHOUSE_DIR


def connect(db_path: Path | str = DB_PATH) -> duckdb.DuckDBPyConnection:
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
    ]:
        conn.execute(statement)


def ensure_warehouse_dirs() -> None:
    WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)

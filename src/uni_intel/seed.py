import csv
from pathlib import Path
from typing import Any

import duckdb

from uni_intel.config import SEED_DIR


def _upsert(
    conn: duckdb.DuckDBPyConnection,
    table: str,
    pk_col: str,
    row: dict[str, Any],
) -> None:
    columns = list(row.keys())
    exists = conn.execute(
        f"SELECT 1 FROM {table} WHERE {pk_col} = ?",
        [row[pk_col]],
    ).fetchone()
    if exists:
        set_columns = [col for col in columns if col != pk_col]
        assignments = ", ".join(f"{col} = ?" for col in set_columns)
        params = [row[col] for col in set_columns] + [row[pk_col]]
        conn.execute(f"UPDATE {table} SET {assignments} WHERE {pk_col} = ?", params)
        return

    placeholders = ", ".join("?" for _ in columns)
    column_sql = ", ".join(columns)
    conn.execute(
        f"INSERT INTO {table} ({column_sql}) VALUES ({placeholders})",
        [row[col] for col in columns],
    )


def seed_providers(conn: duckdb.DuckDBPyConnection, seed_dir: Path = SEED_DIR) -> None:
    providers_path = seed_dir / "providers.csv"
    aliases_path = seed_dir / "provider_aliases.csv"

    with providers_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            row["is_public"] = row["is_public"].strip().lower() == "true"
            _upsert(conn, "providers", "provider_id", row)

    with aliases_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            row["confidence"] = float(row["confidence"])
            _upsert(conn, "provider_aliases", "alias", row)

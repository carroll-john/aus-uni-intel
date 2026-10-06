import gzip
from pathlib import Path

import duckdb
import pytest

from uni_intel.db import WarehouseNotFoundError, resolve_db_path


def _make_duckdb(path: Path) -> None:
    conn = duckdb.connect(str(path))
    try:
        conn.execute("CREATE TABLE t (id INTEGER)")
        conn.execute("INSERT INTO t VALUES (1)")
    finally:
        conn.close()


def _gzip(source: Path, dest: Path) -> None:
    with source.open("rb") as src, gzip.open(dest, "wb") as out:
        out.write(src.read())


def test_returns_existing_local_file(tmp_path: Path) -> None:
    db = tmp_path / "w.duckdb"
    _make_duckdb(db)
    assert resolve_db_path(db_path=db, archive_path=tmp_path / "missing.gz", runtime_path=tmp_path / "rt.duckdb") == db


def test_inflates_committed_archive(tmp_path: Path) -> None:
    db = tmp_path / "src.duckdb"
    _make_duckdb(db)
    archive = tmp_path / "w.duckdb.gz"
    _gzip(db, archive)
    runtime = tmp_path / "rt.duckdb"

    resolved = resolve_db_path(db_path=tmp_path / "absent.duckdb", archive_path=archive, runtime_path=runtime)
    assert resolved == runtime and runtime.exists()
    conn = duckdb.connect(str(resolved), read_only=True)
    try:
        assert conn.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 1
    finally:
        conn.close()


def test_downloads_from_url_when_no_local_archive(tmp_path: Path) -> None:
    db = tmp_path / "src.duckdb"
    _make_duckdb(db)
    remote_archive = tmp_path / "remote.duckdb.gz"
    _gzip(db, remote_archive)
    runtime = tmp_path / "rt.duckdb"

    resolved = resolve_db_path(
        db_path=tmp_path / "absent.duckdb",
        archive_path=tmp_path / "absent.gz",
        runtime_path=runtime,
        db_url=remote_archive.as_uri(),
    )
    assert resolved == runtime and runtime.exists()
    conn = duckdb.connect(str(resolved), read_only=True)
    try:
        assert conn.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 1
    finally:
        conn.close()


def test_raises_when_nothing_available(tmp_path: Path) -> None:
    with pytest.raises(WarehouseNotFoundError):
        resolve_db_path(
            db_path=tmp_path / "absent.duckdb",
            archive_path=tmp_path / "absent.gz",
            runtime_path=tmp_path / "absent-runtime.duckdb",
        )

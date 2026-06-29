from pathlib import Path

import duckdb
from fastapi.testclient import TestClient

from uni_intel.api import main as api_main
from uni_intel.config import SCHEMA_PATH


def test_compare_defaults_to_one_canonical_scope_per_provider(tmp_path: Path, monkeypatch) -> None:
    db_path = _build_compare_db(tmp_path)
    monkeypatch.setattr(api_main, "DB_PATH", db_path)

    client = TestClient(api_main.app)
    response = client.get(
        "/compare",
        params={
            "provider_ids": "provider_a,provider_b",
            "metric_ids": "finance_test_metric",
            "year": 2024,
        },
    )

    assert response.status_code == 200
    rows = response.json()
    assert [row["provider_id"] for row in rows] == ["provider_a", "provider_b"]
    assert {row["dimension_scope"] for row in rows} == {"Total Institution"}
    assert [row["value"] for row in rows] == [100.0, 200.0]


def test_compare_respects_explicit_scope(tmp_path: Path, monkeypatch) -> None:
    db_path = _build_compare_db(tmp_path)
    monkeypatch.setattr(api_main, "DB_PATH", db_path)

    client = TestClient(api_main.app)
    response = client.get(
        "/compare",
        params={
            "provider_ids": "provider_a,provider_b",
            "metric_ids": "finance_test_metric",
            "year": 2024,
            "scope": "HED",
        },
    )

    assert response.status_code == 200
    rows = response.json()
    assert [row["provider_id"] for row in rows] == ["provider_a", "provider_b"]
    assert {row["dimension_scope"] for row in rows} == {"HED"}
    assert [row["value"] for row in rows] == [90.0, 180.0]


def test_trends_defaults_to_one_canonical_scope_per_provider_year(tmp_path: Path, monkeypatch) -> None:
    db_path = _build_compare_db(tmp_path)
    monkeypatch.setattr(api_main, "DB_PATH", db_path)

    client = TestClient(api_main.app)
    response = client.get(
        "/trends",
        params={
            "provider_id": "provider_a",
            "metric_id": "finance_test_metric",
        },
    )

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["provider_id"] == "provider_a"
    assert rows[0]["dimension_scope"] == "Total Institution"
    assert rows[0]["value"] == 100.0


def test_trends_respects_explicit_scope(tmp_path: Path, monkeypatch) -> None:
    db_path = _build_compare_db(tmp_path)
    monkeypatch.setattr(api_main, "DB_PATH", db_path)

    client = TestClient(api_main.app)
    response = client.get(
        "/trends",
        params={
            "provider_id": "provider_a",
            "metric_id": "finance_test_metric",
            "scope": "HED",
        },
    )

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["dimension_scope"] == "HED"
    assert rows[0]["value"] == 90.0


def test_rankings_defaults_to_one_canonical_scope_per_provider_year(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_path = _build_compare_db(tmp_path)
    monkeypatch.setattr(api_main, "DB_PATH", db_path)

    client = TestClient(api_main.app)
    response = client.get(
        "/rankings",
        params={
            "metric_id": "finance_test_metric",
            "year": 2024,
        },
    )

    assert response.status_code == 200
    rows = response.json()
    assert [row["provider_id"] for row in rows] == ["provider_b", "provider_a"]
    assert {row["dimension_scope"] for row in rows} == {"Total Institution"}
    assert [row["value"] for row in rows] == [200.0, 100.0]


def test_rankings_respects_explicit_scope(tmp_path: Path, monkeypatch) -> None:
    db_path = _build_compare_db(tmp_path)
    monkeypatch.setattr(api_main, "DB_PATH", db_path)

    client = TestClient(api_main.app)
    response = client.get(
        "/rankings",
        params={
            "metric_id": "finance_test_metric",
            "year": 2024,
            "scope": "HED",
        },
    )

    assert response.status_code == 200
    rows = response.json()
    assert [row["provider_id"] for row in rows] == ["provider_b", "provider_a"]
    assert {row["dimension_scope"] for row in rows} == {"HED"}
    assert [row["value"] for row in rows] == [180.0, 90.0]


def _build_compare_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "compare.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.executemany(
            """
            INSERT INTO providers (provider_id, provider_name, state, provider_type, is_public)
            VALUES (?, ?, ?, 'university', TRUE)
            """,
            [
                ("provider_a", "Provider A", "NSW"),
                ("provider_b", "Provider B", "VIC"),
            ],
        )
        conn.execute(
            """
            INSERT INTO metrics (
                metric_id, metric_name, metric_group, unit, value_type,
                definition, source_agency, source_dataset
            )
            VALUES (
                'finance_test_metric', 'Finance test metric', 'Finance',
                'AUD thousands', 'currency', 'Test definition',
                'Test agency', 'Test dataset'
            )
            """
        )
        conn.execute(
            """
            INSERT INTO source_files (
                source_file_id, dataset_id, source_name, source_url,
                local_path, file_format, reporting_year, downloaded_at,
                checksum_sha256, row_count
            )
            VALUES (
                'source_test', 'finance', 'Finance test', 'local://finance',
                '/tmp/finance.csv', 'csv', 2024, CURRENT_TIMESTAMP,
                'checksum', 6
            )
            """
        )
        conn.executemany(
            """
            INSERT INTO facts (
                fact_id, provider_id, metric_id, source_file_id, reporting_year,
                dimension_scope, value, unit, source_row_number,
                source_provider_name, source_line_item
            )
            VALUES (?, ?, 'finance_test_metric', 'source_test', 2024, ?, ?, 'AUD thousands', ?, ?, 'Test line')
            """,
            [
                ("fact_a_total", "provider_a", "Total Institution", 100.0, 1, "Provider A"),
                ("fact_a_hed", "provider_a", "HED", 90.0, 2, "Provider A"),
                ("fact_a_tafe", "provider_a", "TAFE", 10.0, 3, "Provider A"),
                ("fact_b_total", "provider_b", "Total Institution", 200.0, 4, "Provider B"),
                ("fact_b_hed", "provider_b", "HED", 180.0, 5, "Provider B"),
                ("fact_b_tafe", "provider_b", "TAFE", 20.0, 6, "Provider B"),
            ],
        )
    finally:
        conn.close()
    return db_path

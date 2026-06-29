from pathlib import Path

import duckdb
from fastapi.testclient import TestClient

from uni_intel.api import main as api_main
from uni_intel.config import SCHEMA_PATH


def test_metric_catalog_defaults_to_available_curated_metrics(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_path = _build_catalog_db(tmp_path)
    monkeypatch.setattr(api_main, "DB_PATH", db_path)

    client = TestClient(api_main.app)
    response = client.get("/metric-catalog")

    assert response.status_code == 200
    rows = response.json()
    assert [row["metric_id"] for row in rows] == [
        "finance_total_revenues_from_continuing_operations_including_deferred_superannuation"
    ]
    assert rows[0]["metric_name"] == "Total revenue (continuing operations) $"
    assert rows[0]["catalog_group"] == "Finance and funding"
    assert rows[0]["source_status"] == "available"


def test_metric_catalog_can_include_missing_backlog_rows(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_path = _build_catalog_db(tmp_path)
    monkeypatch.setattr(api_main, "DB_PATH", db_path)

    client = TestClient(api_main.app)
    response = client.get("/metric-catalog", params={"include_missing": "true"})

    assert response.status_code == 200
    rows = response.json()
    missing = [row for row in rows if row["source_status"] in {"missing", "calculated_needed"}]
    assert missing
    assert all(row["metric_id"] is None for row in missing)
    assert {row["source_dataset"] for row in missing} == {"Not available yet"}


def test_raw_metrics_endpoint_remains_full_catalog(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_path = _build_catalog_db(tmp_path)
    monkeypatch.setattr(api_main, "DB_PATH", db_path)

    client = TestClient(api_main.app)
    response = client.get("/metrics")

    assert response.status_code == 200
    assert [row["metric_name"] for row in response.json()] == ["Raw revenue label"]


def test_curated_metric_resolves_in_rankings_compare_and_trends(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_path = _build_catalog_db(tmp_path)
    monkeypatch.setattr(api_main, "DB_PATH", db_path)

    client = TestClient(api_main.app)
    metric_id = "finance_total_revenues_from_continuing_operations_including_deferred_superannuation"
    rankings = client.get("/rankings", params={"metric_id": metric_id, "year": 2024})
    compare = client.get(
        "/compare",
        params={"provider_ids": "provider_a", "metric_ids": metric_id, "year": 2024},
    )
    trends = client.get("/trends", params={"provider_id": "provider_a", "metric_id": metric_id})

    assert rankings.status_code == 200
    assert compare.status_code == 200
    assert trends.status_code == 200
    assert rankings.json()[0]["value"] == 100.0
    assert compare.json()[0]["value"] == 100.0
    assert trends.json()[0]["value"] == 100.0


def _build_catalog_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "catalog.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.execute(
            """
            INSERT INTO providers (provider_id, provider_name, state, provider_type, is_public)
            VALUES ('provider_a', 'Provider A', 'NSW', 'university', TRUE)
            """
        )
        conn.execute(
            """
            INSERT INTO metrics (
                metric_id, metric_name, metric_group, unit, value_type,
                definition, source_agency, source_dataset, source_table,
                source_line_item
            )
            VALUES (
                'finance_total_revenues_from_continuing_operations_including_deferred_superannuation',
                'Raw revenue label', 'Finance - revenue', 'AUD thousands',
                'currency', 'Raw source definition', 'Agency', 'Dataset',
                'Table', 'Line'
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
                'source_a', 'finance', 'Finance source', 'local://finance',
                '/tmp/source.csv', 'csv', 2024, CURRENT_TIMESTAMP, 'checksum', 1
            )
            """
        )
        conn.execute(
            """
            INSERT INTO facts (
                fact_id, provider_id, metric_id, source_file_id, reporting_year,
                dimension_scope, value, unit, source_row_number,
                source_provider_name, source_line_item
            )
            VALUES (
                'fact_a', 'provider_a',
                'finance_total_revenues_from_continuing_operations_including_deferred_superannuation',
                'source_a', 2024, 'Total Institution', 100,
                'AUD thousands', 1, 'Provider A', 'Line'
            )
            """
        )
    finally:
        conn.close()
    return db_path

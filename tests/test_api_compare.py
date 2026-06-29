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


def test_rankings_filters_by_mission_group(tmp_path: Path, monkeypatch) -> None:
    db_path = _build_compare_db(tmp_path)
    monkeypatch.setattr(api_main, "DB_PATH", db_path)

    client = TestClient(api_main.app)
    response = client.get(
        "/rankings",
        params={"metric_id": "finance_test_metric", "year": 2024, "mission_group": "Go8"},
    )

    assert response.status_code == 200
    rows = response.json()
    assert [row["provider_id"] for row in rows] == ["provider_a"]
    assert {row["dimension_scope"] for row in rows} == {"Total Institution"}


def test_rankings_filters_by_state(tmp_path: Path, monkeypatch) -> None:
    db_path = _build_compare_db(tmp_path)
    monkeypatch.setattr(api_main, "DB_PATH", db_path)

    client = TestClient(api_main.app)
    response = client.get(
        "/rankings",
        params={"metric_id": "finance_test_metric", "year": 2024, "state": "VIC"},
    )

    assert response.status_code == 200
    rows = response.json()
    assert [row["provider_id"] for row in rows] == ["provider_b"]


def test_benchmarks_average_by_mission_group_uses_canonical_scope(tmp_path: Path, monkeypatch) -> None:
    db_path = _build_compare_db(tmp_path)
    monkeypatch.setattr(api_main, "DB_PATH", db_path)

    client = TestClient(api_main.app)
    response = client.get(
        "/benchmarks",
        params={"metric_id": "finance_test_metric", "year": 2024},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["group_by"] == "mission_group"
    by_group = {row["group_value"]: row for row in payload["rows"]}
    # Canonical Total Institution values (100/200), not the HED/TAFE rows.
    assert by_group["Go8"]["average"] == 100.0
    assert by_group["Go8"]["provider_count"] == 1
    assert by_group["ATN"]["average"] == 200.0


def test_benchmarks_group_by_state(tmp_path: Path, monkeypatch) -> None:
    db_path = _build_compare_db(tmp_path)
    monkeypatch.setattr(api_main, "DB_PATH", db_path)

    client = TestClient(api_main.app)
    response = client.get(
        "/benchmarks",
        params={"metric_id": "finance_test_metric", "year": 2024, "group_by": "state"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["group_by"] == "state"
    by_state = {row["group_value"]: row["average"] for row in payload["rows"]}
    assert by_state == {"NSW": 100.0, "VIC": 200.0}


def test_provider_metric_insight_returns_ranks_medians_changes_and_trend(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_path = _build_insight_db(tmp_path)
    monkeypatch.setattr(api_main, "DB_PATH", db_path)

    client = TestClient(api_main.app)
    response = client.get(
        "/provider/provider_a/metric-insight",
        params={"metric_id": "finance_test_metric", "year": 2024},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["value"] == 100.0
    assert payload["ranks"]["national"]["rank"] == 3
    assert payload["ranks"]["national"]["of"] == 3
    assert payload["ranks"]["mission_group"]["label"] == "Go8"
    assert payload["ranks"]["mission_group"]["rank"] == 2
    assert payload["ranks"]["mission_group"]["of"] == 2
    assert payload["ranks"]["state"]["label"] == "NSW"
    assert payload["ranks"]["state"]["rank"] == 2
    assert payload["medians"]["national"] == 200.0
    assert payload["medians"]["mission_group"] == 150.0
    assert payload["changes"]["1y"]["from_value"] == 80.0
    assert payload["changes"]["1y"]["percent"] == 25.0
    assert payload["rank_move"] == {
        "year": 2019,
        "from_rank": 1,
        "to_rank": 3,
        "places": -2,
    }
    assert [row["reporting_year"] for row in payload["trend"]] == [2019, 2021, 2023, 2024]
    assert payload["source"]["source_url"] == "local://finance"


def _build_compare_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "compare.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.executemany(
            """
            INSERT INTO providers (
                provider_id, provider_name, state, mission_group,
                table_classification, provider_type, is_public
            )
            VALUES (?, ?, ?, ?, 'Table A', 'university', TRUE)
            """,
            [
                ("provider_a", "Provider A", "NSW", "Go8"),
                ("provider_b", "Provider B", "VIC", "ATN"),
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


def _build_insight_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "insight.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.executemany(
            """
            INSERT INTO providers (
                provider_id, provider_name, state, mission_group,
                table_classification, provider_type, is_public
            )
            VALUES (?, ?, ?, ?, 'Table A', 'university', TRUE)
            """,
            [
                ("provider_a", "Provider A", "NSW", "Go8"),
                ("provider_b", "Provider B", "VIC", "ATN"),
                ("provider_c", "Provider C", "NSW", "Go8"),
            ],
        )
        conn.execute(
            """
            INSERT INTO metrics (
                metric_id, metric_name, metric_group, unit, value_type,
                definition, source_agency, source_dataset, source_table,
                source_line_item
            )
            VALUES (
                'finance_test_metric', 'Finance test metric', 'Finance',
                'AUD thousands', 'currency', 'Test definition',
                'Test agency', 'Test dataset', 'Test table', 'Test line'
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
                'checksum', 12
            )
            """
        )
        facts = [
            ("a_2019", "provider_a", 2019, 300.0),
            ("b_2019", "provider_b", 2019, 200.0),
            ("c_2019", "provider_c", 2019, 100.0),
            ("a_2021", "provider_a", 2021, 70.0),
            ("a_2023", "provider_a", 2023, 80.0),
            ("a_2024", "provider_a", 2024, 100.0),
            ("b_2024", "provider_b", 2024, 300.0),
            ("c_2024", "provider_c", 2024, 200.0),
        ]
        conn.executemany(
            """
            INSERT INTO facts (
                fact_id, provider_id, metric_id, source_file_id, reporting_year,
                dimension_scope, value, unit, source_row_number,
                source_provider_name, source_line_item
            )
            VALUES (?, ?, 'finance_test_metric', 'source_test', ?, 'Total Institution',
                    ?, 'AUD thousands', 1, ?, 'Test line')
            """,
            [(fact_id, provider_id, year, value, provider_id) for fact_id, provider_id, year, value in facts],
        )
    finally:
        conn.close()
    return db_path

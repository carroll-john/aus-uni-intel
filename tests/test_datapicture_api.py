from pathlib import Path

import duckdb
from fastapi.testclient import TestClient

from uni_intel.api import main as api_main
from uni_intel.config import SCHEMA_PATH

REVENUE_METRIC_ID = "finance_total_revenues_from_continuing_operations_including_deferred_superannuation"
QILT_METRIC_ID = "qilt_overall_educational_experience_positive_rating"
HERDC_METRIC_ID = "herdc_research_income_total"


def test_examples_endpoint_returns_three_canned_questions(tmp_path: Path, monkeypatch) -> None:
    db_path = _build_datapicture_db(tmp_path)
    monkeypatch.setattr(api_main, "DB_PATH", db_path)

    client = TestClient(api_main.app)
    response = client.get("/datapicture/examples")

    assert response.status_code == 200
    examples = response.json()
    assert len(examples) == 3
    assert {example["intent"] for example in examples} == {"trend", "ranking", "mismatch"}


def test_compose_trend_question_returns_trend_chart_with_sources(tmp_path: Path, monkeypatch) -> None:
    db_path = _build_datapicture_db(tmp_path)
    monkeypatch.setattr(api_main, "DB_PATH", db_path)

    client = TestClient(api_main.app)
    response = client.get(
        "/datapicture/compose",
        params={"q": "How has Monash University's total revenue grown since 2018?"},
    )

    assert response.status_code == 200
    picture = response.json()
    assert picture["intent"] == "trend"
    block_types = [block["type"] for block in picture["blocks"]]
    assert "TrendChart" in block_types
    assert "SourceTraceDrawer" in block_types
    assert picture["sources"]
    assert all(source["source_file_id"] for source in picture["sources"])


def test_compose_ranking_question_returns_ranking_bar_chart(tmp_path: Path, monkeypatch) -> None:
    db_path = _build_datapicture_db(tmp_path)
    monkeypatch.setattr(api_main, "DB_PATH", db_path)

    client = TestClient(api_main.app)
    response = client.get(
        "/datapicture/compose",
        params={"q": "Which universities lead in research income in 2024?"},
    )

    assert response.status_code == 200
    picture = response.json()
    assert picture["intent"] == "ranking"
    block_types = [block["type"] for block in picture["blocks"]]
    assert "RankingBarChart" in block_types
    assert "MetricComparisonTable" in block_types
    ranking_block = next(block for block in picture["blocks"] if block["type"] == "RankingBarChart")
    leader = ranking_block["props"]["rows"][0]
    assert leader["provider_id"] == "monash_university"


def test_compose_mismatch_question_returns_mismatch_matrix_with_two_metrics(tmp_path: Path, monkeypatch) -> None:
    db_path = _build_datapicture_db(tmp_path)
    monkeypatch.setattr(api_main, "DB_PATH", db_path)

    client = TestClient(api_main.app)
    response = client.get(
        "/datapicture/compose",
        params={"q": "Which universities have high total revenue but a low overall student experience rating?"},
    )

    assert response.status_code == 200
    picture = response.json()
    assert picture["intent"] == "mismatch"
    mismatch_block = next(block for block in picture["blocks"] if block["type"] == "MismatchMatrix")
    assert {mismatch_block["props"]["metric_a"]["metric_id"], mismatch_block["props"]["metric_b"]["metric_id"]} == {
        REVENUE_METRIC_ID,
        QILT_METRIC_ID,
    }
    assert mismatch_block["props"]["rows"]


def test_compose_unresolvable_question_returns_clarification(tmp_path: Path, monkeypatch) -> None:
    db_path = _build_datapicture_db(tmp_path)
    monkeypatch.setattr(api_main, "DB_PATH", db_path)

    client = TestClient(api_main.app)
    response = client.get("/datapicture/compose", params={"q": "asdkfj qwoeiru zzzzz"})

    assert response.status_code == 200
    picture = response.json()
    assert picture["intent"] == "clarify"
    assert picture["clarification"] is not None
    assert len(picture["follow_ups"]) == 3


def _insert_source(conn: duckdb.DuckDBPyConnection, source_file_id: str, dataset_id: str) -> None:
    conn.execute(
        """
        INSERT INTO source_datasets (dataset_id, dataset_name, source_agency, landing_page_url)
        VALUES (?, ?, 'Department of Education', 'https://example.gov.au')
        """,
        [dataset_id, dataset_id.replace("_", " ").title()],
    )
    conn.execute(
        """
        INSERT INTO source_files (
            source_file_id, dataset_id, source_name, source_url,
            local_path, file_format, reporting_year, downloaded_at,
            checksum_sha256, row_count
        )
        VALUES (?, ?, ?, 'https://example.gov.au/file', '/tmp/file.csv', 'csv', 2024, CURRENT_TIMESTAMP, 'checksum', 1)
        """,
        [source_file_id, dataset_id, f"{dataset_id} source file"],
    )
    conn.execute(
        """
        INSERT INTO data_quality_checks (check_id, run_id, source_file_id, check_name, status, severity, details)
        VALUES (?, 'run-1', ?, 'facts_loaded', 'pass', 'info', 'ok')
        """,
        [f"{source_file_id}-check", source_file_id],
    )


def _insert_metric(conn: duckdb.DuckDBPyConnection, metric_id: str, name: str, unit: str) -> None:
    conn.execute(
        """
        INSERT INTO metrics (
            metric_id, metric_name, metric_group, unit, value_type,
            definition, source_agency, source_dataset, source_table, source_line_item
        )
        VALUES (?, ?, 'Test group', ?, 'currency', 'Test definition', 'Agency', 'Dataset', 'Table', 'Line')
        """,
        [metric_id, name, unit],
    )


def _insert_fact(
    conn: duckdb.DuckDBPyConnection,
    *,
    fact_id: str,
    provider_id: str,
    metric_id: str,
    source_file_id: str,
    year: int,
    scope: str,
    value: float,
    unit: str,
) -> None:
    conn.execute(
        """
        INSERT INTO facts (
            fact_id, provider_id, metric_id, source_file_id, reporting_year,
            dimension_scope, value, unit, source_row_number,
            source_provider_name, source_line_item
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 'Provider', 'Line')
        """,
        [fact_id, provider_id, metric_id, source_file_id, year, scope, value, unit],
    )


def _build_datapicture_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "datapicture.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
        for provider_id, name in (
            ("monash_university", "Monash University"),
            ("university_of_sydney", "The University of Sydney"),
            ("university_of_new_south_wales", "The University of New South Wales"),
        ):
            conn.execute(
                "INSERT INTO providers (provider_id, provider_name, state, provider_type, is_public) "
                "VALUES (?, ?, 'VIC', 'university', TRUE)",
                [provider_id, name],
            )

        _insert_metric(conn, REVENUE_METRIC_ID, "Total revenue (continuing operations) $", "AUD thousands")
        _insert_metric(conn, QILT_METRIC_ID, "Overall educational experience positive rating", "percent")
        _insert_metric(conn, HERDC_METRIC_ID, "HERDC research income (Cat 1-4) $", "AUD")

        _insert_source(conn, "source_finance", "finance")
        _insert_source(conn, "source_qilt", "qilt")
        _insert_source(conn, "source_herdc", "herdc")

        _insert_fact(
            conn,
            fact_id="fact_monash_revenue_2018",
            provider_id="monash_university",
            metric_id=REVENUE_METRIC_ID,
            source_file_id="source_finance",
            year=2018,
            scope="Total Institution",
            value=3_000_000,
            unit="AUD thousands",
        )
        for provider_id, revenue in (
            ("monash_university", 3_500_000),
            ("university_of_sydney", 3_900_000),
            ("university_of_new_south_wales", 3_300_000),
        ):
            _insert_fact(
                conn,
                fact_id=f"fact_{provider_id}_revenue_2024",
                provider_id=provider_id,
                metric_id=REVENUE_METRIC_ID,
                source_file_id="source_finance",
                year=2024,
                scope="Total Institution",
                value=revenue,
                unit="AUD thousands",
            )

        for provider_id, rating in (
            ("monash_university", 70.0),
            ("university_of_sydney", 60.0),
            ("university_of_new_south_wales", 85.0),
        ):
            _insert_fact(
                conn,
                fact_id=f"fact_{provider_id}_qilt_2024",
                provider_id=provider_id,
                metric_id=QILT_METRIC_ID,
                source_file_id="source_qilt",
                year=2024,
                scope="QILT undergraduate",
                value=rating,
                unit="percent",
            )

        for provider_id, income in (
            ("monash_university", 650_000_000),
            ("university_of_sydney", 600_000_000),
            ("university_of_new_south_wales", 580_000_000),
        ):
            _insert_fact(
                conn,
                fact_id=f"fact_{provider_id}_herdc_2024",
                provider_id=provider_id,
                metric_id=HERDC_METRIC_ID,
                source_file_id="source_herdc",
                year=2024,
                scope="HERDC",
                value=income,
                unit="AUD",
            )
    finally:
        conn.close()
    return db_path

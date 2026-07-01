from pathlib import Path

import duckdb
from fastapi.testclient import TestClient

from uni_intel.api import main as api_main
from uni_intel.config import SCHEMA_PATH

TOTAL_REVENUE = "finance_total_revenues_from_continuing_operations_including_deferred_superannuation"
ENROLMENTS = "student_total_enrolments"
RESEARCH = "herdc_research_income_total"
QILT = "qilt_overall_educational_experience_positive_rating"

_METRIC_SPECS = {
    TOTAL_REVENUE: ("Total revenue", "Finance", "AUD thousands"),
    ENROLMENTS: ("Total enrolments", "Students and load", "students"),
    RESEARCH: ("HERDC research income", "Research", "AUD"),
    QILT: ("Overall educational experience", "Student experience", "percent"),
}


def _insert_metric(conn: duckdb.DuckDBPyConnection, metric_id: str) -> None:
    name, group, unit = _METRIC_SPECS[metric_id]
    conn.execute(
        """
        INSERT INTO metrics (
            metric_id, metric_name, metric_group, unit, value_type, definition,
            source_agency, source_dataset, source_table, source_line_item,
            is_calculated, calculation_method
        ) VALUES (?, ?, ?, ?, 'number', ?, 'Dept', 'Dataset', 'Table', ?, FALSE, NULL)
        """,
        [metric_id, name, group, unit, f"Definition of {name}", name],
    )


def _insert_fact(
    conn: duckdb.DuckDBPyConnection,
    provider_id: str,
    metric_id: str,
    year: int,
    scope: str,
    value: float,
) -> None:
    _, _, unit = _METRIC_SPECS[metric_id]
    fact_id = f"{provider_id}-{metric_id}-{year}-{scope}"
    conn.execute(
        """
        INSERT INTO facts (
            fact_id, provider_id, metric_id, source_file_id, reporting_year,
            dimension_scope, value, unit, source_row_number, source_provider_name,
            source_line_item, dimensions_json
        ) VALUES (?, ?, ?, 'sf1', ?, ?, ?, ?, 1, 'Src', 'Line', '{}')
        """,
        [fact_id, provider_id, metric_id, year, scope, value, unit],
    )


def _build_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "endpoints.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.executemany(
            """
            INSERT INTO providers (provider_id, provider_name, state, provider_type, is_public, mission_group, table_classification, website)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "university_of_sydney",
                    "The University of Sydney",
                    "NSW",
                    "university",
                    True,
                    "Go8",
                    "Table A",
                    "https://sydney.edu.au",
                ),
                (
                    "monash_university",
                    "Monash University",
                    "VIC",
                    "university",
                    True,
                    "Go8",
                    "Table A",
                    "https://monash.edu",
                ),
                ("sector_all_pub2", "Public university sector", None, "sector", True, None, None, None),
            ],
        )
        conn.execute(
            """
            INSERT INTO source_files (
                source_file_id, dataset_id, source_name, source_url, local_path,
                file_format, reporting_year, downloaded_at, checksum_sha256, row_count,
                license, publication_date, notes
            ) VALUES ('sf1', 'ds1', 'Source One', 'https://example.gov/data', '/tmp/secret.xlsx',
                      'xlsx', 2024, CURRENT_TIMESTAMP, 'abc123', 10, 'Public', '2024', 'Notes')
            """
        )
        for metric_id in _METRIC_SPECS:
            _insert_metric(conn, metric_id)

        for year in (2023, 2024):
            _insert_fact(conn, "university_of_sydney", TOTAL_REVENUE, year, "Total Institution", 3000.0 + year)
            _insert_fact(conn, "monash_university", TOTAL_REVENUE, year, "Total Institution", 2500.0 + year)
            _insert_fact(conn, "sector_all_pub2", TOTAL_REVENUE, year, "Total Institution", 45000.0 + year)
            _insert_fact(conn, "university_of_sydney", ENROLMENTS, year, "Student", 70000.0 + year)
            _insert_fact(conn, "monash_university", ENROLMENTS, year, "Student", 80000.0 + year)
            _insert_fact(conn, "university_of_sydney", RESEARCH, year, "HERDC", 600000.0 + year)
            _insert_fact(conn, "monash_university", RESEARCH, year, "HERDC", 500000.0 + year)
            _insert_fact(conn, "university_of_sydney", QILT, year, "QILT undergraduate", 75.0)
            _insert_fact(conn, "monash_university", QILT, year, "QILT undergraduate", 78.0)

        conn.execute(
            """
            INSERT INTO data_quality_checks (check_id, run_id, source_file_id, check_name, status, severity, observed_value, expected_value, details)
            VALUES ('c1', 'run1', 'sf1', 'facts_loaded', 'pass', 'info', '18', '> 0', 'Facts loaded.')
            """
        )
    finally:
        conn.close()
    return db_path


def _client(tmp_path: Path, monkeypatch) -> TestClient:
    db_path = _build_db(tmp_path)
    monkeypatch.setattr("uni_intel.api.deps.DB_PATH", db_path)
    return TestClient(api_main.app)


def test_overview_returns_summary_kpis_and_quality(tmp_path: Path, monkeypatch) -> None:
    response = _client(tmp_path, monkeypatch).get("/overview")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"summary", "kpis", "top_rankings", "quality"}
    assert body["summary"]["providers"] == 2  # only public universities
    assert body["summary"]["latest_year"] == 2024
    assert len(body["kpis"]) == 4
    assert body["quality"][0]["check_name"] == "facts_loaded"


def test_providers_lists_all_providers(tmp_path: Path, monkeypatch) -> None:
    response = _client(tmp_path, monkeypatch).get("/providers")
    assert response.status_code == 200
    providers = response.json()
    assert {p["provider_id"] for p in providers} == {
        "university_of_sydney",
        "monash_university",
        "sector_all_pub2",
    }
    sydney = next(p for p in providers if p["provider_id"] == "university_of_sydney")
    assert sydney["mission_group"] == "Go8"


def test_years_and_scopes(tmp_path: Path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    years = client.get("/years").json()
    assert [row["reporting_year"] for row in years] == [2023, 2024]
    scoped_years = client.get(f"/years?metric_id={RESEARCH}").json()
    assert [row["reporting_year"] for row in scoped_years] == [2023, 2024]
    scopes = {row["dimension_scope"] for row in client.get("/scopes").json()}
    assert {"Total Institution", "Student", "HERDC", "QILT undergraduate"} <= scopes
    research_scopes = [row["dimension_scope"] for row in client.get(f"/scopes?metric_id={RESEARCH}").json()]
    assert research_scopes == ["HERDC"]


def test_provider_profile_and_404(tmp_path: Path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    response = client.get("/provider/university_of_sydney/profile")
    assert response.status_code == 200
    body = response.json()
    assert body["provider"]["provider_id"] == "university_of_sydney"
    assert len(body["facts"]) > 0

    filtered = client.get("/provider/university_of_sydney/profile?year=2024&scope=Student").json()
    assert all(fact["reporting_year"] == 2024 for fact in filtered["facts"])
    assert all(fact["dimension_scope"] == "Student" for fact in filtered["facts"])

    assert client.get("/provider/nope/profile").status_code == 404


def test_quality_endpoint(tmp_path: Path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    checks = client.get("/quality").json()
    assert len(checks) == 1
    assert checks[0]["source_name"] == "Source One"
    assert client.get("/quality?limit=1").status_code == 200

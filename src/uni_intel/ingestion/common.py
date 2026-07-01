from __future__ import annotations

import hashlib
import json
import shutil
import urllib.request
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import duckdb

from uni_intel.config import QUALITY_DIR

DOWNLOAD_TIMEOUT_SECONDS = 60


@dataclass(frozen=True)
class SourceDataset:
    dataset_id: str
    dataset_name: str
    source_agency: str
    landing_page_url: str
    notes: str


@dataclass(frozen=True)
class SourceFileMetadata:
    source_file_id: str
    dataset_id: str
    source_name: str
    source_url: str
    local_path: Path
    file_format: str
    reporting_year: int | None
    checksum_sha256: str
    row_count: int
    license: str
    publication_date: str | None
    notes: str


@dataclass(frozen=True)
class QualityCheck:
    check_name: str
    status: str
    severity: str
    observed_value: str
    expected_value: str
    details: str


def new_run_id() -> str:
    return f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}_{uuid4().hex[:8]}"


def download_file(url: str, destination: Path, force: bool = False) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not force:
        return
    with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_file_id(dataset_id: str, checksum: str) -> str:
    return f"{dataset_id}_{checksum[:12]}"


def stable_fact_id(
    source_file_id_value: str,
    provider_id: str,
    metric_id: str,
    year: int,
    scope: str,
    dimensions_json: str = "{}",
) -> str:
    key = f"{source_file_id_value}|{provider_id}|{metric_id}|{year}|{scope}|{dimensions_json}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


def json_dumps(value: dict[str, object]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def upsert_row(
    conn: duckdb.DuckDBPyConnection,
    table: str,
    pk_col: str,
    row: dict[str, object],
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


def upsert_source_dataset(conn: duckdb.DuckDBPyConnection, dataset: SourceDataset) -> None:
    upsert_row(conn, "source_datasets", "dataset_id", asdict(dataset))


def upsert_source_file(conn: duckdb.DuckDBPyConnection, metadata: SourceFileMetadata) -> None:
    upsert_row(
        conn,
        "source_files",
        "source_file_id",
        {
            "source_file_id": metadata.source_file_id,
            "dataset_id": metadata.dataset_id,
            "source_name": metadata.source_name,
            "source_url": metadata.source_url,
            "local_path": str(metadata.local_path),
            "file_format": metadata.file_format,
            "reporting_year": metadata.reporting_year,
            "downloaded_at": datetime.now(UTC).replace(tzinfo=None),
            "checksum_sha256": metadata.checksum_sha256,
            "row_count": metadata.row_count,
            "license": metadata.license,
            "publication_date": metadata.publication_date,
            "notes": metadata.notes,
        },
    )


def upsert_metrics(conn: duckdb.DuckDBPyConnection, records: list[dict[str, object]]) -> None:
    for record in records:
        upsert_row(conn, "metrics", "metric_id", record)


def upsert_metric_dependencies(
    conn: duckdb.DuckDBPyConnection,
    metric_id: str,
    dependencies: list[tuple[str, str]],
) -> None:
    conn.execute("DELETE FROM metric_dependencies WHERE metric_id = ?", [metric_id])
    for depends_on_metric_id, role in dependencies:
        conn.execute(
            """
            INSERT INTO metric_dependencies (metric_id, depends_on_metric_id, dependency_role)
            VALUES (?, ?, ?)
            """,
            [metric_id, depends_on_metric_id, role],
        )


FACTS_INSERT_SQL = """
    INSERT INTO facts (
        fact_id, provider_id, metric_id, source_file_id, reporting_year,
        period_start, period_end, dimension_scope, value, unit,
        source_row_number, source_provider_name, source_line_item,
        dimensions_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def insert_facts(conn: duckdb.DuckDBPyConnection, fact_rows: list[tuple[object, ...]]) -> None:
    """Bulk-insert canonical fact rows. Column order matches :data:`FACTS_INSERT_SQL`."""
    if fact_rows:
        conn.executemany(FACTS_INSERT_SQL, fact_rows)


def standard_quality_checks(
    rows_parsed: int,
    staging_rows: int,
    facts_loaded: int,
    unmatched: list[str],
    *,
    parsed_detail: str,
    facts_detail: str,
    staging_detail: str = "Every parsed source row should be represented in staging.",
    matched_detail: str = "All source provider names matched.",
    extra: list[QualityCheck] | None = None,
) -> list[QualityCheck]:
    """Build the four quality checks every dataset runner shares.

    Detail strings are parametrised so each dataset keeps its own wording. Pass
    ``extra`` for dataset-specific checks (e.g. QILT confidence intervals).
    """
    checks = [
        QualityCheck(
            "source_rows_parsed",
            "pass" if rows_parsed > 0 else "fail",
            "info" if rows_parsed > 0 else "error",
            str(rows_parsed),
            "> 0",
            parsed_detail,
        ),
        QualityCheck(
            "staging_rows_loaded",
            "pass" if rows_parsed == staging_rows else "fail",
            "info" if rows_parsed == staging_rows else "error",
            str(staging_rows),
            str(rows_parsed),
            staging_detail,
        ),
        QualityCheck(
            "facts_loaded",
            "pass" if facts_loaded > 0 else "fail",
            "info" if facts_loaded > 0 else "error",
            str(facts_loaded),
            "> 0",
            facts_detail,
        ),
        QualityCheck(
            "unmatched_source_providers",
            "warn" if unmatched else "pass",
            "warning" if unmatched else "info",
            str(len(unmatched)),
            "0 public-university providers unmatched",
            ", ".join(unmatched) if unmatched else matched_detail,
        ),
    ]
    if extra:
        checks.extend(extra)
    return checks


def metadata_quality_checks(conn: duckdb.DuckDBPyConnection) -> list[QualityCheck]:
    missing_metric_metadata = conn.execute(
        """
        SELECT COUNT(*)
        FROM metrics
        WHERE definition IS NULL
           OR TRIM(definition) = ''
           OR source_agency IS NULL
           OR TRIM(source_agency) = ''
           OR source_dataset IS NULL
           OR TRIM(source_dataset) = ''
           OR (is_calculated = TRUE AND calculation_method IS NULL)
        """
    ).fetchone()[0]
    missing_fact_sources = conn.execute(
        """
        SELECT COUNT(*)
        FROM facts
        WHERE source_file_id IS NULL
           OR source_line_item IS NULL
           OR TRIM(source_line_item) = ''
        """
    ).fetchone()[0]
    duplicate_facts = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT provider_id, metric_id, source_file_id, reporting_year,
                   dimension_scope, dimensions_json
            FROM facts
            GROUP BY 1, 2, 3, 4, 5, 6
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()[0]
    return [
        QualityCheck(
            "metrics_have_sources_and_definitions",
            "pass" if missing_metric_metadata == 0 else "fail",
            "info" if missing_metric_metadata == 0 else "error",
            str(missing_metric_metadata),
            "0",
            "Every metric must carry source metadata and a definition; calculated metrics need methods.",
        ),
        QualityCheck(
            "facts_have_source_references",
            "pass" if missing_fact_sources == 0 else "fail",
            "info" if missing_fact_sources == 0 else "error",
            str(missing_fact_sources),
            "0",
            "Every fact should retain a source file and source line item.",
        ),
        QualityCheck(
            "duplicate_canonical_facts",
            "pass" if duplicate_facts == 0 else "fail",
            "info" if duplicate_facts == 0 else "error",
            str(duplicate_facts),
            "0",
            "Provider/metric/source/year/scope/dimensions should be unique.",
        ),
    ]


def persist_quality_checks(
    conn: duckdb.DuckDBPyConnection,
    run_id: str,
    source_file_id_value: str | None,
    checks: list[QualityCheck],
) -> None:
    rows = []
    source_key = source_file_id_value or "no-source-file"
    for check in checks:
        check_id = hashlib.sha1(f"{run_id}|{source_key}|{check.check_name}".encode()).hexdigest()
        rows.append(
            (
                check_id,
                run_id,
                source_file_id_value,
                check.check_name,
                check.status,
                check.severity,
                check.observed_value,
                check.expected_value,
                check.details,
            )
        )

    conn.executemany(
        """
        INSERT INTO data_quality_checks (
            check_id, run_id, source_file_id, check_name, status, severity,
            observed_value, expected_value, details
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def write_quality_report(
    dataset_slug: str,
    run_id: str,
    source_file_id_value: str | None,
    payload: dict[str, object],
    checks: list[QualityCheck],
) -> Path:
    QUALITY_DIR.mkdir(parents=True, exist_ok=True)
    report_path = QUALITY_DIR / f"{dataset_slug}_{run_id}.json"
    report = {
        **payload,
        "run_id": run_id,
        "source_file_id": source_file_id_value,
        "checks": [asdict(check) for check in checks],
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report_path

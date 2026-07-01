from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import duckdb

from uni_intel.config import (
    DB_PATH,
    FINANCE_PUBLICATION_URL,
    FINANCE_PUBLICATION_URLS,
    FINANCE_URLS,
    QUALITY_DIR,
    RAW_DIR,
)
from uni_intel.db import connect, init_schema
from uni_intel.ingestion.common import download_file
from uni_intel.ingestion.metrics import (
    SOURCE_AGENCY,
    finance_metric_record,
)
from uni_intel.ingestion.parsers.finance import FinanceParser, FinanceRawRow
from uni_intel.ingestion.provider_matching import ProviderResolver
from uni_intel.seed import seed_providers

SOURCE_LICENSE = "Australian Government Department of Education public data"


@dataclass(frozen=True)
class QualityCheck:
    check_name: str
    status: str
    severity: str
    observed_value: str
    expected_value: str
    details: str


def finance_dataset_id(year: int) -> str:
    return f"education_finance_{year}"


def finance_source_name(year: int) -> str:
    return f"Finance {year}: Financial Reports of Higher Education Providers"


def finance_publication_url(year: int) -> str:
    return FINANCE_PUBLICATION_URLS.get(year, FINANCE_PUBLICATION_URL)


def default_raw_path(year: int, source_url: str) -> Path:
    extension = "xlsx" if source_url.rstrip("/").endswith("/xlsx") else "csv"
    return RAW_DIR / "finance" / str(year) / f"finance_{year}_financial_reports_higher_education_providers.{extension}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_fact_id(
    source_file_id: str,
    provider_id: str,
    metric_id: str,
    year: int,
    scope: str,
) -> str:
    key = f"{source_file_id}|{provider_id}|{metric_id}|{year}|{scope}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


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


def upsert_source_dataset(conn: duckdb.DuckDBPyConnection, year: int) -> None:
    upsert_row(
        conn,
        "source_datasets",
        "dataset_id",
        {
            "dataset_id": finance_dataset_id(year),
            "dataset_name": finance_source_name(year),
            "source_agency": SOURCE_AGENCY,
            "landing_page_url": finance_publication_url(year),
            "notes": "Annual Department of Education finance ingestion source.",
        },
    )


def upsert_source_file(
    conn: duckdb.DuckDBPyConnection,
    source_file_id: str,
    raw_path: Path,
    source_url: str,
    checksum: str,
    row_count: int,
    year: int,
) -> None:
    upsert_row(
        conn,
        "source_files",
        "source_file_id",
        {
            "source_file_id": source_file_id,
            "dataset_id": finance_dataset_id(year),
            "source_name": finance_source_name(year),
            "source_url": source_url,
            "local_path": str(raw_path),
            "file_format": raw_path.suffix.lstrip(".").lower() or "csv",
            "reporting_year": year,
            "downloaded_at": datetime.now(UTC).replace(tzinfo=None),
            "checksum_sha256": checksum,
            "row_count": row_count,
            "license": SOURCE_LICENSE,
            "publication_date": str(year),
            "notes": "Headerless CSV extract from Department of Education finance tables.",
        },
    )


def upsert_metrics(conn: duckdb.DuckDBPyConnection, line_items: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for line_item in sorted(set(line_items)):
        record = finance_metric_record(line_item)
        upsert_row(conn, "metrics", "metric_id", record)
        mapping[line_item] = str(record["metric_id"])
    return mapping


def load_staging_and_facts(
    conn: duckdb.DuckDBPyConnection,
    rows: list[FinanceRawRow],
    source_file_id: str,
    run_id: str,
    resolver: ProviderResolver,
    metric_map: dict[str, str],
) -> tuple[int, int, list[str]]:
    conn.execute("DELETE FROM stg_finance_rows WHERE source_file_id = ?", [source_file_id])
    conn.execute("DELETE FROM facts WHERE source_file_id = ?", [source_file_id])

    staging_rows: list[tuple[object, ...]] = []
    fact_rows: list[tuple[object, ...]] = []
    unmatched_providers: set[str] = set()

    for row in rows:
        provider_match = resolver.resolve(row.source_provider_name)
        metric_id = metric_map[row.line_item]
        provider_id = provider_match.provider_id if provider_match else None
        match_status = provider_match.method if provider_match else "unmatched"
        match_confidence = provider_match.confidence if provider_match else None

        staging_rows.append(
            (
                row.row_number,
                row.source_system,
                row.institution_scope,
                row.reporting_year,
                row.statement_code,
                row.source_provider_name,
                row.line_item,
                row.raw_value,
                row.numeric_value,
                source_file_id,
                provider_id,
                metric_id,
                match_status,
                match_confidence,
                run_id,
            )
        )

        if provider_match is None:
            unmatched_providers.add(row.source_provider_name)
            continue

        fact_rows.append(
            (
                stable_fact_id(
                    source_file_id,
                    provider_match.provider_id,
                    metric_id,
                    row.reporting_year,
                    row.institution_scope,
                ),
                provider_match.provider_id,
                metric_id,
                source_file_id,
                row.reporting_year,
                f"{row.reporting_year}-01-01",
                f"{row.reporting_year}-12-31",
                row.institution_scope,
                row.numeric_value,
                "AUD thousands",
                row.row_number,
                row.source_provider_name,
                row.line_item,
                "{}",
            )
        )

    conn.executemany(
        """
        INSERT INTO stg_finance_rows (
            row_number, source_system, institution_scope, reporting_year,
            statement_code, source_provider_name, line_item, raw_value,
            numeric_value, source_file_id, provider_id, metric_id, match_status,
            match_confidence, load_run_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        staging_rows,
    )

    if fact_rows:
        conn.executemany(
            """
            INSERT INTO facts (
                fact_id, provider_id, metric_id, source_file_id, reporting_year,
                period_start, period_end, dimension_scope, value, unit,
                source_row_number, source_provider_name, source_line_item,
                dimensions_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            fact_rows,
        )

    return len(staging_rows), len(fact_rows), sorted(unmatched_providers)


def build_quality_checks(
    conn: duckdb.DuckDBPyConnection,
    rows_parsed: int,
    staging_rows: int,
    facts_loaded: int,
    source_file_id: str,
    unmatched_providers: list[str],
) -> list[QualityCheck]:
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
            SELECT provider_id, metric_id, source_file_id, reporting_year, dimension_scope
            FROM facts
            GROUP BY 1, 2, 3, 4, 5
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()[0]

    return [
        QualityCheck(
            "source_rows_parsed",
            "pass" if rows_parsed > 0 else "fail",
            "info" if rows_parsed > 0 else "error",
            str(rows_parsed),
            "> 0",
            "Finance source file parsed successfully.",
        ),
        QualityCheck(
            "staging_rows_loaded",
            "pass" if staging_rows == rows_parsed else "fail",
            "info" if staging_rows == rows_parsed else "error",
            str(staging_rows),
            str(rows_parsed),
            "Every parsed source row should be represented in staging.",
        ),
        QualityCheck(
            "facts_loaded",
            "pass" if facts_loaded > 0 else "fail",
            "info" if facts_loaded > 0 else "error",
            str(facts_loaded),
            "> 0",
            "Canonical facts loaded for matched providers.",
        ),
        QualityCheck(
            "unmatched_source_providers",
            "warn" if unmatched_providers else "pass",
            "warning" if unmatched_providers else "info",
            str(len(unmatched_providers)),
            "0 public-university providers unmatched",
            ", ".join(unmatched_providers) if unmatched_providers else "All source provider names matched.",
        ),
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
            "Provider/metric/source/year/scope should be unique in canonical facts.",
        ),
    ]


def persist_quality_checks(
    conn: duckdb.DuckDBPyConnection,
    run_id: str,
    source_file_id: str,
    checks: list[QualityCheck],
) -> None:
    rows = []
    for check in checks:
        check_id = hashlib.sha1(f"{run_id}|{source_file_id}|{check.check_name}".encode()).hexdigest()
        rows.append(
            (
                check_id,
                run_id,
                source_file_id,
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
    run_id: str,
    source_file_id: str,
    raw_path: Path,
    source_url: str,
    year: int,
    rows_parsed: int,
    staging_rows: int,
    facts_loaded: int,
    metrics_loaded: int,
    unmatched_providers: list[str],
    checks: list[QualityCheck],
) -> Path:
    QUALITY_DIR.mkdir(parents=True, exist_ok=True)
    report_path = QUALITY_DIR / f"finance_{year}_{run_id}.json"
    report = {
        "run_id": run_id,
        "source_file_id": source_file_id,
        "source_dataset": finance_source_name(year),
        "source_url": source_url,
        "raw_path": str(raw_path),
        "reporting_year": year,
        "rows_parsed": rows_parsed,
        "staging_rows_loaded": staging_rows,
        "facts_loaded": facts_loaded,
        "metrics_loaded": metrics_loaded,
        "unmatched_provider_names": unmatched_providers,
        "checks": [asdict(check) for check in checks],
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report_path


def ingest_finance(
    year: int,
    db_path: Path,
    source_url: str | None = None,
    raw_path: Path | None = None,
    force_download: bool = False,
) -> dict[str, object]:
    source_url = source_url or FINANCE_URLS.get(year)
    if not source_url:
        available_years = ", ".join(str(item) for item in sorted(FINANCE_URLS))
        raise ValueError(f"No finance CSV source is configured for {year}. Available years: {available_years}.")

    raw_path = raw_path or default_raw_path(year, source_url)
    download_file(source_url, raw_path, force=force_download)

    parser = FinanceParser()
    rows = parser.parse(raw_path)
    checksum = sha256_file(raw_path)
    source_file_id = f"{finance_dataset_id(year)}_{checksum[:12]}"
    run_id = f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}_{uuid4().hex[:8]}"

    conn = connect(db_path)
    try:
        init_schema(conn)
        seed_providers(conn)
        upsert_source_dataset(conn, year)
        upsert_source_file(conn, source_file_id, raw_path, source_url, checksum, len(rows), year)
        metric_map = upsert_metrics(conn, [row.line_item for row in rows])
        resolver = ProviderResolver.from_connection(conn)
        staging_rows, facts_loaded, unmatched_providers = load_staging_and_facts(
            conn,
            rows,
            source_file_id,
            run_id,
            resolver,
            metric_map,
        )
        checks = build_quality_checks(
            conn,
            rows_parsed=len(rows),
            staging_rows=staging_rows,
            facts_loaded=facts_loaded,
            source_file_id=source_file_id,
            unmatched_providers=unmatched_providers,
        )
        persist_quality_checks(conn, run_id, source_file_id, checks)
    finally:
        conn.close()

    report_path = write_quality_report(
        run_id=run_id,
        source_file_id=source_file_id,
        raw_path=raw_path,
        source_url=source_url,
        year=year,
        rows_parsed=len(rows),
        staging_rows=staging_rows,
        facts_loaded=facts_loaded,
        metrics_loaded=len(metric_map),
        unmatched_providers=unmatched_providers,
        checks=checks,
    )

    return {
        "run_id": run_id,
        "source_file_id": source_file_id,
        "raw_path": str(raw_path),
        "reporting_year": year,
        "db_path": str(db_path),
        "quality_report": str(report_path),
        "rows_parsed": len(rows),
        "staging_rows_loaded": staging_rows,
        "facts_loaded": facts_loaded,
        "metrics_loaded": len(metric_map),
        "unmatched_provider_names": unmatched_providers,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest Department of Education finance CSV.")
    parser.add_argument("--year", type=int, default=2024)
    parser.add_argument("--db-path", type=Path, default=DB_PATH)
    parser.add_argument("--source-url")
    parser.add_argument("--raw-path", type=Path)
    parser.add_argument("--force-download", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = ingest_finance(
        year=args.year,
        db_path=args.db_path,
        source_url=args.source_url,
        raw_path=args.raw_path,
        force_download=args.force_download,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

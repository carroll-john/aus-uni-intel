from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb

from uni_intel.config import (
    DB_PATH,
    FINANCE_PUBLICATION_URL,
    FINANCE_PUBLICATION_URLS,
    FINANCE_URLS,
    RAW_DIR,
)
from uni_intel.db import connect, init_schema
from uni_intel.ingestion.common import (
    SourceDataset,
    SourceFileMetadata,
    download_file,
    insert_facts,
    metadata_quality_checks,
    new_run_id,
    persist_quality_checks,
    sha256_file,
    source_file_id,
    stable_fact_id,
    standard_quality_checks,
    upsert_metrics,
    upsert_source_dataset,
    upsert_source_file,
    write_quality_report,
)
from uni_intel.ingestion.metrics import (
    SOURCE_AGENCY,
    finance_metric_record,
)
from uni_intel.ingestion.parsers.finance import FinanceParser, FinanceRawRow
from uni_intel.ingestion.provider_matching import ProviderResolver
from uni_intel.seed import seed_providers

SOURCE_LICENSE = "Australian Government Department of Education public data"


def finance_dataset_id(year: int) -> str:
    return f"education_finance_{year}"


def finance_source_name(year: int) -> str:
    return f"Finance {year}: Financial Reports of Higher Education Providers"


def finance_publication_url(year: int) -> str:
    return FINANCE_PUBLICATION_URLS.get(year, FINANCE_PUBLICATION_URL)


def default_raw_path(year: int, source_url: str) -> Path:
    extension = "xlsx" if source_url.rstrip("/").endswith("/xlsx") else "csv"
    return RAW_DIR / "finance" / str(year) / f"finance_{year}_financial_reports_higher_education_providers.{extension}"


def upsert_finance_metrics(conn: duckdb.DuckDBPyConnection, line_items: list[str]) -> dict[str, str]:
    """Upsert one metric per finance line item and return line-item to metric-id map."""
    records = []
    mapping: dict[str, str] = {}
    for line_item in sorted(set(line_items)):
        record = finance_metric_record(line_item)
        records.append(record)
        mapping[line_item] = str(record["metric_id"])
    upsert_metrics(conn, records)
    return mapping


def load_staging_and_facts(
    conn: duckdb.DuckDBPyConnection,
    rows: list[FinanceRawRow],
    source_id: str,
    run_id: str,
    resolver: ProviderResolver,
    metric_map: dict[str, str],
) -> tuple[int, int, list[str]]:
    conn.execute("DELETE FROM stg_finance_rows WHERE source_file_id = ?", [source_id])
    conn.execute("DELETE FROM facts WHERE source_file_id = ?", [source_id])

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
                source_id,
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
                    source_id,
                    provider_match.provider_id,
                    metric_id,
                    row.reporting_year,
                    row.institution_scope,
                ),
                provider_match.provider_id,
                metric_id,
                source_id,
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
    insert_facts(conn, fact_rows)

    return len(staging_rows), len(fact_rows), sorted(unmatched_providers)


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
    dataset_id = finance_dataset_id(year)
    source_id = source_file_id(dataset_id, checksum)
    run_id = new_run_id()

    conn = connect(db_path)
    try:
        init_schema(conn)
        seed_providers(conn)
        upsert_source_dataset(
            conn,
            SourceDataset(
                dataset_id,
                finance_source_name(year),
                SOURCE_AGENCY,
                finance_publication_url(year),
                "Annual Department of Education finance ingestion source.",
            ),
        )
        upsert_source_file(
            conn,
            SourceFileMetadata(
                source_id,
                dataset_id,
                finance_source_name(year),
                source_url,
                raw_path,
                raw_path.suffix.lstrip(".").lower() or "csv",
                year,
                checksum,
                len(rows),
                SOURCE_LICENSE,
                str(year),
                "Headerless CSV extract from Department of Education finance tables.",
            ),
        )
        metric_map = upsert_finance_metrics(conn, [row.line_item for row in rows])
        resolver = ProviderResolver.from_connection(conn)
        staging_rows, facts_loaded, unmatched_providers = load_staging_and_facts(
            conn,
            rows,
            source_id,
            run_id,
            resolver,
            metric_map,
        )
        checks = standard_quality_checks(
            len(rows),
            staging_rows,
            facts_loaded,
            unmatched_providers,
            parsed_detail="Finance source file parsed successfully.",
            facts_detail="Canonical facts loaded for matched providers.",
        )
        checks.extend(metadata_quality_checks(conn))
        persist_quality_checks(conn, run_id, source_id, checks)
    finally:
        conn.close()

    report_path = write_quality_report(
        f"finance_{year}",
        run_id,
        source_id,
        {
            "source_dataset": finance_source_name(year),
            "source_url": source_url,
            "raw_path": str(raw_path),
            "reporting_year": year,
            "rows_parsed": len(rows),
            "staging_rows_loaded": staging_rows,
            "facts_loaded": facts_loaded,
            "metrics_loaded": len(metric_map),
            "unmatched_provider_names": unmatched_providers,
        },
        checks,
    )

    return {
        "run_id": run_id,
        "source_file_id": source_id,
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

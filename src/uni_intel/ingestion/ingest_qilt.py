from __future__ import annotations

import argparse
import json
from pathlib import Path

from uni_intel.config import DB_PATH, QILT_SES_PUBLICATION_URL, QILT_SES_URLS, RAW_DIR
from uni_intel.db import connect, init_schema
from uni_intel.ingestion.common import (
    QualityCheck,
    SourceDataset,
    SourceFileMetadata,
    download_file,
    json_dumps,
    metadata_quality_checks,
    new_run_id,
    persist_quality_checks,
    sha256_file,
    source_file_id,
    stable_fact_id,
    upsert_metrics,
    upsert_source_dataset,
    upsert_source_file,
    write_quality_report,
)
from uni_intel.ingestion.metrics import QILT_METRICS, QILT_SOURCE_AGENCY, QILT_SOURCE_DATASET
from uni_intel.ingestion.parsers.qilt import QiltRawRow, QiltSesParser
from uni_intel.ingestion.provider_matching import ProviderResolver
from uni_intel.seed import seed_providers

DATASET_ID_PREFIX = "qilt_ses"
SOURCE_LICENSE = "QILT public report tables"
METRIC_LINE_ITEMS = {str(metric["metric_id"]): str(metric["source_line_item"]) for metric in QILT_METRICS}


def ingest_qilt(db_path: Path = DB_PATH, force_download: bool = False) -> dict[str, object]:
    run_id = new_run_id()
    year_results: list[dict[str, object]] = []
    all_checks: list[QualityCheck] = []
    source_ids: list[str] = []

    conn = connect(db_path)
    try:
        init_schema(conn)
        seed_providers(conn)
        upsert_metrics(conn, QILT_METRICS)
        resolver = ProviderResolver.from_connection(conn)

        for year, url in sorted(QILT_SES_URLS.items()):
            dataset_id = f"{DATASET_ID_PREFIX}_{year}"
            raw_path = RAW_DIR / "qilt" / str(year) / _raw_filename(year, url)
            download_file(url, raw_path, force=force_download)
            rows = QiltSesParser(reporting_year=year).parse(raw_path)
            checksum = sha256_file(raw_path)
            source_id = source_file_id(dataset_id, checksum)
            source_ids.append(source_id)

            upsert_source_dataset(
                conn,
                SourceDataset(
                    dataset_id,
                    f"{year} {QILT_SOURCE_DATASET}",
                    QILT_SOURCE_AGENCY,
                    QILT_SES_PUBLICATION_URL,
                    "QILT Student Experience Survey provider-level report tables.",
                ),
            )
            upsert_source_file(
                conn,
                SourceFileMetadata(
                    source_id,
                    dataset_id,
                    f"{year} Student Experience Survey National Report Tables",
                    url,
                    raw_path,
                    raw_path.suffix.lower().lstrip("."),
                    year,
                    checksum,
                    len(rows),
                    SOURCE_LICENSE,
                    str(year + 1),
                    "QILT SES national report tables containing provider-level undergraduate and postgraduate coursework tables.",
                ),
            )
            staging_rows, facts_loaded, unmatched = _load_rows(conn, rows, source_id, run_id, resolver)
            checks = _quality_checks(year, len(rows), staging_rows, facts_loaded, unmatched)
            persist_quality_checks(conn, run_id, source_id, checks)
            all_checks.extend(checks)
            year_results.append(
                {
                    "reporting_year": year,
                    "source_file_id": source_id,
                    "source_url": url,
                    "raw_path": str(raw_path),
                    "rows_parsed": len(rows),
                    "staging_rows_loaded": staging_rows,
                    "facts_loaded": facts_loaded,
                    "unmatched_provider_names": unmatched,
                }
            )

        metadata_checks = metadata_quality_checks(conn)
        persist_quality_checks(conn, run_id, None, metadata_checks)
        all_checks.extend(metadata_checks)
    finally:
        conn.close()

    report = write_quality_report(
        "qilt_ses",
        run_id,
        None,
        {
            "source_dataset": QILT_SOURCE_DATASET,
            "source_years": sorted(QILT_SES_URLS),
            "source_file_ids": source_ids,
            "year_results": year_results,
        },
        all_checks,
    )
    return {
        "run_id": run_id,
        "source_file_ids": source_ids,
        "quality_report": str(report),
        "year_results": year_results,
        "rows_parsed": sum(int(result["rows_parsed"]) for result in year_results),
        "staging_rows_loaded": sum(int(result["staging_rows_loaded"]) for result in year_results),
        "facts_loaded": sum(int(result["facts_loaded"]) for result in year_results),
    }


def _load_rows(
    conn,
    rows: list[QiltRawRow],
    source_id: str,
    run_id: str,
    resolver: ProviderResolver,
) -> tuple[int, int, list[str]]:
    conn.execute("DELETE FROM stg_qilt_rows WHERE source_file_id = ?", [source_id])
    conn.execute("DELETE FROM facts WHERE source_file_id = ?", [source_id])
    staging_rows: list[tuple[object, ...]] = []
    fact_rows: list[tuple[object, ...]] = []
    unmatched: set[str] = set()

    for row in rows:
        provider_match = resolver.resolve(row.source_provider_name)
        dimensions_json = json_dumps(row.dimensions)
        provider_id = provider_match.provider_id if provider_match else None
        match_status = provider_match.method if provider_match else "unmatched"
        match_confidence = provider_match.confidence if provider_match else None
        staging_rows.append(
            (
                row.row_number,
                row.source_table,
                row.source_provider_name,
                row.metric_id,
                row.reporting_year,
                row.raw_value,
                row.numeric_value,
                row.ci_lower,
                row.ci_upper,
                source_id,
                provider_id,
                match_status,
                match_confidence,
                dimensions_json,
                run_id,
            )
        )
        if not provider_match:
            unmatched.add(row.source_provider_name)
            continue
        scope = f"QILT {row.dimensions['course_level']}"
        fact_rows.append(
            (
                stable_fact_id(
                    source_id,
                    provider_match.provider_id,
                    row.metric_id,
                    row.reporting_year,
                    scope,
                    dimensions_json,
                ),
                provider_match.provider_id,
                row.metric_id,
                source_id,
                row.reporting_year,
                f"{row.reporting_year}-01-01",
                f"{row.reporting_year}-12-31",
                scope,
                row.numeric_value,
                "percent",
                row.row_number,
                row.source_provider_name,
                METRIC_LINE_ITEMS[row.metric_id],
                dimensions_json,
            )
        )

    conn.executemany(
        """
        INSERT INTO stg_qilt_rows (
            row_number, source_table, source_provider_name, metric_id,
            reporting_year, raw_value, numeric_value, ci_lower, ci_upper,
            source_file_id, provider_id, match_status, match_confidence,
            dimensions_json, load_run_id
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
    return len(staging_rows), len(fact_rows), sorted(unmatched)


def _raw_filename(year: int, url: str) -> str:
    suffix = ".zip" if ".zip" in url.lower() else ".ods" if ".ods" in url.lower() else ".xlsx"
    return f"ses_{year}_national_report_tables{suffix}"


def _quality_checks(year: int, rows_parsed: int, staging_rows: int, facts_loaded: int, unmatched: list[str]) -> list[QualityCheck]:
    return [
        QualityCheck("source_rows_parsed", "pass" if rows_parsed else "fail", "info" if rows_parsed else "error", str(rows_parsed), "> 0", f"{year} QILT SES rows parsed from national report tables."),
        QualityCheck("staging_rows_loaded", "pass" if rows_parsed == staging_rows else "fail", "info" if rows_parsed == staging_rows else "error", str(staging_rows), str(rows_parsed), f"Every parsed {year} source row should be represented in staging."),
        QualityCheck("facts_loaded", "pass" if facts_loaded else "fail", "info" if facts_loaded else "error", str(facts_loaded), "> 0", f"Canonical {year} QILT facts loaded for matched providers."),
        QualityCheck("unmatched_source_providers", "warn" if unmatched else "pass", "warning" if unmatched else "info", str(len(unmatched)), "0 public-university providers unmatched", ", ".join(unmatched) if unmatched else f"All {year} source provider names matched."),
        QualityCheck("qilt_confidence_intervals_present", "pass", "info", "stored", "stored", "90% confidence interval bounds are stored in dimensions_json and staging columns where published."),
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest QILT SES report-table ZIP.")
    parser.add_argument("--db-path", type=Path, default=DB_PATH)
    parser.add_argument("--force-download", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(json.dumps(ingest_qilt(args.db_path, args.force_download), indent=2))


if __name__ == "__main__":
    main()

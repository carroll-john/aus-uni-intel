from __future__ import annotations

import argparse
import json
from pathlib import Path

from uni_intel.config import DB_PATH, HERDC_PUBLICATION_URL, HERDC_RESEARCH_INCOME_URL, RAW_DIR
from uni_intel.db import connect, init_schema
from uni_intel.ingestion.common import (
    SourceDataset,
    SourceFileMetadata,
    download_file,
    insert_facts,
    json_dumps,
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
from uni_intel.ingestion.metrics import HERDC_METRICS, HERDC_SOURCE_DATASET, SOURCE_AGENCY
from uni_intel.ingestion.parsers.herdc import HerdcRawRow, HerdcResearchIncomeParser
from uni_intel.ingestion.provider_matching import ProviderResolver
from uni_intel.seed import seed_providers

DATASET_ID = "education_herdc_research_income"
SOURCE_LICENSE = "Australian Government Department of Education public data"
METRIC_LINE_ITEMS = {str(metric["metric_id"]): str(metric["source_line_item"]) for metric in HERDC_METRICS}


def ingest_herdc(
    db_path: Path = DB_PATH,
    force_download: bool = False,
) -> dict[str, object]:
    raw_path = RAW_DIR / "herdc" / "research_income_time_series.xlsx"
    download_file(HERDC_RESEARCH_INCOME_URL, raw_path, force=force_download)
    rows = HerdcResearchIncomeParser().parse(raw_path)
    checksum = sha256_file(raw_path)
    source_id = source_file_id(DATASET_ID, checksum)
    run_id = new_run_id()

    conn = connect(db_path)
    try:
        init_schema(conn)
        seed_providers(conn)
        upsert_source_dataset(
            conn,
            SourceDataset(
                DATASET_ID,
                HERDC_SOURCE_DATASET,
                SOURCE_AGENCY,
                HERDC_PUBLICATION_URL,
                "HERDC research and development income time series.",
            ),
        )
        upsert_source_file(
            conn,
            SourceFileMetadata(
                source_id,
                DATASET_ID,
                "Research and Development Income Time Series",
                HERDC_RESEARCH_INCOME_URL,
                raw_path,
                "xlsx",
                None,
                checksum,
                len(rows),
                SOURCE_LICENSE,
                "2025",
                "Department HERDC research income time series workbook.",
            ),
        )
        upsert_metrics(conn, HERDC_METRICS)
        resolver = ProviderResolver.from_connection(conn)
        staging_rows, facts_loaded, unmatched = _load_rows(conn, rows, source_id, run_id, resolver)
        checks = standard_quality_checks(
            len(rows),
            staging_rows,
            facts_loaded,
            unmatched,
            parsed_detail="HERDC rows parsed.",
            facts_detail="Canonical HERDC facts loaded for matched providers.",
        )
        checks.extend(metadata_quality_checks(conn))
        persist_quality_checks(conn, run_id, source_id, checks)
    finally:
        conn.close()

    report = write_quality_report(
        "herdc_research_income",
        run_id,
        source_id,
        {
            "source_dataset": HERDC_SOURCE_DATASET,
            "source_url": HERDC_RESEARCH_INCOME_URL,
            "raw_path": str(raw_path),
            "rows_parsed": len(rows),
            "staging_rows_loaded": staging_rows,
            "facts_loaded": facts_loaded,
            "unmatched_provider_names": unmatched,
        },
        checks,
    )
    return {
        "run_id": run_id,
        "source_file_id": source_id,
        "raw_path": str(raw_path),
        "quality_report": str(report),
        "rows_parsed": len(rows),
        "staging_rows_loaded": staging_rows,
        "facts_loaded": facts_loaded,
        "unmatched_provider_names": unmatched,
    }


def _load_rows(
    conn,
    rows: list[HerdcRawRow],
    source_id: str,
    run_id: str,
    resolver: ProviderResolver,
) -> tuple[int, int, list[str]]:
    conn.execute("DELETE FROM stg_herdc_rows WHERE source_file_id = ?", [source_id])
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
                row.hep_code,
                row.source_provider_name,
                row.metric_id,
                row.reporting_year,
                row.raw_value,
                row.numeric_value,
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
        fact_rows.append(
            (
                stable_fact_id(
                    source_id,
                    provider_match.provider_id,
                    row.metric_id,
                    row.reporting_year,
                    "HERDC",
                    dimensions_json,
                ),
                provider_match.provider_id,
                row.metric_id,
                source_id,
                row.reporting_year,
                f"{row.reporting_year}-01-01",
                f"{row.reporting_year}-12-31",
                "HERDC",
                row.numeric_value,
                "AUD",
                row.row_number,
                row.source_provider_name,
                METRIC_LINE_ITEMS[row.metric_id],
                dimensions_json,
            )
        )

    conn.executemany(
        """
        INSERT INTO stg_herdc_rows (
            row_number, hep_code, source_provider_name, metric_id,
            reporting_year, raw_value, numeric_value, source_file_id, provider_id,
            match_status, match_confidence, dimensions_json, load_run_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        staging_rows,
    )
    insert_facts(conn, fact_rows)
    return len(staging_rows), len(fact_rows), sorted(unmatched)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest HERDC research income workbook.")
    parser.add_argument("--db-path", type=Path, default=DB_PATH)
    parser.add_argument("--force-download", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(json.dumps(ingest_herdc(args.db_path, args.force_download), indent=2))


if __name__ == "__main__":
    main()

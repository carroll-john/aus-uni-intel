from __future__ import annotations

import argparse
import json
from pathlib import Path

from uni_intel.config import (
    DB_PATH,
    STUDENT_PUBLICATION_URL,
)
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
from uni_intel.ingestion.metrics import SOURCE_AGENCY, STUDENT_METRICS, STUDENT_SOURCE_DATASET
from uni_intel.ingestion.parsers.student import StudentRawRow
from uni_intel.ingestion.provider_matching import ProviderResolver
from uni_intel.ingestion.student_sources import build_student_sources
from uni_intel.seed import seed_providers

DATASET_ID = "education_student"
SOURCE_LICENSE = "Australian Government Department of Education public data"
METRIC_LINE_ITEMS = {str(metric["metric_id"]): str(metric["source_line_item"]) for metric in STUDENT_METRICS}
HISTORICAL_STUDENT_METRICS = {str(metric["metric_id"]) for metric in STUDENT_METRICS}


def ingest_student(
    year: int = 2024,
    db_path: Path = DB_PATH,
    force_download: bool = False,
) -> dict[str, object]:
    if year != 2024:
        raise ValueError("The current student publication year is 2024.")

    sources = build_student_sources()

    run_id = new_run_id()
    conn = connect(db_path)
    results: list[dict[str, object]] = []
    try:
        init_schema(conn)
        seed_providers(conn)
        upsert_source_dataset(
            conn,
            SourceDataset(
                DATASET_ID,
                STUDENT_SOURCE_DATASET,
                SOURCE_AGENCY,
                STUDENT_PUBLICATION_URL,
                "Student enrolment, EFTSL, and completions sources.",
            ),
        )
        upsert_metrics(conn, STUDENT_METRICS)
        resolver = ProviderResolver.from_connection(conn)
        purge_existing_student_facts(conn)

        for slug, url, raw_path, parser, source_name in sources:
            download_file(url, raw_path, force=force_download)
            rows = parser.parse(raw_path)
            checksum = sha256_file(raw_path)
            source_id = source_file_id(f"{DATASET_ID}_{slug}", checksum)
            upsert_source_file(
                conn,
                SourceFileMetadata(
                    source_id,
                    DATASET_ID,
                    source_name,
                    url,
                    raw_path,
                    raw_path.suffix.lstrip("."),
                    source_reporting_year(parser, year),
                    checksum,
                    len(rows),
                    SOURCE_LICENSE,
                    str(source_reporting_year(parser, year)),
                    "Department student statistics Excel workbook.",
                ),
            )
            staging_rows, facts_loaded, unmatched = _load_rows(conn, rows, source_id, run_id, resolver)
            checks = standard_quality_checks(
                len(rows),
                staging_rows,
                facts_loaded,
                unmatched,
                parsed_detail="Student source rows parsed.",
                facts_detail="Canonical student facts loaded for matched providers.",
            )
            checks.extend(metadata_quality_checks(conn))
            persist_quality_checks(conn, run_id, source_id, checks)
            report = write_quality_report(
                slug,
                run_id,
                source_id,
                {
                    "source_dataset": STUDENT_SOURCE_DATASET,
                    "source_url": url,
                    "raw_path": str(raw_path),
                    "rows_parsed": len(rows),
                    "staging_rows_loaded": staging_rows,
                    "facts_loaded": facts_loaded,
                    "unmatched_provider_names": unmatched,
                },
                checks,
            )
            results.append(
                {
                    "source_file_id": source_id,
                    "raw_path": str(raw_path),
                    "quality_report": str(report),
                    "rows_parsed": len(rows),
                    "staging_rows_loaded": staging_rows,
                    "facts_loaded": facts_loaded,
                    "unmatched_provider_names": unmatched,
                }
            )
    finally:
        conn.close()

    return {"run_id": run_id, "sources": results}


def source_reporting_year(parser: object, default_year: int) -> int:
    parser_year = getattr(parser, "year", None)
    return parser_year if isinstance(parser_year, int) else default_year


def purge_existing_student_facts(conn) -> None:
    metric_ids = ", ".join(f"'{metric_id}'" for metric_id in sorted(HISTORICAL_STUDENT_METRICS))
    conn.execute(
        f"""
        DELETE FROM facts
        WHERE metric_id IN ({metric_ids})
          AND source_file_id IN (
              SELECT source_file_id
              FROM source_files
              WHERE dataset_id LIKE 'education_student%'
          )
        """
    )


def _load_rows(
    conn,
    rows: list[StudentRawRow],
    source_id: str,
    run_id: str,
    resolver: ProviderResolver,
) -> tuple[int, int, list[str]]:
    conn.execute("DELETE FROM stg_student_rows WHERE source_file_id = ?", [source_id])
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
                row.sheet_name,
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
                    "Student",
                    dimensions_json,
                ),
                provider_match.provider_id,
                row.metric_id,
                source_id,
                row.reporting_year,
                f"{row.reporting_year}-01-01",
                f"{row.reporting_year}-12-31",
                "Student",
                row.numeric_value,
                "students"
                if "enrolments" in row.metric_id
                else ("EFTSL" if "eftsl" in row.metric_id else "completions"),
                row.row_number,
                row.source_provider_name,
                METRIC_LINE_ITEMS[row.metric_id],
                dimensions_json,
            )
        )

    conn.executemany(
        """
        INSERT INTO stg_student_rows (
            row_number, source_table, sheet_name, source_provider_name, metric_id,
            reporting_year, raw_value, numeric_value, source_file_id, provider_id,
            match_status, match_confidence, dimensions_json, load_run_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        staging_rows,
    )
    insert_facts(conn, fact_rows)
    return len(staging_rows), len(fact_rows), sorted(unmatched)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest Department student data workbooks.")
    parser.add_argument("--year", type=int, default=2024)
    parser.add_argument("--db-path", type=Path, default=DB_PATH)
    parser.add_argument("--force-download", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(
        json.dumps(
            ingest_student(args.year, args.db_path, args.force_download),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

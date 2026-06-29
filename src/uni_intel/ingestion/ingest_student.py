from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.request
from urllib.parse import urljoin

from uni_intel.config import (
    DB_PATH,
    RAW_DIR,
    STUDENT_ANNUAL_PAGE_URLS,
    STUDENT_COMPLETIONS_2024_URL,
    STUDENT_PUBLICATION_URL,
    STUDENT_SECTION_YEARS,
)
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
from uni_intel.ingestion.metrics import SOURCE_AGENCY, STUDENT_METRICS, STUDENT_SOURCE_DATASET
from uni_intel.ingestion.parsers.student import (
    StudentCompletionsParser,
    StudentRawRow,
    StudentSectionParser,
)
from uni_intel.ingestion.provider_matching import ProviderResolver
from uni_intel.seed import seed_providers


DATASET_ID = "education_student"
SOURCE_LICENSE = "Australian Government Department of Education public data"
METRIC_LINE_ITEMS = {str(metric["metric_id"]): str(metric["source_line_item"]) for metric in STUDENT_METRICS}
SECTION_SPECS = {
    1: {
        "slug": "commencing_students",
        "sheet_name": "1.5",
        "metric_id": "student_commencing_enrolments",
        "population": "Commencing Students",
        "total_column": "Total",
        "source_label": "Commencing students",
    },
    2: {
        "slug": "all_students",
        "sheet_name": "2.5",
        "metric_id": "student_total_enrolments",
        "population": "All Students",
        "total_column": "Total",
        "source_label": "All students",
    },
    3: {
        "slug": "commencing_student_load",
        "sheet_name": "3.1",
        "metric_id": "student_commencing_load_eftsl",
        "population": "Commencing Students EFTSL",
        "total_column": "Total EFTSL",
        "source_label": "Commencing student load",
    },
    4: {
        "slug": "all_student_load",
        "sheet_name": "4.1",
        "metric_id": "student_total_load_eftsl",
        "population": "All Students EFTSL",
        "total_column": "Total",
        "source_label": "All student load",
    },
}
HISTORICAL_STUDENT_METRICS = {str(spec["metric_id"]) for spec in SECTION_SPECS.values()}


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
                    parser.year if isinstance(parser, StudentSectionParser) else year,
                    checksum,
                    len(rows),
                    SOURCE_LICENSE,
                    str(parser.year) if isinstance(parser, StudentSectionParser) else "2024",
                    "Department student statistics Excel workbook.",
                ),
            )
            staging_rows, facts_loaded, unmatched = _load_rows(
                conn, rows, source_id, run_id, resolver
            )
            checks = _quality_checks(len(rows), staging_rows, facts_loaded, unmatched)
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


def build_student_sources() -> list[tuple[str, str, Path, object, str]]:
    sources: list[tuple[str, str, Path, object, str]] = []
    for source_year in STUDENT_SECTION_YEARS:
        for section, spec in SECTION_SPECS.items():
            source_url = resolve_student_section_xlsx_url(source_year, section)
            file_extension = source_extension(source_url)
            slug = f"student_{source_year}_section_{section}_{spec['slug']}"
            sources.append(
                (
                    slug,
                    source_url,
                    (
                        RAW_DIR
                        / "student"
                        / str(source_year)
                        / f"section_{section}_{spec['slug']}_{source_year}.{file_extension}"
                    ),
                    StudentSectionParser(
                        year=source_year,
                        section=section,
                        sheet_name=str(spec["sheet_name"]),
                        metric_id=str(spec["metric_id"]),
                        population=str(spec["population"]),
                        total_column_name=str(spec["total_column"]),
                    ),
                    f"{source_year} Section {section} - {spec['source_label']}",
                )
            )

    sources.append(
        (
            "student_completions_2024",
            STUDENT_COMPLETIONS_2024_URL,
            RAW_DIR / "student" / "2024" / "student_completions_2024.xlsx",
            StudentCompletionsParser(),
            "2024 Section 14 Award Course Completions",
        )
    )
    return sources


def resolve_student_section_xlsx_url(year: int, section: int) -> str:
    annual_page = STUDENT_ANNUAL_PAGE_URLS[year]
    resource_page = find_link(
        annual_page,
        lambda text, href: bool(re.search(rf"\bsection\s+{section}\b", text))
        and str(year) in f"{text} {href}"
        and "resources" in href,
    )
    return find_link(
        resource_page,
        lambda text, href: href.rstrip("/").endswith(("/xlsx", "/xls"))
        or "xlsx" in text
        or "xls" in text,
    )


def source_extension(url: str) -> str:
    return "xlsx" if url.rstrip("/").endswith("/xlsx") else "xls"


def find_link(page_url: str, predicate) -> str:
    with urllib.request.urlopen(page_url) as response:
        html = response.read().decode("utf-8", errors="replace")
    parser = LinkParser(page_url)
    parser.feed(html)
    for text, href in parser.links:
        normalized_text = " ".join(text.lower().split())
        if predicate(normalized_text, href):
            return href
    raise ValueError(f"Required student source link not found on {page_url}")


class LinkParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.links: list[tuple[str, str]] = []
        self._current_href: str | None = None
        self._current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attr_map = dict(attrs)
        self._current_href = attr_map.get("href")
        self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_href is not None:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self._current_href is None:
            return
        self.links.append(
            (
                "".join(self._current_text),
                urljoin(self.base_url, self._current_href),
            )
        )
        self._current_href = None
        self._current_text = []


def purge_existing_student_facts(conn) -> None:
    conn.execute(
        """
        DELETE FROM facts
        WHERE metric_id IN (
            'student_commencing_enrolments',
            'student_total_enrolments',
            'student_commencing_load_eftsl',
            'student_total_load_eftsl',
            'student_award_course_completions'
        )
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
                "students" if "enrolments" in row.metric_id else ("EFTSL" if "eftsl" in row.metric_id else "completions"),
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


def _quality_checks(
    rows_parsed: int,
    staging_rows: int,
    facts_loaded: int,
    unmatched: list[str],
) -> list[QualityCheck]:
    return [
        QualityCheck(
            "source_rows_parsed",
            "pass" if rows_parsed > 0 else "fail",
            "info" if rows_parsed > 0 else "error",
            str(rows_parsed),
            "> 0",
            "Student source rows parsed.",
        ),
        QualityCheck(
            "staging_rows_loaded",
            "pass" if rows_parsed == staging_rows else "fail",
            "info" if rows_parsed == staging_rows else "error",
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
            "Canonical student facts loaded for matched providers.",
        ),
        QualityCheck(
            "unmatched_source_providers",
            "warn" if unmatched else "pass",
            "warning" if unmatched else "info",
            str(len(unmatched)),
            "0 public-university providers unmatched",
            ", ".join(unmatched) if unmatched else "All source provider names matched.",
        ),
    ]


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

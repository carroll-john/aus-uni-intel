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
    StudentMetricColumn,
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
        "metric_columns": (
            StudentMetricColumn(
                "student_commencing_enrolments",
                "Commencing Students",
                ("Total",),
                "Total",
            ),
            StudentMetricColumn(
                "student_postgraduate_research_commencing_enrolments",
                "Commencing Postgraduate by Research",
                ("Postgraduate by Research",),
                "Postgraduate by Research",
                (("Doctorate by Research", "Master's by Research"), ("Doctorate by Research", "Masters by Research")),
            ),
            StudentMetricColumn(
                "student_postgraduate_coursework_commencing_enrolments",
                "Commencing Postgraduate by Coursework",
                ("Postgraduate by Coursework",),
                "Postgraduate by Coursework",
                (
                    (
                        "Doctorate by Coursework",
                        "Master's (Extended)",
                        "Master's by Coursework",
                        "Other Postgraduate",
                    ),
                    (
                        "Doctorate by Coursework",
                        "Masters (Extended)",
                        "Masters by Coursework",
                        "Other Postgraduate",
                    ),
                ),
            ),
            StudentMetricColumn(
                "student_postgraduate_total_commencing_enrolments",
                "Commencing Postgraduate",
                ("Postgraduate by Research", "Postgraduate by Coursework"),
                "Postgraduate by Research + Postgraduate by Coursework",
                (
                    (
                        "Doctorate by Research",
                        "Doctorate by Coursework",
                        "Master's (Extended)",
                        "Master's by Research",
                        "Master's by Coursework",
                        "Other Postgraduate",
                    ),
                    (
                        "Doctorate by Research",
                        "Doctorate by Coursework",
                        "Masters (Extended)",
                        "Masters by Research",
                        "Masters by Coursework",
                        "Other Postgraduate",
                    ),
                ),
            ),
        ),
    },
    2: {
        "slug": "all_students",
        "sheet_name": "2.5",
        "metric_id": "student_total_enrolments",
        "population": "All Students",
        "total_column": "Total",
        "source_label": "All students",
        "metric_columns": (
            StudentMetricColumn(
                "student_total_enrolments",
                "All Students",
                ("Total",),
                "Total",
            ),
            StudentMetricColumn(
                "student_postgraduate_research_enrolments",
                "Postgraduate by Research",
                ("Postgraduate by Research",),
                "Postgraduate by Research",
                (("Doctorate by Research", "Master's by Research"), ("Doctorate by Research", "Masters by Research")),
            ),
            StudentMetricColumn(
                "student_postgraduate_coursework_enrolments",
                "Postgraduate by Coursework",
                ("Postgraduate by Coursework",),
                "Postgraduate by Coursework",
                (
                    (
                        "Doctorate by Coursework",
                        "Master's (Extended)",
                        "Master's by Coursework",
                        "Other Postgraduate",
                    ),
                    (
                        "Doctorate by Coursework",
                        "Masters (Extended)",
                        "Masters by Coursework",
                        "Other Postgraduate",
                    ),
                ),
            ),
            StudentMetricColumn(
                "student_postgraduate_total_enrolments",
                "Postgraduate",
                ("Postgraduate by Research", "Postgraduate by Coursework"),
                "Postgraduate by Research + Postgraduate by Coursework",
                (
                    (
                        "Doctorate by Research",
                        "Doctorate by Coursework",
                        "Master's (Extended)",
                        "Master's by Research",
                        "Master's by Coursework",
                        "Other Postgraduate",
                    ),
                    (
                        "Doctorate by Research",
                        "Doctorate by Coursework",
                        "Masters (Extended)",
                        "Masters by Research",
                        "Masters by Coursework",
                        "Other Postgraduate",
                    ),
                ),
            ),
        ),
    },
    3: {
        "slug": "commencing_student_load",
        "sheet_name": "3.1",
        "metric_id": "student_commencing_load_eftsl",
        "population": "Commencing Students EFTSL",
        "total_column": "Total EFTSL",
        "source_label": "Commencing student load",
        "metric_columns": (
            StudentMetricColumn(
                "student_commencing_load_eftsl",
                "Commencing Students EFTSL",
                ("Total EFTSL",),
                "Total",
            ),
        ),
    },
    4: {
        "slug": "all_student_load",
        "sheet_name": "4.1",
        "metric_id": "student_total_load_eftsl",
        "population": "All Students EFTSL",
        "total_column": "Total",
        "source_label": "All student load",
        "metric_columns": (
            StudentMetricColumn(
                "student_total_load_eftsl",
                "All Students EFTSL",
                ("Total",),
                "Total",
            ),
            StudentMetricColumn(
                "student_postgraduate_research_load_eftsl",
                "Postgraduate by Research EFTSL",
                ("Postgraduate by Research",),
                "Postgraduate by Research",
                (("Doctorate by Research", "Master's by Research"), ("Doctorate by Research", "Masters by Research")),
            ),
            StudentMetricColumn(
                "student_postgraduate_coursework_load_eftsl",
                "Postgraduate by Coursework EFTSL",
                ("Postgraduate by Coursework",),
                "Postgraduate by Coursework",
                (
                    (
                        "Doctorate by Coursework",
                        "Master's (Extended)",
                        "Master's by Coursework",
                        "Other Postgraduate",
                    ),
                    (
                        "Doctorate by Coursework",
                        "Masters (Extended)",
                        "Masters by Coursework",
                        "Other Postgraduate",
                    ),
                ),
            ),
            StudentMetricColumn(
                "student_postgraduate_total_load_eftsl",
                "Postgraduate EFTSL",
                ("Postgraduate by Research", "Postgraduate by Coursework"),
                "Postgraduate by Research + Postgraduate by Coursework",
                (
                    (
                        "Doctorate by Research",
                        "Doctorate by Coursework",
                        "Master's (Extended)",
                        "Master's by Research",
                        "Master's by Coursework",
                        "Other Postgraduate",
                    ),
                    (
                        "Doctorate by Research",
                        "Doctorate by Coursework",
                        "Masters (Extended)",
                        "Masters by Research",
                        "Masters by Coursework",
                        "Other Postgraduate",
                    ),
                ),
            ),
        ),
    },
}
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
                        metric_columns=tuple(spec.get("metric_columns", ())),
                    ),
                    f"{source_year} Section {section} - {spec['source_label']}",
                )
            )

    for source_year in STUDENT_SECTION_YEARS:
        source_url = (
            STUDENT_COMPLETIONS_2024_URL
            if source_year == 2024
            else resolve_student_section_xlsx_url(source_year, 14)
        )
        file_extension = source_extension(source_url)
        sources.append(
            (
                f"student_{source_year}_section_14_completions",
                source_url,
                RAW_DIR
                / "student"
                / str(source_year)
                / f"section_14_completions_{source_year}.{file_extension}",
                StudentCompletionsParser(
                    year=source_year,
                    parse_total_time_series=source_year == 2024,
                    parse_level_metrics=True,
                ),
                f"{source_year} Section 14 - Award course completions",
            )
        )
    return sources


def source_reporting_year(parser: object, default_year: int) -> int:
    parser_year = getattr(parser, "year", None)
    return parser_year if isinstance(parser_year, int) else default_year


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

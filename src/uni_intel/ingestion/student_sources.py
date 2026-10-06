"""Student dataset source discovery.

Holds the per-section column specifications and the HTML-scraping logic that
resolves annual Department of Education student workbook URLs. Kept separate from
the ingestion runner so the runner focuses on staging and fact loading.
"""

from __future__ import annotations

import re
import urllib.request
from collections.abc import Callable
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

from uni_intel.config import (
    RAW_DIR,
    STUDENT_ANNUAL_PAGE_URLS,
    STUDENT_COMPLETIONS_2024_URL,
    STUDENT_SECTION_YEARS,
)
from uni_intel.ingestion.common import DOWNLOAD_TIMEOUT_SECONDS
from uni_intel.ingestion.parsers.student import (
    StudentCompletionsParser,
    StudentMetricColumn,
    StudentSectionParser,
)

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


StudentParser = StudentSectionParser | StudentCompletionsParser


def build_student_sources() -> list[tuple[str, str, Path, StudentParser, str]]:
    sources: list[tuple[str, str, Path, StudentParser, str]] = []
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
            STUDENT_COMPLETIONS_2024_URL if source_year == 2024 else resolve_student_section_xlsx_url(source_year, 14)
        )
        file_extension = source_extension(source_url)
        sources.append(
            (
                f"student_{source_year}_section_14_completions",
                source_url,
                RAW_DIR / "student" / str(source_year) / f"section_14_completions_{source_year}.{file_extension}",
                StudentCompletionsParser(
                    year=source_year,
                    parse_total_time_series=source_year == 2024,
                    parse_level_metrics=True,
                ),
                f"{source_year} Section 14 - Award course completions",
            )
        )
    return sources


def resolve_student_section_xlsx_url(year: int, section: int) -> str:
    annual_page = STUDENT_ANNUAL_PAGE_URLS[year]
    resource_page = find_link(
        annual_page,
        lambda text, href: (
            bool(re.search(rf"\bsection\s+{section}\b", text)) and str(year) in f"{text} {href}" and "resources" in href
        ),
    )
    return find_link(
        resource_page,
        lambda text, href: href.rstrip("/").endswith(("/xlsx", "/xls")) or "xlsx" in text or "xls" in text,
    )


def source_extension(url: str) -> str:
    return "xlsx" if url.rstrip("/").endswith("/xlsx") else "xls"


def find_link(page_url: str, predicate: Callable[[str, str], bool]) -> str:
    with urllib.request.urlopen(page_url, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
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

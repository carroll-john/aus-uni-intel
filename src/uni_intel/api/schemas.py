"""Pydantic response models for the API.

Applied via ``response_model=`` on the flat list/object endpoints to document the
contract and validate output. The deeply nested/dynamic endpoints (overview,
provider profile, metric insight) return plain dicts by design.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class Provider(BaseModel):
    provider_id: str
    provider_name: str
    state: str | None = None
    provider_type: str | None = None
    is_public: bool | None = None
    website: str | None = None
    mission_group: str | None = None
    table_classification: str | None = None


class Metric(BaseModel):
    metric_id: str
    metric_name: str
    metric_group: str | None = None
    unit: str | None = None
    value_type: str | None = None
    definition: str | None = None
    source_agency: str | None = None
    source_dataset: str | None = None
    source_table: str | None = None
    source_line_item: str | None = None
    is_calculated: bool | None = None
    calculation_method: str | None = None


class CatalogEntry(BaseModel):
    metric_id: str | None = None
    metric_name: str
    raw_metric_name: str | None = None
    metric_group: str | None = None
    raw_metric_group: str | None = None
    catalog_group: str
    catalog_item_id: str
    preferred_scope: str | None = None
    source_status: str
    source_note: str | None = None
    unit: str | None = None
    value_type: str | None = None
    definition: str | None = None
    source_agency: str | None = None
    source_dataset: str | None = None
    source_table: str | None = None
    source_line_item: str | None = None
    is_calculated: bool | None = None
    calculation_method: str | None = None
    selectable: bool


class YearRow(BaseModel):
    reporting_year: int


class ScopeRow(BaseModel):
    dimension_scope: str


class SourceFile(BaseModel):
    source_file_id: str
    dataset_id: str | None = None
    source_name: str | None = None
    source_url: str | None = None
    file_format: str | None = None
    reporting_year: int | None = None
    downloaded_at: datetime | None = None
    checksum_sha256: str | None = None
    row_count: int | None = None
    license: str | None = None
    publication_date: str | None = None
    notes: str | None = None


class QualityCheckRow(BaseModel):
    run_id: str | None = None
    source_file_id: str | None = None
    source_name: str | None = None
    check_name: str | None = None
    status: str | None = None
    severity: str | None = None
    observed_value: str | None = None
    expected_value: str | None = None
    details: str | None = None
    created_at: datetime | None = None


class RankingRow(BaseModel):
    provider_id: str
    provider_name: str
    state: str | None = None
    metric_id: str
    metric_name: str | None = None
    value: float | None = None
    unit: str | None = None
    reporting_year: int
    dimension_scope: str | None = None
    definition: str | None = None
    source_dataset: str | None = None
    is_calculated: bool | None = None
    calculation_method: str | None = None


class BenchmarkRow(BaseModel):
    group_value: str | None = None
    reporting_year: int
    average: float | None = None
    median: float | None = None
    minimum: float | None = None
    maximum: float | None = None
    provider_count: int
    unit: str | None = None


class BenchmarkResponse(BaseModel):
    group_by: str
    rows: list[BenchmarkRow]


class CompareRow(BaseModel):
    provider_id: str
    provider_name: str
    metric_id: str
    metric_name: str | None = None
    value: float | None = None
    unit: str | None = None
    reporting_year: int
    dimension_scope: str | None = None


class TrendRow(BaseModel):
    reporting_year: int
    provider_id: str
    provider_name: str
    metric_id: str
    metric_name: str | None = None
    dimension_scope: str | None = None
    value: float | None = None
    unit: str | None = None

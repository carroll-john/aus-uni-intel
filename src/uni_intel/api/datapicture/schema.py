"""Typed shapes for the Data Picture Studio declarative UI contract.

These are documentation-grade ``TypedDict`` definitions rather than
runtime-validated Pydantic models: every other endpoint in
``uni_intel.api.main`` returns plain dicts built from SQL rows, so this
mirrors that existing convention instead of introducing a second response
style. The frontend keeps a matching TypeScript mirror in
``apps/web/lib/api.ts``; keep the two in sync when this contract changes.
"""

from __future__ import annotations

from typing import Literal, TypedDict

BlockType = Literal[
    "InsightHeader",
    "NarrativeBuilder",
    "EvidenceCardGrid",
    "RankingBarChart",
    "TrendChart",
    "MismatchMatrix",
    "EquityGapPanel",
    "OutlierExplorer",
    "MetricComparisonTable",
    "DataQualityPanel",
    "SourceTraceDrawer",
    "FollowUpPromptRail",
]

Intent = Literal["trend", "ranking", "mismatch", "equity", "outlier", "quality", "clarify"]

CaveatSeverity = Literal["info", "warning", "error"]


class MetricRef(TypedDict):
    """A resolved metric, carried alongside its catalog label for display."""

    metric_id: str
    metric_name: str
    unit: str
    catalog_group: str | None


class ProviderRef(TypedDict):
    provider_id: str
    provider_name: str


class DataPictureBlock(TypedDict):
    """One declarative UI block. ``props`` is shaped per ``type``.

    The frontend's ``DataPictureRenderer`` maps ``type`` to exactly one
    component via an exhaustive switch, so every value here must be a
    member of ``BlockType``.
    """

    type: BlockType
    title: str
    props: dict[str, object]


class SourceTraceItem(TypedDict):
    source_file_id: str
    source_name: str
    source_url: str | None
    dataset_name: str | None
    license: str | None
    publication_date: str | None
    reporting_year: int | None


class Caveat(TypedDict):
    severity: CaveatSeverity
    message: str
    check_name: str | None


class Plan(TypedDict):
    """The planner's structured interpretation of a free-text question."""

    intent: Intent
    metrics: list[MetricRef]
    providers: list[ProviderRef]
    year: int | None
    scope: str | None
    confidence: float
    suggestions: list[str]


class ExampleQuestion(TypedDict):
    id: str
    label: str
    question: str
    intent: Intent


class DataPicture(TypedDict):
    id: str
    question: str
    intent: Intent
    generated_at: str
    headline: dict[str, object]
    blocks: list[DataPictureBlock]
    caveats: list[Caveat]
    sources: list[SourceTraceItem]
    follow_ups: list[str]
    clarification: dict[str, object] | None

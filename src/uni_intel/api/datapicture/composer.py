"""Turns a `Plan` into a declarative `DataPicture` by calling `queries.py`.

Every claim in the resulting picture must be traceable: each builder below
collects the `source_file_id`s and `data_quality_checks` behind the metric(s)
it used and attaches them as `sources` / `caveats` on the returned picture.
"""

from __future__ import annotations

import statistics
import uuid
from datetime import UTC, datetime

from uni_intel.api.datapicture import queries
from uni_intel.api.datapicture.examples import EXAMPLE_QUESTIONS
from uni_intel.api.datapicture.planner import Planner, RuleBasedPlanner
from uni_intel.api.datapicture.schema import (
    Caveat,
    DataPicture,
    DataPictureBlock,
    MetricRef,
    Plan,
)

MAX_TREND_PROVIDERS = 5
MAX_MISMATCH_ROWS = 8
MAX_OUTLIER_ROWS = 6

_DEFAULT_MISMATCH_PARTNER = {
    "finance_total_revenues_from_continuing_operations_including_deferred_superannuation": (
        "qilt_overall_educational_experience_positive_rating"
    ),
    "qilt_overall_educational_experience_positive_rating": (
        "finance_total_revenues_from_continuing_operations_including_deferred_superannuation"
    ),
}


def compose(question: str, *, planner: Planner | None = None, year: int | None = None) -> DataPicture:
    planner = planner or RuleBasedPlanner()
    metric_catalog = queries.get_metric_catalog(include_missing=True)
    providers = queries.get_providers()
    universities = [row for row in providers if row.get("provider_type") == "university"]
    default_year = year or queries.get_latest_year()

    plan = planner.plan(
        question,
        metric_catalog=metric_catalog,
        providers=universities,
        default_year=default_year,
    )

    if plan["intent"] == "equity":
        return _build_equity(question, plan, metric_catalog)
    if plan["intent"] == "quality":
        return _build_quality(question, plan)
    if not plan["metrics"]:
        return _clarification_picture(question, plan)

    university_ids = {str(row["provider_id"]) for row in universities}
    if plan["intent"] == "trend":
        return _build_trend(question, plan, university_ids)
    if plan["intent"] == "mismatch":
        return _build_mismatch(question, plan, metric_catalog)
    if plan["intent"] == "outlier":
        return _build_outlier(question, plan)
    return _build_ranking(question, plan)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _new_id() -> str:
    return uuid.uuid4().hex


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _format_value(value: float | None, unit: str) -> str:
    """Prose-friendly number formatting. Mirrors apps/web/lib/format.ts.

    Charts and cards send raw numbers to the frontend, which formats them
    with that same TS module for pixel-consistent display. Narrative prose
    is generated server-side, so this small, intentional duplication keeps
    sentences readable without round-tripping through the browser.
    """
    if value is None:
        return "no data"
    if unit == "percent":
        return f"{value:.1f}%"
    if unit.startswith("AUD"):
        amount = value * 1000 if unit == "AUD thousands" else value
        return _format_compact_currency(amount)
    return f"{value:,.1f}"


def _format_compact_currency(amount: float) -> str:
    sign = "-" if amount < 0 else ""
    absolute = abs(amount)
    for threshold, suffix in ((1e12, "t"), (1e9, "b"), (1e6, "m"), (1e3, "k")):
        if absolute >= threshold:
            scaled = absolute / threshold
            digits = 0 if scaled >= 100 else 1
            return f"{sign}${scaled:.{digits}f}{suffix}"
    return f"{sign}${absolute:,.0f}"


def _caveats_from_quality(checks: list[dict[str, object]]) -> list[Caveat]:
    caveats: list[Caveat] = []
    seen: set[tuple[str, str]] = set()
    for check in checks:
        status = str(check.get("status"))
        if status == "pass":
            continue
        message = str(check.get("details") or check.get("check_name"))
        check_name = str(check.get("check_name"))
        key = (check_name, message)
        if key in seen:
            continue
        seen.add(key)
        caveats.append(
            {
                "severity": "warning" if status == "warn" else "error",
                "message": message,
                "check_name": check_name,
            }
        )
    return caveats


def _sources_block_and_list(metric_ids: list[str], year: int | None) -> tuple[DataPictureBlock, list[dict[str, object]]]:
    trace: list[dict[str, object]] = []
    seen: set[str] = set()
    for metric_id in metric_ids:
        for item in queries.get_source_trace_for_metric(metric_id, year=year):
            key = str(item["source_file_id"])
            if key in seen:
                continue
            seen.add(key)
            trace.append(item)
    block: DataPictureBlock = {
        "type": "SourceTraceDrawer",
        "title": "Where these numbers come from",
        "props": {"sources": trace},
    }
    return block, trace


def _quality_block_and_caveats(metric_ids: list[str], year: int | None) -> tuple[DataPictureBlock, list[Caveat]]:
    checks: list[dict[str, object]] = []
    seen: set[str] = set()
    for metric_id in metric_ids:
        for check in queries.get_quality_for_metric(metric_id, year=year):
            key = f"{check.get('check_name')}:{check.get('created_at')}"
            if key in seen:
                continue
            seen.add(key)
            checks.append(check)
    block: DataPictureBlock = {
        "type": "DataQualityPanel",
        "title": "Data quality checks behind this picture",
        "props": {"checks": checks},
    }
    return block, _caveats_from_quality(checks)


def _follow_up_block(prompts: list[str]) -> DataPictureBlock:
    return {
        "type": "FollowUpPromptRail",
        "title": "Keep exploring",
        "props": {"prompts": prompts},
    }


def _narrative_block(paragraphs: list[str]) -> DataPictureBlock:
    return {"type": "NarrativeBuilder", "title": "", "props": {"paragraphs": paragraphs}}


def _insight_header(
    title: str,
    subtitle: str,
    *,
    stat_label: str,
    stat_value: float | None,
    stat_unit: str,
    delta_label: str | None = None,
    delta_value: float | None = None,
) -> dict[str, object]:
    return {
        "title": title,
        "subtitle": subtitle,
        "stat_label": stat_label,
        "stat_value": stat_value,
        "stat_unit": stat_unit,
        "delta_label": delta_label,
        "delta_value": delta_value,
    }


def _ranked_rows(rows: list[dict[str, object]], *, order: str = "desc") -> list[dict[str, object]]:
    valid = [row for row in rows if row.get("value") is not None]
    valid.sort(key=lambda row: float(row["value"]), reverse=(order == "desc"))
    return valid


def _zscores_by_provider(rows: list[dict[str, object]]) -> dict[str, float]:
    values = [float(row["value"]) for row in rows if row.get("value") is not None]
    if len(values) < 3:
        return {}
    mean = statistics.fmean(values)
    stdev = statistics.pstdev(values)
    if stdev == 0:
        return {}
    return {
        str(row["provider_id"]): (float(row["value"]) - mean) / stdev
        for row in rows
        if row.get("value") is not None
    }


# ---------------------------------------------------------------------------
# Trend
# ---------------------------------------------------------------------------


def _build_trend(question: str, plan: Plan, university_ids: set[str]) -> DataPicture:
    metric = plan["metrics"][0]
    metric_id = metric["metric_id"]
    providers = plan["providers"][:MAX_TREND_PROVIDERS]

    if providers:
        rows: list[dict[str, object]] = []
        for provider in providers:
            rows.extend(queries.get_trends(metric_id, provider_id=provider["provider_id"]))
        subject_label = " and ".join(provider["provider_name"] for provider in providers)
    else:
        all_rows = queries.get_trends(metric_id)
        rows = _national_median_series(all_rows, metric, university_ids)
        subject_label = "the university sector"

    ordered = sorted(rows, key=lambda row: int(row["reporting_year"]))
    latest = ordered[-1] if ordered else None
    earliest = ordered[0] if ordered else None

    delta_pct = None
    if latest and earliest and earliest.get("value"):
        delta_pct = ((float(latest["value"]) - float(earliest["value"])) / abs(float(earliest["value"]))) * 100

    headline_stat = float(latest["value"]) if latest and latest.get("value") is not None else None
    headline = _insight_header(
        f"How {subject_label}'s {metric['metric_name'].lower()} has moved",
        f"{metric['metric_name']} from {earliest['reporting_year'] if earliest else '—'} "
        f"to {latest['reporting_year'] if latest else '—'}.",
        stat_label=f"{metric['metric_name']} ({latest['reporting_year'] if latest else '—'})",
        stat_value=headline_stat,
        stat_unit=metric["unit"],
        delta_label=f"Since {earliest['reporting_year']}" if earliest else None,
        delta_value=delta_pct,
    )

    narrative = _trend_narrative(subject_label, metric, earliest, latest, delta_pct)
    cards = _trend_evidence_cards(ordered, metric)

    blocks: list[DataPictureBlock] = [
        {"type": "InsightHeader", "title": "", "props": headline},
        _narrative_block(narrative),
        {
            "type": "TrendChart",
            "title": f"{metric['metric_name']} over time",
            "props": {"rows": ordered, "variant": "multi" if len(providers) > 1 else "single"},
        },
        {"type": "EvidenceCardGrid", "title": "Key moments", "props": {"cards": cards}},
    ]

    sources_block, sources = _sources_block_and_list([metric_id], None)
    quality_block, caveats = _quality_block_and_caveats([metric_id], None)
    blocks.append(quality_block)
    blocks.append(sources_block)

    follow_ups = [
        f"Which universities lead in {metric['metric_name'].lower()} today?",
        f"How does {subject_label} compare to its peers on {metric['metric_name'].lower()}?",
    ]
    blocks.append(_follow_up_block(follow_ups))

    return {
        "id": _new_id(),
        "question": question,
        "intent": "trend",
        "generated_at": _now_iso(),
        "headline": headline,
        "blocks": blocks,
        "caveats": caveats,
        "sources": sources,
        "follow_ups": follow_ups,
        "clarification": None,
    }


def _national_median_series(
    rows: list[dict[str, object]],
    metric: MetricRef,
    university_ids: set[str],
) -> list[dict[str, object]]:
    by_year: dict[int, list[float]] = {}
    for row in rows:
        if str(row.get("provider_id")) not in university_ids or row.get("value") is None:
            continue
        by_year.setdefault(int(row["reporting_year"]), []).append(float(row["value"]))
    return [
        {
            "reporting_year": year,
            "provider_id": "national_median",
            "provider_name": "National median (universities)",
            "metric_id": metric["metric_id"],
            "metric_name": metric["metric_name"],
            "dimension_scope": "Derived",
            "value": statistics.median(values),
            "unit": metric["unit"],
        }
        for year, values in sorted(by_year.items())
        if values
    ]


def _trend_narrative(
    subject_label: str,
    metric: MetricRef,
    earliest: dict[str, object] | None,
    latest: dict[str, object] | None,
    delta_pct: float | None,
) -> list[str]:
    if not earliest or not latest:
        return [f"No time series is available yet for {metric['metric_name'].lower()}."]
    earliest_value = _format_value(float(earliest["value"]) if earliest.get("value") is not None else None, metric["unit"])
    latest_value = _format_value(float(latest["value"]) if latest.get("value") is not None else None, metric["unit"])
    direction = "grown" if (delta_pct or 0) >= 0 else "fallen"
    delta_text = f"{abs(delta_pct):.0f}%" if delta_pct is not None else "an unknown amount"
    return [
        (
            f"{subject_label}'s {metric['metric_name'].lower()} has {direction} from {earliest_value} "
            f"in {earliest['reporting_year']} to {latest_value} in {latest['reporting_year']}, "
            f"a change of {delta_text} over that period."
        )
    ]


def _trend_evidence_cards(ordered: list[dict[str, object]], metric: MetricRef) -> list[dict[str, object]]:
    if not ordered:
        return []
    valued = [row for row in ordered if row.get("value") is not None]
    if not valued:
        return []
    peak = max(valued, key=lambda row: float(row["value"]))
    cards = [
        {"label": f"First recorded ({ordered[0]['reporting_year']})", "value": ordered[0].get("value"), "unit": metric["unit"]},
        {"label": f"Latest ({ordered[-1]['reporting_year']})", "value": ordered[-1].get("value"), "unit": metric["unit"]},
    ]
    if peak["reporting_year"] not in (ordered[0]["reporting_year"], ordered[-1]["reporting_year"]):
        cards.append({"label": f"Peak ({peak['reporting_year']})", "value": peak.get("value"), "unit": metric["unit"]})
    return cards


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


def _build_ranking(question: str, plan: Plan) -> DataPicture:
    metric = plan["metrics"][0]
    metric_id = metric["metric_id"]
    year = plan["year"]
    rows = queries.get_rankings(metric_id, year=year, limit=10, order="desc")
    all_rows = queries.get_rankings(metric_id, year=year, limit=100, order="desc")

    leader = rows[0] if rows else None
    headline = _insight_header(
        f"Who leads in {metric['metric_name'].lower()}",
        f"Top-ranked Australian universities on {metric['metric_name'].lower()} in "
        f"{leader['reporting_year'] if leader else year or 'the latest year'}.",
        stat_label=metric["metric_name"],
        stat_value=float(leader["value"]) if leader and leader.get("value") is not None else None,
        stat_unit=metric["unit"],
        delta_label=leader["provider_name"] if leader else None,
        delta_value=None,
    )

    narrative = [_ranking_narrative(leader, metric, len(all_rows))]
    outliers = _outlier_rows(all_rows)

    blocks: list[DataPictureBlock] = [
        {"type": "InsightHeader", "title": "", "props": headline},
        _narrative_block(narrative),
        {"type": "RankingBarChart", "title": f"Top 10 by {metric['metric_name']}", "props": {"rows": rows}},
        {"type": "MetricComparisonTable", "title": "Full ranking detail", "props": {"rows": rows}},
        {"type": "OutlierExplorer", "title": "Statistical outliers", "props": {"rows": outliers}},
    ]

    sources_block, sources = _sources_block_and_list([metric_id], year)
    quality_block, caveats = _quality_block_and_caveats([metric_id], year)
    blocks.append(quality_block)
    blocks.append(sources_block)

    follow_ups = [
        f"How has {leader['provider_name']}'s {metric['metric_name'].lower()} changed over time?" if leader else question,
        f"Which universities have high {metric['metric_name'].lower()} but a low student experience rating?",
    ]
    blocks.append(_follow_up_block(follow_ups))

    return {
        "id": _new_id(),
        "question": question,
        "intent": "ranking",
        "generated_at": _now_iso(),
        "headline": headline,
        "blocks": blocks,
        "caveats": caveats,
        "sources": sources,
        "follow_ups": follow_ups,
        "clarification": None,
    }


def _ranking_narrative(leader: dict[str, object] | None, metric: MetricRef, total: int) -> str:
    if not leader:
        return f"No ranking data is available yet for {metric['metric_name'].lower()}."
    value = _format_value(float(leader["value"]) if leader.get("value") is not None else None, metric["unit"])
    return (
        f"{leader['provider_name']} leads Australian universities on {metric['metric_name'].lower()} "
        f"with {value}, ahead of {total - 1} other reporting universities."
    )


def _outlier_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    zscores = _zscores_by_provider(rows)
    flagged = [
        {**row, "zscore": zscores[str(row["provider_id"])]}
        for row in rows
        if str(row["provider_id"]) in zscores and abs(zscores[str(row["provider_id"])]) >= 1.5
    ]
    flagged.sort(key=lambda row: abs(float(row["zscore"])), reverse=True)
    return flagged[:MAX_OUTLIER_ROWS]


# ---------------------------------------------------------------------------
# Outlier (metric-focused, no ranking table)
# ---------------------------------------------------------------------------


def _build_outlier(question: str, plan: Plan) -> DataPicture:
    metric = plan["metrics"][0]
    metric_id = metric["metric_id"]
    year = plan["year"]
    all_rows = queries.get_rankings(metric_id, year=year, limit=100, order="desc")
    outliers = _outlier_rows(all_rows)

    top_outlier = outliers[0] if outliers else None
    headline = _insight_header(
        f"Outliers in {metric['metric_name'].lower()}",
        "Universities whose value sits more than 1.5 standard deviations from the sector mean.",
        stat_label="Outliers found",
        stat_value=float(len(outliers)),
        stat_unit="count",
    )
    if top_outlier:
        direction = "above" if float(top_outlier["zscore"]) > 0 else "below"
        narrative = [
            f"{top_outlier['provider_name']} stands out furthest from the sector mean on "
            f"{metric['metric_name'].lower()}, sitting {direction} the average by "
            f"{abs(float(top_outlier['zscore'])):.1f} standard deviations."
        ]
    else:
        narrative = [f"No statistically unusual values were found for {metric['metric_name'].lower()}."]

    blocks: list[DataPictureBlock] = [
        {"type": "InsightHeader", "title": "", "props": headline},
        _narrative_block(narrative),
        {"type": "OutlierExplorer", "title": "Flagged outliers", "props": {"rows": outliers}},
        {"type": "RankingBarChart", "title": "Sector context", "props": {"rows": all_rows[:10]}},
    ]

    sources_block, sources = _sources_block_and_list([metric_id], year)
    quality_block, caveats = _quality_block_and_caveats([metric_id], year)
    blocks.append(quality_block)
    blocks.append(sources_block)
    follow_ups = [f"Which universities lead in {metric['metric_name'].lower()}?"]
    blocks.append(_follow_up_block(follow_ups))

    return {
        "id": _new_id(),
        "question": question,
        "intent": "outlier",
        "generated_at": _now_iso(),
        "headline": headline,
        "blocks": blocks,
        "caveats": caveats,
        "sources": sources,
        "follow_ups": follow_ups,
        "clarification": None,
    }


# ---------------------------------------------------------------------------
# Mismatch
# ---------------------------------------------------------------------------


def _build_mismatch(question: str, plan: Plan, metric_catalog: list[dict[str, object]]) -> DataPicture:
    metrics = list(plan["metrics"])
    if len(metrics) < 2:
        partner_id = _DEFAULT_MISMATCH_PARTNER.get(metrics[0]["metric_id"]) if metrics else None
        partner = next((row for row in metric_catalog if row.get("metric_id") == partner_id), None)
        if metrics and partner:
            metrics.append(
                {
                    "metric_id": str(partner["metric_id"]),
                    "metric_name": str(partner["metric_name"]),
                    "unit": str(partner.get("unit") or ""),
                    "catalog_group": partner.get("catalog_group"),
                }
            )
        else:
            fallback_plan: Plan = {**plan, "intent": "ranking"}
            return _build_ranking(question, fallback_plan)

    metric_a, metric_b = metrics[0], metrics[1]
    year = plan["year"]
    rows_a = _ranked_rows(queries.get_rankings(metric_a["metric_id"], year=year, limit=100))
    rows_b = _ranked_rows(queries.get_rankings(metric_b["metric_id"], year=year, limit=100))
    rank_a = {str(row["provider_id"]): index + 1 for index, row in enumerate(rows_a)}
    rank_b = {str(row["provider_id"]): index + 1 for index, row in enumerate(rows_b)}
    value_a = {str(row["provider_id"]): row["value"] for row in rows_a}
    value_b = {str(row["provider_id"]): row["value"] for row in rows_b}
    names = {str(row["provider_id"]): row["provider_name"] for row in rows_a + rows_b}

    common_ids = set(rank_a) & set(rank_b)
    mismatch_rows = [
        {
            "provider_id": provider_id,
            "provider_name": names[provider_id],
            "rank_a": rank_a[provider_id],
            "value_a": value_a[provider_id],
            "rank_b": rank_b[provider_id],
            "value_b": value_b[provider_id],
            "rank_delta": rank_a[provider_id] - rank_b[provider_id],
        }
        for provider_id in common_ids
    ]
    mismatch_rows.sort(key=lambda row: abs(row["rank_delta"]), reverse=True)
    top_rows = mismatch_rows[:MAX_MISMATCH_ROWS]

    biggest = top_rows[0] if top_rows else None
    headline = _insight_header(
        f"Where {metric_a['metric_name'].lower()} and {metric_b['metric_name'].lower()} disagree",
        f"Universities whose rank on {metric_a['metric_name'].lower()} diverges most from their rank on "
        f"{metric_b['metric_name'].lower()}.",
        stat_label="Biggest divergence",
        stat_value=float(abs(biggest["rank_delta"])) if biggest else None,
        stat_unit="places",
        delta_label=biggest["provider_name"] if biggest else None,
    )

    narrative = [_mismatch_narrative(biggest, metric_a, metric_b)]

    blocks: list[DataPictureBlock] = [
        {"type": "InsightHeader", "title": "", "props": headline},
        _narrative_block(narrative),
        {
            "type": "MismatchMatrix",
            "title": f"{metric_a['metric_name']} vs {metric_b['metric_name']}",
            "props": {"metric_a": metric_a, "metric_b": metric_b, "rows": top_rows},
        },
        {
            "type": "EvidenceCardGrid",
            "title": "Biggest mismatches",
            "props": {
                "cards": [
                    {
                        "label": row["provider_name"],
                        "value": row["rank_delta"],
                        "unit": "places",
                        "caption": f"#{row['rank_a']} on {metric_a['metric_name']}, #{row['rank_b']} on {metric_b['metric_name']}",
                    }
                    for row in top_rows[:3]
                ]
            },
        },
    ]

    sources_block, sources = _sources_block_and_list([metric_a["metric_id"], metric_b["metric_id"]], year)
    quality_block, caveats = _quality_block_and_caveats([metric_a["metric_id"], metric_b["metric_id"]], year)
    blocks.append(quality_block)
    blocks.append(sources_block)
    follow_ups = [
        f"Show the full ranking for {metric_a['metric_name'].lower()}.",
        f"Show the full ranking for {metric_b['metric_name'].lower()}.",
    ]
    blocks.append(_follow_up_block(follow_ups))

    return {
        "id": _new_id(),
        "question": question,
        "intent": "mismatch",
        "generated_at": _now_iso(),
        "headline": headline,
        "blocks": blocks,
        "caveats": caveats,
        "sources": sources,
        "follow_ups": follow_ups,
        "clarification": None,
    }


def _mismatch_narrative(biggest: dict[str, object] | None, metric_a: MetricRef, metric_b: MetricRef) -> str:
    if not biggest:
        return f"No universities have comparable data on both {metric_a['metric_name'].lower()} and {metric_b['metric_name'].lower()} yet."
    higher_metric = metric_a if biggest["rank_delta"] < 0 else metric_b
    lower_metric = metric_b if biggest["rank_delta"] < 0 else metric_a
    return (
        f"{biggest['provider_name']} shows the biggest mismatch: it ranks much higher on "
        f"{higher_metric['metric_name'].lower()} than on {lower_metric['metric_name'].lower()}, "
        f"a gap of {abs(biggest['rank_delta'])} places."
    )


# ---------------------------------------------------------------------------
# Equity (graceful "not available yet")
# ---------------------------------------------------------------------------


def _build_equity(question: str, plan: Plan, metric_catalog: list[dict[str, object]]) -> DataPicture:
    equity_items = [row for row in metric_catalog if row.get("catalog_group") == "Equity"]
    headline = _insight_header(
        "Equity breakdowns are not in the warehouse yet",
        "This prototype has not ingested a demographic equity dataset (low-SES, First Nations, regional/remote).",
        stat_label="Equity metrics tracked in the backlog",
        stat_value=float(len(equity_items)),
        stat_unit="count",
    )
    narrative = [
        (
            "There is no ingested source yet for demographic equity performance "
            "(low-SES, First Nations, regional/remote, CALD, disability shares of commencing students). "
            "These are tracked as backlog items in the metric catalogue rather than shown with placeholder numbers."
        )
    ]
    blocks: list[DataPictureBlock] = [
        {"type": "InsightHeader", "title": "", "props": headline},
        _narrative_block(narrative),
        {
            "type": "EquityGapPanel",
            "title": "Equity metric backlog",
            "props": {
                "items": [
                    {"label": row.get("metric_name"), "note": row.get("source_note")} for row in equity_items
                ]
            },
        },
    ]
    caveats: list[Caveat] = [
        {"severity": "info", "message": str(row.get("source_note")), "check_name": None} for row in equity_items
    ]
    follow_ups = [
        "Which universities lead in research income in 2024?",
        "How has student experience changed over time?",
    ]
    blocks.append(_follow_up_block(follow_ups))

    return {
        "id": _new_id(),
        "question": question,
        "intent": "equity",
        "generated_at": _now_iso(),
        "headline": headline,
        "blocks": blocks,
        "caveats": caveats,
        "sources": [],
        "follow_ups": follow_ups,
        "clarification": None,
    }


# ---------------------------------------------------------------------------
# Quality
# ---------------------------------------------------------------------------


def _build_quality(question: str, plan: Plan) -> DataPicture:
    metric_ids = [metric["metric_id"] for metric in plan["metrics"]]
    if metric_ids:
        checks: list[dict[str, object]] = []
        for metric_id in metric_ids:
            checks.extend(queries.get_quality_for_metric(metric_id, limit=50))
        subject = ", ".join(metric["metric_name"] for metric in plan["metrics"])
    else:
        checks = queries.get_quality(limit=50)
        subject = "the whole warehouse"

    passed = sum(1 for check in checks if check.get("status") == "pass")
    warned = sum(1 for check in checks if check.get("status") == "warn")
    failed = sum(1 for check in checks if check.get("status") == "fail")

    headline = _insight_header(
        f"Data quality for {subject}",
        f"{passed} checks passed, {warned} warned, {failed} failed.",
        stat_label="Checks passed",
        stat_value=float(passed),
        stat_unit="count",
    )
    narrative = [
        f"Of {len(checks)} recorded data-quality checks touching {subject}, {passed} passed, "
        f"{warned} produced a warning, and {failed} failed outright."
    ]
    blocks: list[DataPictureBlock] = [
        {"type": "InsightHeader", "title": "", "props": headline},
        _narrative_block(narrative),
        {"type": "DataQualityPanel", "title": "All checks", "props": {"checks": checks}},
    ]
    sources: list[dict[str, object]] = []
    if metric_ids:
        sources_block, sources = _sources_block_and_list(metric_ids, None)
        blocks.append(sources_block)
    follow_ups = ["Which universities lead in research income in 2024?"]
    blocks.append(_follow_up_block(follow_ups))

    return {
        "id": _new_id(),
        "question": question,
        "intent": "quality",
        "generated_at": _now_iso(),
        "headline": headline,
        "blocks": blocks,
        "caveats": _caveats_from_quality(checks),
        "sources": sources,
        "follow_ups": follow_ups,
        "clarification": None,
    }


# ---------------------------------------------------------------------------
# Clarification fallback
# ---------------------------------------------------------------------------


def _clarification_picture(question: str, plan: Plan) -> DataPicture:
    example_questions = [example["question"] for example in EXAMPLE_QUESTIONS]
    suggestion_text = (
        "I couldn't confidently match that to a metric this prototype tracks. "
        + ("Related backlog items: " + "; ".join(plan["suggestions"]) + "." if plan["suggestions"] else "")
    )
    headline = _insight_header(
        "I need a bit more detail",
        suggestion_text,
        stat_label="Confidence",
        stat_value=plan["confidence"],
        stat_unit="score",
    )
    blocks: list[DataPictureBlock] = [
        {"type": "InsightHeader", "title": "", "props": headline},
        _narrative_block([suggestion_text, "Try one of these instead:"]),
        _follow_up_block(example_questions),
    ]
    return {
        "id": _new_id(),
        "question": question,
        "intent": "clarify",
        "generated_at": _now_iso(),
        "headline": headline,
        "blocks": blocks,
        "caveats": [],
        "sources": [],
        "follow_ups": example_questions,
        "clarification": {"suggestions": plan["suggestions"], "confidence": plan["confidence"]},
    }

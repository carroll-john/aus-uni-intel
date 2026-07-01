from uni_intel.api.datapicture.planner import RuleBasedPlanner

REVENUE_METRIC = {
    "metric_id": "finance_total_revenues_from_continuing_operations_including_deferred_superannuation",
    "metric_name": "Total revenue (continuing operations) $",
    "catalog_group": "Finance and funding",
    "unit": "AUD thousands",
    "selectable": True,
    "source_note": "Department provider finance tables.",
}
QILT_METRIC = {
    "metric_id": "qilt_overall_educational_experience_positive_rating",
    "metric_name": "Overall educational experience positive rating",
    "catalog_group": "Student experience",
    "unit": "percent",
    "selectable": True,
    "source_note": "QILT SES provider-level tables.",
}
HERDC_METRIC = {
    "metric_id": "herdc_research_income_total",
    "metric_name": "HERDC research income (Cat 1-4) $",
    "catalog_group": "Research",
    "unit": "AUD",
    "selectable": True,
    "source_note": "HERDC research income time series.",
}
LOW_SES_METRIC = {
    "metric_id": None,
    "metric_name": "Low-SES share of domestic commencers %",
    "catalog_group": "Equity",
    "unit": "",
    "selectable": False,
    "source_note": "Requires equity performance data parsing.",
}
CATALOG = [REVENUE_METRIC, QILT_METRIC, HERDC_METRIC, LOW_SES_METRIC]
PROVIDERS = [
    {"provider_id": "monash_university", "provider_name": "Monash University", "provider_type": "university"},
    {"provider_id": "university_of_sydney", "provider_name": "The University of Sydney", "provider_type": "university"},
    {
        "provider_id": "university_of_new_south_wales",
        "provider_name": "The University of New South Wales",
        "provider_type": "university",
    },
]


def test_trend_question_resolves_metric_provider_and_intent() -> None:
    plan = RuleBasedPlanner().plan(
        "How has Monash University's total revenue grown since 2018?",
        metric_catalog=CATALOG,
        providers=PROVIDERS,
        default_year=2024,
    )

    assert plan["intent"] == "trend"
    assert plan["metrics"][0]["metric_id"] == REVENUE_METRIC["metric_id"]
    assert plan["providers"][0]["provider_id"] == "monash_university"
    assert plan["year"] == 2018


def test_ranking_question_resolves_herdc_metric() -> None:
    plan = RuleBasedPlanner().plan(
        "Which universities lead in research income in 2024?",
        metric_catalog=CATALOG,
        providers=PROVIDERS,
        default_year=2023,
    )

    assert plan["intent"] == "ranking"
    assert plan["metrics"][0]["metric_id"] == HERDC_METRIC["metric_id"]
    assert plan["year"] == 2024


def test_mismatch_question_resolves_two_distinct_metrics() -> None:
    plan = RuleBasedPlanner().plan(
        "Which universities have high total revenue but a low overall student experience rating?",
        metric_catalog=CATALOG,
        providers=PROVIDERS,
        default_year=2024,
    )

    assert plan["intent"] == "mismatch"
    resolved_ids = {metric["metric_id"] for metric in plan["metrics"]}
    assert resolved_ids == {REVENUE_METRIC["metric_id"], QILT_METRIC["metric_id"]}


def test_unsw_abbreviation_resolves_to_provider() -> None:
    plan = RuleBasedPlanner().plan(
        "How has UNSW's research income changed?",
        metric_catalog=CATALOG,
        providers=PROVIDERS,
        default_year=2024,
    )

    assert plan["providers"]
    assert plan["providers"][0]["provider_id"] == "university_of_new_south_wales"


def test_equity_question_returns_equity_intent_without_metrics() -> None:
    plan = RuleBasedPlanner().plan(
        "What is the low-SES share of commencing students at these universities?",
        metric_catalog=CATALOG,
        providers=PROVIDERS,
        default_year=2024,
    )

    assert plan["intent"] == "equity"
    assert plan["metrics"] == []


def test_nonsense_question_falls_back_to_clarify() -> None:
    plan = RuleBasedPlanner().plan(
        "asdkfj qwoeiru zzzzz",
        metric_catalog=CATALOG,
        providers=PROVIDERS,
        default_year=2024,
    )

    assert plan["intent"] == "clarify"
    assert plan["metrics"] == []

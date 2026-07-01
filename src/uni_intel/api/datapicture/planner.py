"""Deterministic, offline question planner for the Data Picture Studio.

This is intentionally a rule-based keyword/phrase matcher over the existing
metric catalogue and provider list, not an LLM call: this repo is local-first,
ships with no AI/HTTP-client dependency, and every other data path in the
codebase runs offline against the DuckDB warehouse. ``Planner`` is a
``Protocol`` so a future LLM-backed implementation could be swapped in later
without changing ``composer.py`` or the API contract -- it only needs to
return the same ``Plan`` shape.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Protocol

from uni_intel.api.datapicture.schema import Intent, MetricRef, Plan, ProviderRef

_STOPWORDS = {
    "the",
    "a",
    "an",
    "of",
    "and",
    "for",
    "in",
    "at",
    "on",
    "to",
    "is",
    "are",
    "university",
    "universities",
    "uni",
}

_YEAR_PATTERN = re.compile(r"\b(19|20)\d{2}\b")

# "high X but low Y" (and variants with a filler word, e.g. "but a low") is a
# strong, common phrasing for a mismatch question that a plain keyword list
# handles poorly, since the filler word breaks substring matches like
# "but low".
_MISMATCH_PATTERN = re.compile(r"\bbut\b(\s+\w+){0,2}\s+\b(low|high)\b")

# Ordered by specificity: earlier entries win ties against later, more
# generic intents (e.g. "ranking" is the generic fallback when a metric is
# found but no stronger signal is present).
_INTENT_KEYWORDS: tuple[tuple[Intent, tuple[str, ...]], ...] = (
    (
        "mismatch",
        (
            "vs",
            "versus",
            "compare",
            "comparison",
            "difference between",
            "gap between",
            "mismatch",
            "diverge",
            "but low",
            "but high",
            "punches above",
            "underperform",
            "outperform",
            "high revenue but",
        ),
    ),
    (
        "equity",
        (
            "equity",
            "disadvantage",
            "disadvantaged",
            "low ses",
            "low-ses",
            "first nations",
            "indigenous",
            "regional and remote",
            "regional/remote",
            "under-represented",
            "underrepresented",
        ),
    ),
    (
        "outlier",
        (
            "outlier",
            "outliers",
            "unusual",
            "anomaly",
            "anomalies",
            "surprising",
            "stands out",
            "stand out",
            "odd one out",
        ),
    ),
    (
        "quality",
        (
            "data quality",
            "reliable",
            "reliability",
            "trust",
            "confidence in",
            "how confident",
            "how accurate",
        ),
    ),
    (
        "trend",
        (
            "trend",
            "over time",
            "over the last",
            "since 20",
            "since 19",
            "growth",
            "grown",
            "growing",
            "history",
            "historical",
            "trajectory",
            "year on year",
            "year-on-year",
            "how has",
        ),
    ),
    (
        "ranking",
        (
            "rank",
            "ranking",
            "top ",
            "leading",
            "leader",
            "leaders",
            "best",
            "worst",
            "highest",
            "lowest",
            "largest",
            "smallest",
            "which university",
            "which universities",
        ),
    ),
)

# Common abbreviations that do not otherwise overlap with real words, matched
# on word boundaries only. Full provider names are matched separately by
# token overlap, so this only covers short acronyms that would not survive
# stopword-filtered token matching.
_METRIC_OPTIONAL_INTENTS: frozenset[Intent] = frozenset({"equity", "quality"})

_PROVIDER_ABBREVIATIONS: dict[str, str] = {
    "unsw": "new south wales",
    "anu": "australian national",
    "rmit": "rmit",
    "uts": "technology sydney",
    "qut": "queensland technology",
    "uow": "wollongong",
    "utas": "tasmania",
    "acu": "catholic",
    "vu": "victoria",
    "usq": "southern queensland",
}


class Planner(Protocol):
    """Interface implemented by any question -> Plan strategy."""

    def plan(
        self,
        question: str,
        *,
        metric_catalog: list[dict[str, object]],
        providers: list[dict[str, object]],
        default_year: int | None,
    ) -> Plan: ...


class RuleBasedPlanner:
    """Keyword/phrase-matching planner. No network calls, fully deterministic."""

    def plan(
        self,
        question: str,
        *,
        metric_catalog: list[dict[str, object]],
        providers: list[dict[str, object]],
        default_year: int | None,
    ) -> Plan:
        normalized = _normalize(question)
        metrics, suggestions = _resolve_metrics(normalized, metric_catalog)
        resolved_providers = _resolve_providers(normalized, providers)
        intent = _resolve_intent(normalized, has_metric=bool(metrics))
        year = _resolve_year(normalized) or default_year

        # "equity" and "quality" data pictures are meaningful even with no
        # resolved metric (equity metrics are all backlog items today; a
        # general quality question can summarize the whole warehouse), so
        # only fall back to "clarify" for the other, metric-dependent intents.
        if not metrics and intent not in _METRIC_OPTIONAL_INTENTS:
            return {
                "intent": "clarify",
                "metrics": [],
                "providers": resolved_providers,
                "year": year,
                "scope": None,
                "confidence": 0.0,
                "suggestions": suggestions,
            }

        confidence = min(1.0, 0.4 + 0.2 * len(metrics) + (0.2 if resolved_providers else 0.0))
        return {
            "intent": intent,
            "metrics": metrics,
            "providers": resolved_providers,
            "year": year,
            "scope": None,
            "confidence": confidence,
            "suggestions": suggestions,
        }


def _normalize(question: str) -> str:
    lowered = question.lower().strip()
    return re.sub(r"\s+", " ", lowered)


def _resolve_year(normalized: str) -> int | None:
    match = _YEAR_PATTERN.search(normalized)
    return int(match.group(0)) if match else None


def _resolve_intent(normalized: str, *, has_metric: bool) -> Intent:
    best_intent: Intent | None = None
    best_score = 0
    for intent, keywords in _INTENT_KEYWORDS:
        score = sum(1 for keyword in keywords if keyword in normalized)
        if intent == "mismatch" and _MISMATCH_PATTERN.search(normalized):
            score += 2
        if score > best_score:
            best_score = score
            best_intent = intent
    if best_intent is not None:
        return best_intent
    return "ranking" if has_metric else "clarify"


def _significant_words(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9%]+", text.lower())
    return {word for word in words if word not in _STOPWORDS and len(word) > 1}


def _resolve_metrics(
    normalized: str,
    metric_catalog: list[dict[str, object]],
) -> tuple[list[MetricRef], list[str]]:
    question_words = _significant_words(normalized)
    label_word_sets = [(_significant_words(str(item.get("metric_name") or "")), item) for item in metric_catalog]

    # Weight overlapping words by inverse document frequency across the
    # catalog: distinctive words (e.g. "revenue", "herdc") should decide a
    # match far more than words shared by many labels in the same group
    # (e.g. "rating", "student" across six QILT sub-metrics), otherwise a
    # generic-group match can outscore the metric the user actually named.
    doc_freq: dict[str, int] = {}
    for label_words, _ in label_word_sets:
        for word in label_words:
            doc_freq[word] = doc_freq.get(word, 0) + 1

    scored: list[tuple[float, dict[str, object]]] = []
    for label_words, item in label_word_sets:
        if not label_words:
            continue
        label = str(item.get("metric_name") or "")
        group = str(item.get("catalog_group") or item.get("metric_group") or "")
        overlap_words = label_words & question_words
        weighted_overlap = sum(2.0 / doc_freq[word] for word in overlap_words)
        substring_bonus = 1.5 if label.lower() in normalized else 0.0
        fuzzy_bonus = SequenceMatcher(None, label.lower(), normalized).find_longest_match().size / max(len(label), 1)
        group_bonus = 0.1 if group and group.lower() in normalized else 0.0
        score = weighted_overlap + substring_bonus + fuzzy_bonus + group_bonus
        if score > 0.5:
            scored.append((score, item))

    scored.sort(key=lambda pair: pair[0], reverse=True)

    available = [(score, item) for score, item in scored if item.get("selectable")]
    unavailable = [(score, item) for score, item in scored if not item.get("selectable")]

    if not available:
        suggestions = [
            f"{item['metric_name']} ({item.get('source_note', 'not available yet')})"
            for _, item in unavailable[:3]
        ]
        return [], suggestions

    top_score = available[0][0]
    picked: list[MetricRef] = []
    for score, item in available:
        if len(picked) >= 2:
            break
        # Keep a second metric only when it is a genuinely distinct, strong
        # match (e.g. "revenue vs student experience"), not a near-duplicate
        # of the top pick's score noise.
        if picked and score < top_score * 0.6:
            break
        picked.append(
            {
                "metric_id": str(item["metric_id"]),
                "metric_name": str(item["metric_name"]),
                "unit": str(item.get("unit") or ""),
                "catalog_group": item.get("catalog_group"),  # type: ignore[typeddict-item]
            }
        )
    return picked, []


def _resolve_providers(
    normalized: str,
    providers: list[dict[str, object]],
) -> list[ProviderRef]:
    matches: list[ProviderRef] = []
    for provider in providers:
        name = str(provider.get("provider_name") or "")
        name_words = _significant_words(name)
        if not name_words:
            continue
        if name_words.issubset(_significant_words(normalized)) or _has_abbreviation_match(normalized, name):
            matches.append(
                {
                    "provider_id": str(provider["provider_id"]),
                    "provider_name": name,
                }
            )
    return matches[:5]


def _has_abbreviation_match(normalized: str, provider_name: str) -> bool:
    provider_lower = provider_name.lower()
    for abbreviation, name_fragment in _PROVIDER_ABBREVIATIONS.items():
        if re.search(rf"\b{re.escape(abbreviation)}\b", normalized) and name_fragment in provider_lower:
            return True
    return False

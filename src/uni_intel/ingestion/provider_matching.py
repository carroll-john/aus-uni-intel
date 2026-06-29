from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Iterable

import duckdb

_PUNCTUATION_RE = re.compile(r"[^a-z0-9]+")


def normalize_provider_name(value: str) -> str:
    normalized = value.lower().replace("&", " and ")
    normalized = re.sub(r"\([^)]*\d[^)]*\)", " ", normalized)
    normalized = _PUNCTUATION_RE.sub(" ", normalized)
    normalized = re.sub(r"\bthe\b", " ", normalized)
    return " ".join(normalized.split())


@dataclass(frozen=True)
class ProviderMatch:
    provider_id: str
    matched_name: str
    confidence: float
    method: str


class ProviderResolver:
    def __init__(
        self,
        provider_records: Iterable[dict[str, str]],
        alias_records: Iterable[dict[str, str | float]],
        fuzzy_threshold: float = 0.94,
    ) -> None:
        self.fuzzy_threshold = fuzzy_threshold
        self._lookup: dict[str, ProviderMatch] = {}
        self._candidates: list[tuple[str, ProviderMatch]] = []

        for provider in provider_records:
            self._add_candidate(
                provider["provider_name"],
                provider["provider_id"],
                confidence=1.0,
                method="provider_name",
            )

        for alias in alias_records:
            self._add_candidate(
                str(alias["alias"]),
                str(alias["provider_id"]),
                confidence=float(alias.get("confidence", 1.0)),
                method="alias",
            )

    @classmethod
    def from_connection(cls, conn: duckdb.DuckDBPyConnection) -> "ProviderResolver":
        providers = [
            {"provider_id": row[0], "provider_name": row[1]}
            for row in conn.execute(
                "SELECT provider_id, provider_name FROM providers"
            ).fetchall()
        ]
        aliases = [
            {"alias": row[0], "provider_id": row[1], "confidence": row[2]}
            for row in conn.execute(
                "SELECT alias, provider_id, confidence FROM provider_aliases"
            ).fetchall()
        ]
        return cls(providers, aliases)

    @classmethod
    def from_records(
        cls,
        providers: Iterable[tuple[str, str]],
        aliases: Iterable[tuple[str, str, float]] = (),
        fuzzy_threshold: float = 0.94,
    ) -> "ProviderResolver":
        provider_records = [
            {"provider_id": provider_id, "provider_name": name}
            for provider_id, name in providers
        ]
        alias_records = [
            {"alias": alias, "provider_id": provider_id, "confidence": confidence}
            for alias, provider_id, confidence in aliases
        ]
        return cls(provider_records, alias_records, fuzzy_threshold=fuzzy_threshold)

    def _add_candidate(
        self,
        name: str,
        provider_id: str,
        confidence: float,
        method: str,
    ) -> None:
        normalized = normalize_provider_name(name)
        match = ProviderMatch(provider_id, name, confidence, method)
        self._lookup[normalized] = match
        self._candidates.append((normalized, match))

    def resolve(self, source_name: str) -> ProviderMatch | None:
        normalized = normalize_provider_name(source_name)
        exact = self._lookup.get(normalized)
        if exact:
            return exact

        best_score = 0.0
        best_match: ProviderMatch | None = None
        for candidate_name, candidate_match in self._candidates:
            score = SequenceMatcher(None, normalized, candidate_name).ratio()
            if score > best_score:
                best_score = score
                best_match = candidate_match

        if best_match and best_score >= self.fuzzy_threshold:
            return ProviderMatch(
                best_match.provider_id,
                best_match.matched_name,
                round(best_score, 4),
                "fuzzy",
            )
        return None

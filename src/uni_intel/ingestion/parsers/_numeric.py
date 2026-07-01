"""Shared numeric coercion for dataset parsers."""

from __future__ import annotations

from collections.abc import Callable


def parse_optional_numeric(
    value: object,
    none_sentinels: set[str],
    error: Callable[[object], Exception],
) -> float | None:
    """Coerce a spreadsheet cell into a float.

    Returns ``None`` for empty/suppressed values listed in ``none_sentinels``, and
    raises ``error(value)`` for values that are non-empty but not numeric.
    """
    if value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    text = str(value).strip().replace(",", "")
    if text in none_sentinels:
        return None
    try:
        return float(text)
    except ValueError as exc:
        raise error(value) from exc

"""Pure analytics helpers: no database or HTTP dependencies.

Ranking, median, year-on-year change math, canonical scope selection, and metric
history aliasing. Everything here is unit-testable without a connection.
"""

from __future__ import annotations

from statistics import median

TOTAL_REVENUE_METRIC_ID = "finance_total_revenues_from_continuing_operations_including_deferred_superannuation"
LEGACY_TOTAL_REVENUE_METRIC_ID = "finance_total_revenues_from_continuing_operations"
OVERSEAS_FEE_INCOME_METRIC_ID = "finance_international_students"
LEGACY_OVERSEAS_FEE_INCOME_METRIC_ID = "finance_fee_paying_overseas_students"
METRIC_HISTORY_ALIASES = {
    TOTAL_REVENUE_METRIC_ID: [TOTAL_REVENUE_METRIC_ID, LEGACY_TOTAL_REVENUE_METRIC_ID],
    OVERSEAS_FEE_INCOME_METRIC_ID: [
        OVERSEAS_FEE_INCOME_METRIC_ID,
        LEGACY_OVERSEAS_FEE_INCOME_METRIC_ID,
    ],
}
MAX_COMPARE_PROVIDERS = 10
MAX_COMPARE_METRICS = 10


def safe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def metric_ids_for_query(metric_id: str) -> list[str]:
    return METRIC_HISTORY_ALIASES.get(metric_id, [metric_id])


def metric_filter_sql(metric_ids: list[str]) -> str:
    placeholders = ", ".join("?" for _ in metric_ids)
    return f"f.metric_id IN ({placeholders})"


def normalize_metric_rows(
    rows: list[dict[str, object]],
    requested_metric_id: str,
    canonical_metric_name: str | None,
) -> list[dict[str, object]]:
    """Re-map legacy metric ids/names onto the requested canonical id so that
    renamed metrics present a continuous history."""
    alias_metric_ids = METRIC_HISTORY_ALIASES.get(requested_metric_id)
    if not alias_metric_ids:
        return rows

    for row in rows:
        if row.get("metric_id") not in alias_metric_ids:
            continue
        row["metric_id"] = requested_metric_id
        if canonical_metric_name:
            row["metric_name"] = canonical_metric_name
    return rows


def canonical_scope_qualifier(scope: str | None, partition_columns: list[str]) -> str:
    """Return a ``QUALIFY`` clause that keeps one canonical scope per partition.

    When a caller does not pin a ``scope`` we pick a single ``dimension_scope`` per
    provider/metric/year so dual-sector providers are not double-counted.
    """
    if scope is not None:
        return ""

    partition_sql = ", ".join(partition_columns)
    return f"""
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY {partition_sql}
            ORDER BY
                CASE
                    WHEN f.dimension_scope = 'Total Institution' THEN 0
                    WHEN f.dimension_scope = 'Student' THEN 0
                    WHEN f.dimension_scope = 'HERDC' THEN 0
                    WHEN f.dimension_scope = 'QILT undergraduate' THEN 0
                    WHEN f.dimension_scope = 'Calculated' THEN 0
                    WHEN f.dimension_scope = 'HED' THEN 1
                    WHEN f.dimension_scope LIKE 'QILT %' THEN 1
                    ELSE 2
                END,
                f.dimension_scope
        ) = 1
        """


def rank_for_value(rows: list[dict[str, object]], provider_id: str, order: str = "desc") -> dict[str, object] | None:
    scoped_rows: list[dict[str, object]] = []
    for row in rows:
        value = safe_float(row.get("value"))
        if value is not None:
            scoped_rows.append({**row, "value": value})
    current = next((row for row in scoped_rows if row["provider_id"] == provider_id), None)
    if current is None:
        return None
    current_value = float(current["value"])  # type: ignore[arg-type]
    if order == "asc":
        rank = 1 + sum(1 for row in scoped_rows if float(row["value"]) < current_value)  # type: ignore[arg-type]
    else:
        rank = 1 + sum(1 for row in scoped_rows if float(row["value"]) > current_value)  # type: ignore[arg-type]
    return {"rank": rank, "of": len(scoped_rows), "value": current_value}


def median_for_rows(rows: list[dict[str, object]]) -> float | None:
    values = [value for row in rows if (value := safe_float(row.get("value"))) is not None]
    return float(median(values)) if values else None


def rank_scope(
    rows: list[dict[str, object]],
    provider_id: str,
    year: int,
    *,
    mission_group: str | None = None,
    state: str | None = None,
) -> list[dict[str, object]]:
    scoped = [row for row in rows if int(row["reporting_year"]) == year]  # type: ignore[arg-type]
    if mission_group is not None:
        scoped = [row for row in scoped if row.get("mission_group") == mission_group]
    if state is not None:
        scoped = [row for row in scoped if row.get("state") == state]
    return scoped


def change_payload(current_value: float, previous_row: dict[str, object]) -> dict[str, object] | None:
    previous_value = safe_float(previous_row.get("value"))
    if previous_value is None or previous_value == 0:
        return None
    return {
        "year": int(previous_row["reporting_year"]),  # type: ignore[arg-type]
        "from_value": previous_value,
        "absolute": current_value - previous_value,
        "percent": ((current_value - previous_value) / abs(previous_value)) * 100,
    }

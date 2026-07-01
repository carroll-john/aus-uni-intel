from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query

from uni_intel.api import analytics
from uni_intel.api.deps import get_conn
from uni_intel.api.repositories import metrics as metrics_repo
from uni_intel.api.repositories import providers as repo
from uni_intel.api.schemas import Provider

router = APIRouter()


@router.get("/providers", response_model=list[Provider])
def providers(conn: duckdb.DuckDBPyConnection = Depends(get_conn)) -> list[dict[str, object]]:
    return repo.list_providers(conn)


@router.get("/provider/{provider_id}/profile")
def provider_profile(
    provider_id: str,
    year: int | None = Query(None),
    scope: str | None = Query(None),
    conn: duckdb.DuckDBPyConnection = Depends(get_conn),
) -> dict[str, object]:
    provider = repo.get_provider(conn, provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    facts = repo.provider_facts(conn, provider_id, year, scope)
    return {"provider": provider, "facts": facts}


@router.get("/provider/{provider_id}/metric-insight")
def provider_metric_insight(
    provider_id: str,
    metric_id: str,
    year: int | None = Query(None),
    scope: str | None = Query(None),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    conn: duckdb.DuckDBPyConnection = Depends(get_conn),
) -> dict[str, object]:
    provider = repo.get_provider(conn, provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")

    metric_ids = analytics.metric_ids_for_query(metric_id)
    rows = repo.metric_insight_rows(conn, metric_ids, scope)
    rows = analytics.normalize_metric_rows(rows, metric_id, metrics_repo.canonical_metric_name(conn, metric_id))
    provider_metric_rows = [row for row in rows if row["provider_id"] == provider_id]
    if not provider_metric_rows:
        raise HTTPException(status_code=404, detail="No facts found for provider and metric")

    selected_year = year if year is not None else max(int(row["reporting_year"]) for row in provider_metric_rows)
    current = next((row for row in provider_metric_rows if int(row["reporting_year"]) == selected_year), None)
    if current is None:
        raise HTTPException(status_code=404, detail="No fact found for selected year")

    current_value = analytics.safe_float(current.get("value"))
    if current_value is None:
        raise HTTPException(status_code=500, detail="Invalid metric value")

    national_rows = analytics.rank_scope(rows, provider_id, selected_year)
    mission_group = provider.get("mission_group")
    state = provider.get("state")
    mission_rows = (
        analytics.rank_scope(rows, provider_id, selected_year, mission_group=str(mission_group))
        if mission_group
        else []
    )
    state_rows = analytics.rank_scope(rows, provider_id, selected_year, state=str(state)) if state else []

    ranks = {
        "national": analytics.rank_for_value(national_rows, provider_id, order),
        "mission_group": {
            **(analytics.rank_for_value(mission_rows, provider_id, order) or {}),
            "label": mission_group,
        }
        if mission_group
        else None,
        "state": {
            **(analytics.rank_for_value(state_rows, provider_id, order) or {}),
            "label": state,
        }
        if state
        else None,
    }
    medians = {
        "national": analytics.median_for_rows(national_rows),
        "mission_group": analytics.median_for_rows(mission_rows) if mission_group else None,
        "state": analytics.median_for_rows(state_rows) if state else None,
    }

    by_year = {int(row["reporting_year"]): row for row in provider_metric_rows}
    changes = {
        f"{offset}y": analytics.change_payload(current_value, by_year[selected_year - offset])
        for offset in (1, 3, 5)
        if selected_year - offset in by_year
    }

    movement_reference_year = selected_year - 5 if selected_year - 5 in by_year else min(by_year)
    current_rank = ranks["national"]["rank"] if ranks["national"] else None
    previous_rank_payload = analytics.rank_for_value(
        analytics.rank_scope(rows, provider_id, movement_reference_year), provider_id, order
    )
    rank_move = None
    if current_rank is not None and previous_rank_payload:
        rank_move = {
            "year": movement_reference_year,
            "from_rank": previous_rank_payload["rank"],
            "to_rank": current_rank,
            "places": int(previous_rank_payload["rank"]) - int(current_rank),
        }

    trend = sorted(provider_metric_rows, key=lambda row: int(row["reporting_year"]))
    return {
        "provider": provider,
        "metric": {
            "metric_id": metric_id,
            "metric_name": current["metric_name"],
            "metric_group": current["metric_group"],
            "definition": current["definition"],
            "unit": current["unit"],
            "source_agency": current["source_agency"],
            "source_dataset": current["source_dataset"],
            "source_table": current["source_table"],
            "source_line_item": current["source_line_item"],
            "is_calculated": current["is_calculated"],
            "calculation_method": current["calculation_method"],
        },
        "year": selected_year,
        "scope": current["dimension_scope"],
        "value": current_value,
        "unit": current["unit"],
        "current": current,
        "trend": trend,
        "ranks": ranks,
        "rank_move": rank_move,
        "medians": medians,
        "changes": changes,
        "source": {
            "source_name": current["source_name"],
            "source_url": current["source_url"],
            "license": current["license"],
            "publication_date": current["publication_date"],
        },
    }

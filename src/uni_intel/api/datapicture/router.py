"""Data Picture Studio routes, registered by the API application factory."""

from __future__ import annotations

from fastapi import APIRouter, Query

from uni_intel.api.datapicture.composer import compose
from uni_intel.api.datapicture.examples import EXAMPLE_QUESTIONS

router = APIRouter(prefix="/datapicture", tags=["datapicture"])


@router.get("/examples")
def examples():
    return EXAMPLE_QUESTIONS


@router.get("/compose")
def compose_data_picture(
    q: str = Query(..., min_length=1, max_length=300, description="A free-text strategic question."),
    year: int | None = Query(None),
):
    return compose(q, year=year)

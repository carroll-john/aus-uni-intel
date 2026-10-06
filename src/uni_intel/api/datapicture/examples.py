"""Canned example questions for the Data Picture Studio quick-start chips.

These are just example inputs, not canned outputs: `GET /datapicture/examples`
returns this list so the frontend can render them, and clicking one runs the
exact same planner + composer pipeline as any other typed question, against
live DuckDB data.
"""

from __future__ import annotations

from uni_intel.api.datapicture.schema import ExampleQuestion

EXAMPLE_QUESTIONS: list[ExampleQuestion] = [
    {
        "id": "trend-monash-revenue",
        "label": "Trend",
        "question": "How has Monash University's total revenue grown since 2018?",
        "intent": "trend",
    },
    {
        "id": "ranking-research-income",
        "label": "Ranking",
        "question": "Which universities lead in research income in 2024?",
        "intent": "ranking",
    },
    {
        "id": "mismatch-revenue-vs-experience",
        "label": "Mismatch",
        "question": "Which universities have high total revenue but a low overall student experience rating?",
        "intent": "mismatch",
    },
]

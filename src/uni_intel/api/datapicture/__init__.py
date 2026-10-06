"""Data Picture Studio: prompt-driven composition layer over the existing API.

This package never talks to the database directly with new write paths and
never calls any external network service. It only reads the already-ingested
DuckDB warehouse through the existing FastAPI query functions in
``uni_intel.api.main`` (see ``queries.py``), then assembles a declarative,
typed "data picture" JSON payload that the Next.js frontend renders with a
small fixed component catalogue.
"""

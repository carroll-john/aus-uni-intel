"""Ingestion framework for public higher education datasets.

Two layers, kept strictly separate:

- ``parsers/`` are pure: they turn downloaded file bytes into dataclass rows with
  no network or database access.
- ``ingest_*.py`` runners own I/O: they download sources, register source
  metadata, stage rows, resolve providers, load canonical facts, and write
  quality checks. Shared helpers live in :mod:`uni_intel.ingestion.common`.

See ``AGENTS.md`` ("Adding a dataset") for the end-to-end workflow.
"""

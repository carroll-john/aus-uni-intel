"""ASGI entrypoint for the API.

Kept thin on purpose: the app is assembled in :mod:`uni_intel.api.app`, data
access lives in :mod:`uni_intel.api.repositories`, and pure logic in
:mod:`uni_intel.api.analytics`. A few symbols are re-exported for backwards
compatibility with existing imports and tests.
"""

from __future__ import annotations

from uni_intel.api.analytics import (
    MAX_COMPARE_METRICS,
    MAX_COMPARE_PROVIDERS,
)
from uni_intel.api.analytics import (
    safe_float as _safe_float,
)
from uni_intel.api.app import create_app

app = create_app()

__all__ = ["MAX_COMPARE_METRICS", "MAX_COMPARE_PROVIDERS", "_safe_float", "app"]

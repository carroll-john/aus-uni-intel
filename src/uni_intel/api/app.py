"""FastAPI application factory. Wiring only; behaviour lives in routers."""

from __future__ import annotations

from fastapi import FastAPI

from uni_intel.api.routers import (
    benchmarks,
    compare,
    metrics,
    overview,
    providers,
    rankings,
    sources,
    trends,
)

ROUTERS = (
    overview.router,
    providers.router,
    metrics.router,
    rankings.router,
    benchmarks.router,
    compare.router,
    trends.router,
    sources.router,
)


def create_app() -> FastAPI:
    app = FastAPI(title="Australian University Intelligence API")
    for router in ROUTERS:
        app.include_router(router)
    return app

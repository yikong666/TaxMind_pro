from __future__ import annotations

from fastapi import FastAPI

from taxmind.bootstrap.container import ServiceRegistry
from taxmind.entrypoints.api.candidates import router as candidates_router
from taxmind.entrypoints.api.cases import router as cases_router
from taxmind.entrypoints.api.conversations import router as conversations_router
from taxmind.entrypoints.api.documents import router as documents_router
from taxmind.entrypoints.api.health import router as health_router
from taxmind.entrypoints.api.identity import router as identity_router
from taxmind.entrypoints.api.query_runs import router as query_runs_router
from taxmind.entrypoints.api.sources import router as sources_router
from taxmind.entrypoints.api.uploads import router as uploads_router


def register_routers(app: FastAPI, registry: ServiceRegistry) -> None:
    del registry
    app.include_router(health_router)
    app.include_router(identity_router, prefix="/api/v1")
    app.include_router(cases_router, prefix="/api/v1")
    app.include_router(query_runs_router, prefix="/api/v1")
    app.include_router(conversations_router, prefix="/api/v1")
    app.include_router(documents_router, prefix="/api/v1")
    app.include_router(sources_router, prefix="/api/v1")
    app.include_router(uploads_router, prefix="/api/v1")
    app.include_router(candidates_router, prefix="/api/v1")

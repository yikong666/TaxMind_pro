from __future__ import annotations

from fastapi import FastAPI

from taxmind.bootstrap.container import ServiceRegistry
from taxmind.entrypoints.api.health import router as health_router


def register_routers(app: FastAPI, registry: ServiceRegistry) -> None:
    del registry
    app.include_router(health_router)
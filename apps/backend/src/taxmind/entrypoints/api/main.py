from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from taxmind.bootstrap.container import AppContainer, build_container, wire_services
from taxmind.bootstrap.lifespan import app_lifespan
from taxmind.bootstrap.logging import configure_logging
from taxmind.bootstrap.settings import Settings, get_settings, validate_runtime_settings
from taxmind.entrypoints.api.exception_handlers import register_exception_handlers
from taxmind.entrypoints.api.middleware import register_middleware
from taxmind.entrypoints.api.router_registry import register_routers


def create_app(
    settings: Settings | None = None,
    *,
    container: AppContainer | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    validate_runtime_settings(resolved_settings)
    configure_logging(resolved_settings, service="api")
    resolved_container = container or build_container(resolved_settings)
    registry = wire_services(resolved_container)

    app = FastAPI(
        title=resolved_settings.app_name,
        version="0.1.0",
        default_response_class=ORJSONResponse,
        lifespan=app_lifespan,
    )
    app.state.container = resolved_container
    app.state.services = dict(registry)
    register_middleware(app)
    register_exception_handlers(app)
    register_routers(app, registry)
    return app

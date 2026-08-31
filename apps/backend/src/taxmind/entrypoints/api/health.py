from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, ConfigDict

from taxmind import __version__
from taxmind.bootstrap.container import AppContainer, ProbeResult
from taxmind.shared.contracts.api import ResponseMeta

router = APIRouter(prefix="/health", tags=["health"])


class DependencyStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    detail: str
    required: bool


class HealthData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["live", "ready", "degraded", "not_ready"]
    service: str
    checked_at: datetime
    dependencies: dict[str, DependencyStatus] = {}


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: HealthData
    meta: ResponseMeta


class VersionData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app_version: str
    build_sha: str
    contract_version: str


class VersionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: VersionData
    meta: ResponseMeta


def _meta(request: Request) -> ResponseMeta:
    return ResponseMeta(request_id=request.state.request_id)


def _dependency_payload(
    container: AppContainer, results: dict[str, ProbeResult]
) -> dict[str, DependencyStatus]:
    return {
        name: DependencyStatus(
            status=result.status,
            detail=result.detail,
            required=container.probes[name].required,
        )
        for name, result in results.items()
    }


@router.get("/live", response_model=HealthResponse)
async def liveness(request: Request) -> HealthResponse:
    return HealthResponse(
        data=HealthData(
            status="live",
            service="api",
            checked_at=datetime.now(UTC),
        ),
        meta=_meta(request),
    )


@router.get(
    "/ready",
    response_model=HealthResponse,
    responses={503: {"model": HealthResponse}},
)
async def readiness(request: Request) -> HealthResponse | ORJSONResponse:
    container: AppContainer = request.app.state.container
    results = await container.check_readiness()
    required_failed = any(
        not result.healthy and container.probes[name].required for name, result in results.items()
    )
    optional_failed = any(
        not result.healthy and not container.probes[name].required
        for name, result in results.items()
    )
    status: Literal["ready", "degraded", "not_ready"]
    if required_failed:
        status = "not_ready"
    elif optional_failed:
        status = "degraded"
    else:
        status = "ready"
    envelope = HealthResponse(
        data=HealthData(
            status=status,
            service="api",
            checked_at=datetime.now(UTC),
            dependencies=_dependency_payload(container, results),
        ),
        meta=_meta(request),
    )
    if status == "not_ready":
        return ORJSONResponse(status_code=503, content=envelope.model_dump(mode="json"))
    return envelope


@router.get("/version", response_model=VersionResponse)
async def version(request: Request) -> VersionResponse:
    settings = request.app.state.container.settings
    return VersionResponse(
        data=VersionData(
            app_version=__version__,
            build_sha=settings.build_sha,
            contract_version=settings.contract_version,
        ),
        meta=_meta(request),
    )

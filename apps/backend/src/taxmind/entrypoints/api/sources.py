from __future__ import annotations

from datetime import datetime
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from taxmind.entrypoints.api.dependencies import current_principal
from taxmind.modules.sources.application.service import (
    RegisterSourceSiteCommand,
    SourcesService,
)
from taxmind.modules.sources.domain import IngestionJobRecord, SourceSiteRecord
from taxmind.shared.contracts.api import ResponseMeta
from taxmind.shared.domain.principal import Principal

router = APIRouter(tags=["knowledge-sources"])


class RegisterSourceSiteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=200)
    base_url: HttpUrl
    source_level: str = Field(pattern="^[A-D]$")
    authority_name: str = Field(min_length=2, max_length=200)
    region_code: str = Field(pattern="^\\d{6}$")
    collection_method: str = Field(pattern="^(manual|whitelist_crawl|api|file_import)$")
    whitelist_rules: dict[str, object] = Field(default_factory=dict)
    crawl_interval_minutes: int | None = Field(default=None, ge=60, le=43200)


class SourceSiteData(BaseModel):
    id: str
    name: str
    base_url: str
    domain: str
    source_level: str
    authority_name: str
    region_code: str
    collection_method: str
    whitelist_rules: dict[str, object]
    crawl_interval_minutes: int | None
    status: str
    last_checked_at: datetime | None
    created_by: str
    created_at: datetime
    updated_at: datetime


class SourceSiteResponse(BaseModel):
    data: SourceSiteData
    meta: ResponseMeta


class SourceSiteListResponse(BaseModel):
    data: list[SourceSiteData]
    meta: ResponseMeta


class IngestionJobData(BaseModel):
    id: str
    source_site_id: str
    job_type: str
    trigger_type: str
    source_url: str | None
    status: str
    attempt_count: int
    discovered_count: int
    changed_count: int
    error_code: str | None
    error_detail_safe: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


class IngestionJobResponse(BaseModel):
    data: IngestionJobData
    meta: ResponseMeta


def _service(request: Request) -> SourcesService:
    services = cast(dict[str, object], request.app.state.services)
    service = services.get("sources")
    if not isinstance(service, SourcesService):
        raise RuntimeError("sources service is not configured")
    return service


def _source_data(record: SourceSiteRecord) -> SourceSiteData:
    return SourceSiteData(
        id=record.id,
        name=record.name,
        base_url=record.base_url,
        domain=record.domain,
        source_level=record.source_level,
        authority_name=record.authority_name,
        region_code=record.region_code,
        collection_method=record.collection_method,
        whitelist_rules=record.whitelist_rules,
        crawl_interval_minutes=record.crawl_interval_minutes,
        status=record.status,
        last_checked_at=record.last_checked_at,
        created_by=record.created_by,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _job_data(record: IngestionJobRecord) -> IngestionJobData:
    return IngestionJobData(
        id=record.id,
        source_site_id=record.source_site_id,
        job_type=record.job_type,
        trigger_type=record.trigger_type,
        source_url=record.source_url,
        status=record.status,
        attempt_count=record.attempt_count,
        discovered_count=record.discovered_count,
        changed_count=record.changed_count,
        error_code=record.error_code,
        error_detail_safe=record.error_detail_safe,
        started_at=record.started_at,
        finished_at=record.finished_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _meta(request: Request) -> ResponseMeta:
    return ResponseMeta(request_id=request.state.request_id)


@router.post("/knowledge/sources", response_model=SourceSiteResponse, status_code=201)
async def register_source(
    payload: RegisterSourceSiteRequest,
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
) -> SourceSiteResponse:
    source = await _service(request).register_source(
        RegisterSourceSiteCommand(
            name=payload.name,
            base_url=str(payload.base_url),
            source_level=payload.source_level,
            authority_name=payload.authority_name,
            region_code=payload.region_code,
            collection_method=payload.collection_method,
            whitelist_rules=payload.whitelist_rules,
            crawl_interval_minutes=payload.crawl_interval_minutes,
            request_id=request.state.request_id,
        ),
        principal,
    )
    return SourceSiteResponse(data=_source_data(source), meta=_meta(request))


@router.get("/knowledge/sources", response_model=SourceSiteListResponse)
async def list_sources(
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
) -> SourceSiteListResponse:
    sources = await _service(request).list_sources(principal)
    return SourceSiteListResponse(
        data=[_source_data(source) for source in sources],
        meta=_meta(request),
    )


@router.get("/knowledge/jobs/{job_id}", response_model=IngestionJobResponse)
async def get_ingestion_job(
    job_id: str,
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
) -> IngestionJobResponse:
    job = await _service(request).get_job(job_id, principal)
    return IngestionJobResponse(data=_job_data(job), meta=_meta(request))

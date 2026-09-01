from __future__ import annotations

from datetime import date
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from taxmind.entrypoints.api.dependencies import current_principal
from taxmind.modules.procedures.application.service import ProceduresService
from taxmind.shared.contracts.api import ResponseMeta
from taxmind.shared.domain.principal import Principal

router = APIRouter(tags=["procedures"])


class ProcedureData(BaseModel):
    procedure_version_id: str
    procedure_code: str
    title: str
    region_code: str
    region_match: str
    effective_start: date | None
    effective_end: date | None
    official_url: str
    source_chunk_ids: list[str]
    materials: list[str]
    channels: list[str]


class ProcedureSearchResponse(BaseModel):
    data: list[ProcedureData]
    meta: ResponseMeta


def _service(request: Request) -> ProceduresService:
    service = cast(dict[str, object], request.app.state.services).get("procedures")
    if not isinstance(service, ProceduresService):
        raise RuntimeError("procedures service is not configured")
    return service


@router.get("/procedures/search", response_model=ProcedureSearchResponse)
async def search_procedures(
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
    query: Annotated[str, Query(min_length=1, max_length=200)],
    region_code: Annotated[str, Query(pattern="^\\d{6}$")],
    business_date: date,
) -> ProcedureSearchResponse:
    results = await _service(request).search_published(
        query=query,
        region_code=region_code,
        business_date=business_date,
        principal=principal,
    )
    return ProcedureSearchResponse(
        data=[
            ProcedureData(
                procedure_version_id=item.procedure_version_id,
                procedure_code=item.procedure_code,
                title=item.title,
                region_code=item.region_code,
                region_match="local" if item.region_code == region_code else "national_only",
                effective_start=item.effective_start,
                effective_end=item.effective_end,
                official_url=item.official_url,
                source_chunk_ids=list(item.source_chunk_ids),
                materials=list(item.materials),
                channels=list(item.channels),
            )
            for item in results
        ],
        meta=ResponseMeta(request_id=request.state.request_id),
    )

from __future__ import annotations

from datetime import date
from typing import Annotated, cast

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from pydantic import BaseModel, ConfigDict, HttpUrl

from taxmind.entrypoints.api.dependencies import current_principal
from taxmind.modules.documents.application.import_service import (
    ManualImportCommand,
    ManualImportService,
)
from taxmind.modules.documents.application.service import DocumentMetadataInput
from taxmind.shared.contracts.api import ResponseMeta
from taxmind.shared.domain.principal import Principal

router = APIRouter(tags=["knowledge-uploads"])


class ManualImportData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    job_status: str
    document_id: str | None
    document_version_id: str | None
    chunk_count: int
    idempotent: bool


class ManualImportResponse(BaseModel):
    data: ManualImportData
    meta: ResponseMeta


def _service(request: Request) -> ManualImportService:
    services = cast(dict[str, object], request.app.state.services)
    service = services.get("manual_import")
    if not isinstance(service, ManualImportService):
        raise RuntimeError("manual import service is not configured")
    return service


def _meta(request: Request) -> ResponseMeta:
    return ResponseMeta(request_id=request.state.request_id)


@router.post("/knowledge/uploads", response_model=ManualImportResponse, status_code=201)
async def upload_official_document(
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
    source_site_id: Annotated[str, Form(pattern="^[0-9a-f-]{36}$")],
    title: Annotated[str, Form(min_length=2, max_length=500)],
    issuing_authority: Annotated[str, Form(min_length=2, max_length=200)],
    region_code: Annotated[str, Form(pattern="^\\d{6}$")],
    canonical_url: Annotated[HttpUrl, Form()],
    file: Annotated[UploadFile, File()],
    doc_no: Annotated[str | None, Form(max_length=200)] = None,
    doc_type: Annotated[
        str,
        Form(pattern="^(law|regulation|announcement|interpretation|guide|faq)$"),
    ] = "announcement",
    source_level: Annotated[str, Form(pattern="^[A-D]$")] = "A",
    publish_date: Annotated[date | None, Form()] = None,
    effective_start: Annotated[date | None, Form()] = None,
    effective_end: Annotated[date | None, Form()] = None,
) -> ManualImportResponse:
    service = _service(request)
    content = await file.read(service.max_bytes + 1)
    result = await service.import_file(
        ManualImportCommand(
            source_site_id=source_site_id,
            filename=file.filename or "",
            mime_type=file.content_type or "",
            content=content,
            metadata=DocumentMetadataInput(
                title=title,
                doc_no=doc_no,
                doc_type=doc_type,
                source_level=source_level,
                issuing_authority=issuing_authority,
                region_code=region_code,
                publish_date=publish_date,
                effective_start=effective_start,
                effective_end=effective_end,
                policy_status="active",
                canonical_url=str(canonical_url),
            ),
            request_id=request.state.request_id,
        ),
        principal,
    )
    return ManualImportResponse(
        data=ManualImportData(
            job_id=result.job.id,
            job_status=result.job.status,
            document_id=result.document_id,
            document_version_id=result.document_version_id,
            chunk_count=result.chunk_count,
            idempotent=result.idempotent,
        ),
        meta=_meta(request),
    )

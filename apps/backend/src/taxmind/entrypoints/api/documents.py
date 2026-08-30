from __future__ import annotations

from datetime import date
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from taxmind.entrypoints.api.dependencies import current_principal
from taxmind.modules.documents.application.service import (
    ChunkInput,
    DocumentMetadataInput,
    DocumentsService,
    VersionInput,
)
from taxmind.modules.documents.domain import (
    DocumentChunkRecord,
    DocumentDetail,
    DocumentVersionRecord,
    PolicyEvidence,
    SourceDocumentRecord,
)
from taxmind.shared.contracts.api import ResponseMeta
from taxmind.shared.domain.principal import Principal

router = APIRouter(tags=["knowledge-documents"])


class DocumentMetadataPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=2, max_length=500)
    doc_no: str | None = Field(default=None, max_length=200)
    doc_type: str = Field(pattern="^(law|regulation|announcement|interpretation|guide|faq)$")
    source_level: str = Field(pattern="^[A-D]$")
    issuing_authority: str = Field(min_length=2, max_length=200)
    region_code: str = Field(pattern="^\\d{6}$")
    publish_date: date | None = None
    effective_start: date | None = None
    effective_end: date | None = None
    policy_status: str = Field(pattern="^active$")
    canonical_url: HttpUrl


class VersionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_url: HttpUrl
    mime_type: str = Field(min_length=3, max_length=128)
    content_hash_sha256: str = Field(pattern="^[0-9a-fA-F]{64}$")
    raw_object_key: str | None = Field(default=None, max_length=512)
    parsed_object_key: str | None = Field(default=None, max_length=512)


class CreateDocumentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metadata: DocumentMetadataPayload
    version: VersionPayload


class ChunkPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_chunk_id: str = Field(min_length=1, max_length=100)
    chunk_order: int = Field(ge=0)
    chunk_type: str = Field(pattern="^(title|chapter|article|paragraph|table|attachment)$")
    heading_path: str = Field(min_length=1, max_length=1000)
    clause_label: str | None = Field(default=None, max_length=100)
    content_text: str = Field(min_length=1, max_length=100000)
    content_hash_sha256: str = Field(pattern="^[0-9a-fA-F]{64}$")
    token_count: int = Field(ge=0)
    effective_start: date | None = None
    effective_end: date | None = None


class CreateChunksRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunks: list[ChunkPayload] = Field(min_length=1, max_length=200)


class DocumentData(BaseModel):
    id: str
    title: str
    doc_no: str | None
    doc_type: str
    source_level: str
    issuing_authority: str
    region_code: str
    effective_start: date | None
    effective_end: date | None
    policy_status: str
    canonical_url: str
    current_version_id: str | None
    review_status: str


class VersionData(BaseModel):
    id: str
    version_no: int
    source_url: str
    mime_type: str
    content_hash_sha256: str
    review_status: str
    published_at: str | None


class ChunkData(BaseModel):
    id: str
    source_chunk_id: str
    chunk_order: int
    chunk_type: str
    heading_path: str
    clause_label: str | None
    content_text: str
    effective_start: date | None
    effective_end: date | None
    region_code: str
    policy_status: str
    review_status: str
    index_status: str


class DocumentDetailData(BaseModel):
    document: DocumentData
    version: VersionData
    chunks: list[ChunkData]


class DocumentDetailResponse(BaseModel):
    data: DocumentDetailData
    meta: ResponseMeta


class PolicyEvidenceData(BaseModel):
    document: DocumentData
    version: VersionData
    chunk: ChunkData
    region_match: str


class PolicySearchResponse(BaseModel):
    data: list[PolicyEvidenceData]
    meta: ResponseMeta


def _service(request: Request) -> DocumentsService:
    services = cast(dict[str, object], request.app.state.services)
    service = services.get("documents")
    if not isinstance(service, DocumentsService):
        raise RuntimeError("documents service is not configured")
    return service


def _meta(request: Request) -> ResponseMeta:
    return ResponseMeta(request_id=request.state.request_id)


def _metadata_input(payload: DocumentMetadataPayload) -> DocumentMetadataInput:
    return DocumentMetadataInput(
        title=payload.title,
        doc_no=payload.doc_no,
        doc_type=payload.doc_type,
        source_level=payload.source_level,
        issuing_authority=payload.issuing_authority,
        region_code=payload.region_code,
        publish_date=payload.publish_date,
        effective_start=payload.effective_start,
        effective_end=payload.effective_end,
        policy_status=payload.policy_status,
        canonical_url=str(payload.canonical_url),
    )


def _version_input(payload: VersionPayload) -> VersionInput:
    return VersionInput(
        source_url=str(payload.source_url),
        mime_type=payload.mime_type,
        content_hash_sha256=payload.content_hash_sha256,
        raw_object_key=payload.raw_object_key,
        parsed_object_key=payload.parsed_object_key,
    )


def _chunk_input(payload: ChunkPayload) -> ChunkInput:
    return ChunkInput(
        source_chunk_id=payload.source_chunk_id,
        chunk_order=payload.chunk_order,
        chunk_type=payload.chunk_type,
        heading_path=payload.heading_path,
        clause_label=payload.clause_label,
        content_text=payload.content_text,
        content_hash_sha256=payload.content_hash_sha256,
        token_count=payload.token_count,
        effective_start=payload.effective_start,
        effective_end=payload.effective_end,
    )


def _document_data(record: SourceDocumentRecord) -> DocumentData:
    return DocumentData(
        id=record.id,
        title=record.title,
        doc_no=record.doc_no,
        doc_type=record.doc_type,
        source_level=record.source_level,
        issuing_authority=record.issuing_authority,
        region_code=record.region_code,
        effective_start=record.effective_start,
        effective_end=record.effective_end,
        policy_status=record.policy_status,
        canonical_url=record.canonical_url,
        current_version_id=record.current_version_id,
        review_status=record.review_status,
    )


def _version_data(record: DocumentVersionRecord) -> VersionData:
    return VersionData(
        id=record.id,
        version_no=record.version_no,
        source_url=record.source_url,
        mime_type=record.mime_type,
        content_hash_sha256=record.content_hash_sha256,
        review_status=record.review_status,
        published_at=record.published_at.isoformat() if record.published_at else None,
    )


def _chunk_data(record: DocumentChunkRecord) -> ChunkData:
    return ChunkData(
        id=record.id,
        source_chunk_id=record.source_chunk_id,
        chunk_order=record.chunk_order,
        chunk_type=record.chunk_type,
        heading_path=record.heading_path,
        clause_label=record.clause_label,
        content_text=record.content_text,
        effective_start=record.effective_start,
        effective_end=record.effective_end,
        region_code=record.region_code,
        policy_status=record.policy_status,
        review_status=record.review_status,
        index_status=record.index_status,
    )


def _detail_data(detail: DocumentDetail) -> DocumentDetailData:
    return DocumentDetailData(
        document=_document_data(detail.document),
        version=_version_data(detail.version),
        chunks=[_chunk_data(chunk) for chunk in detail.chunks],
    )


def _evidence_data(evidence: PolicyEvidence) -> PolicyEvidenceData:
    return PolicyEvidenceData(
        document=_document_data(evidence.document),
        version=_version_data(evidence.version),
        chunk=_chunk_data(evidence.chunk),
        region_match=evidence.region_match,
    )


@router.post("/knowledge/documents", response_model=DocumentDetailResponse)
async def create_document(
    payload: CreateDocumentRequest,
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
) -> DocumentDetailResponse:
    detail = await _service(request).create_document(
        _metadata_input(payload.metadata),
        _version_input(payload.version),
        request_id=request.state.request_id,
        principal=principal,
    )
    return DocumentDetailResponse(data=_detail_data(detail), meta=_meta(request))


@router.post("/knowledge/documents/{document_id}/versions", response_model=DocumentDetailResponse)
async def create_version(
    document_id: str,
    payload: VersionPayload,
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
) -> DocumentDetailResponse:
    detail = await _service(request).create_version(
        document_id,
        _version_input(payload),
        request_id=request.state.request_id,
        principal=principal,
    )
    return DocumentDetailResponse(data=_detail_data(detail), meta=_meta(request))


@router.post(
    "/knowledge/document-versions/{version_id}/chunks", response_model=DocumentDetailResponse
)
async def create_chunks(
    version_id: str,
    payload: CreateChunksRequest,
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
) -> DocumentDetailResponse:
    detail = await _service(request).create_chunks(
        version_id,
        [_chunk_input(chunk) for chunk in payload.chunks],
        request_id=request.state.request_id,
        principal=principal,
    )
    return DocumentDetailResponse(data=_detail_data(detail), meta=_meta(request))


@router.post(
    "/knowledge/document-versions/{version_id}/submit-review", response_model=DocumentDetailResponse
)
async def submit_review(
    version_id: str,
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
) -> DocumentDetailResponse:
    detail = await _service(request).submit_review(
        version_id,
        request_id=request.state.request_id,
        principal=principal,
    )
    return DocumentDetailResponse(data=_detail_data(detail), meta=_meta(request))


@router.post(
    "/knowledge/document-versions/{version_id}/publish", response_model=DocumentDetailResponse
)
async def publish(
    version_id: str,
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
) -> DocumentDetailResponse:
    detail = await _service(request).publish(
        version_id,
        request_id=request.state.request_id,
        principal=principal,
    )
    return DocumentDetailResponse(data=_detail_data(detail), meta=_meta(request))


@router.get("/policies/search", response_model=PolicySearchResponse)
async def search_policies(
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
    query: Annotated[str, Query(min_length=1, max_length=200)],
    region_code: Annotated[str, Query(pattern="^\\d{6}$")],
    business_date: date,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> PolicySearchResponse:
    evidences = await _service(request).search_published(
        query=query,
        region_code=region_code,
        business_date=business_date,
        limit=limit,
        principal=principal,
    )
    return PolicySearchResponse(
        data=[_evidence_data(item) for item in evidences], meta=_meta(request)
    )

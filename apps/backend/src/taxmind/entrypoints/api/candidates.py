from __future__ import annotations

from decimal import Decimal
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from taxmind.entrypoints.api.dependencies import current_principal
from taxmind.modules.knowledge.application.review_service import KnowledgeReviewService
from taxmind.modules.knowledge.application.service import (
    CreatedCandidateBatch,
    KnowledgeCandidatesService,
)
from taxmind.modules.knowledge.application.snapshot_service import KnowledgeSnapshotService
from taxmind.modules.knowledge.domain import (
    KnowledgeCandidateBatchRecord,
    KnowledgeCandidateRecord,
    KnowledgePublishBatchRecord,
    KnowledgeSnapshotRecord,
)
from taxmind.shared.contracts.api import ResponseMeta
from taxmind.shared.domain.principal import Principal

router = APIRouter(tags=["knowledge-candidates"])


class CandidateBatchData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    document_version_id: str
    extraction_method: str
    extractor_version: str
    model_name: str | None
    prompt_version: str | None
    status: str
    candidate_count: int
    created_at: str


class KnowledgeCandidateData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    batch_id: str
    candidate_type: str
    payload: dict[str, object]
    source_document_id: str
    source_chunk_id: str
    extraction_method: str
    extraction_confidence: Decimal
    normalization_status: str
    review_status: str
    review_reason_safe: str | None
    reviewed_by: str | None
    reviewed_at: str | None
    created_at: str


class CreatedCandidateBatchData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    batch: CandidateBatchData
    candidates: list[KnowledgeCandidateData]
    created: bool


class CreatedCandidateBatchResponse(BaseModel):
    data: CreatedCandidateBatchData
    meta: ResponseMeta


class CandidateQueueResponse(BaseModel):
    data: list[KnowledgeCandidateData]
    meta: ResponseMeta


class CandidateReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(pattern="^(approved|rejected)$")
    reason: str | None = Field(default=None, max_length=1000)


class KnowledgePublishBatchData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    batch_type: str
    scope: str
    status: str
    candidate_count: int
    approved_count: int
    rejected_count: int
    validation_report: dict[str, object]
    manifest_hash: str | None
    submitted_at: str
    published_at: str | None
    created_at: str


class KnowledgeCandidateResponse(BaseModel):
    data: KnowledgeCandidateData
    meta: ResponseMeta


class CreatePublishBatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_ids: list[str] = Field(min_length=1, max_length=100)


class KnowledgePublishBatchResponse(BaseModel):
    data: KnowledgePublishBatchData
    meta: ResponseMeta


class KnowledgeSnapshotData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    snapshot_code: str
    snapshot_type: str
    status: str
    manifest_hash: str
    activated_at: str | None
    created_at: str
    pending_projection_event_count: int


class KnowledgeSnapshotResponse(BaseModel):
    data: KnowledgeSnapshotData
    meta: ResponseMeta


def _service(request: Request) -> KnowledgeCandidatesService:
    services = cast(dict[str, object], request.app.state.services)
    service = services.get("knowledge_candidates")
    if not isinstance(service, KnowledgeCandidatesService):
        raise RuntimeError("knowledge candidates service is not configured")
    return service


def _review_service(request: Request) -> KnowledgeReviewService:
    services = cast(dict[str, object], request.app.state.services)
    service = services.get("knowledge_review")
    if not isinstance(service, KnowledgeReviewService):
        raise RuntimeError("knowledge review service is not configured")
    return service


def _snapshot_service(request: Request) -> KnowledgeSnapshotService:
    service = cast(dict[str, object], request.app.state.services).get("knowledge_snapshot")
    if not isinstance(service, KnowledgeSnapshotService):
        raise RuntimeError("knowledge snapshot service is not configured")
    return service


def _meta(request: Request) -> ResponseMeta:
    return ResponseMeta(request_id=request.state.request_id)


def _batch_data(record: KnowledgeCandidateBatchRecord) -> CandidateBatchData:
    return CandidateBatchData(
        id=record.id,
        document_version_id=record.document_version_id,
        extraction_method=record.extraction_method,
        extractor_version=record.extractor_version,
        model_name=record.model_name,
        prompt_version=record.prompt_version,
        status=record.status,
        candidate_count=record.candidate_count,
        created_at=record.created_at.isoformat(),
    )


def _candidate_data(record: KnowledgeCandidateRecord) -> KnowledgeCandidateData:
    return KnowledgeCandidateData(
        id=record.id,
        batch_id=record.batch_id,
        candidate_type=record.candidate_type,
        payload=record.payload,
        source_document_id=record.source_document_id,
        source_chunk_id=record.source_chunk_id,
        extraction_method=record.extraction_method,
        extraction_confidence=record.extraction_confidence,
        normalization_status=record.normalization_status,
        review_status=record.review_status,
        review_reason_safe=record.review_reason_safe,
        reviewed_by=record.reviewed_by,
        reviewed_at=record.reviewed_at.isoformat() if record.reviewed_at else None,
        created_at=record.created_at.isoformat(),
    )


def _created_data(result: CreatedCandidateBatch) -> CreatedCandidateBatchData:
    return CreatedCandidateBatchData(
        batch=_batch_data(result.batch),
        candidates=[_candidate_data(candidate) for candidate in result.candidates],
        created=result.created,
    )


def _publish_batch_data(record: KnowledgePublishBatchRecord) -> KnowledgePublishBatchData:
    return KnowledgePublishBatchData(
        id=record.id,
        batch_type=record.batch_type,
        scope=record.scope,
        status=record.status,
        candidate_count=record.candidate_count,
        approved_count=record.approved_count,
        rejected_count=record.rejected_count,
        validation_report=record.validation_report,
        manifest_hash=record.manifest_hash,
        submitted_at=record.submitted_at.isoformat(),
        published_at=record.published_at.isoformat() if record.published_at else None,
        created_at=record.created_at.isoformat(),
    )


def _snapshot_data(
    record: KnowledgeSnapshotRecord, *, pending_projection_event_count: int
) -> KnowledgeSnapshotData:
    return KnowledgeSnapshotData(
        id=record.id,
        snapshot_code=record.snapshot_code,
        snapshot_type=record.snapshot_type,
        status=record.status,
        manifest_hash=record.manifest_hash,
        activated_at=record.activated_at.isoformat() if record.activated_at else None,
        created_at=record.created_at.isoformat(),
        pending_projection_event_count=pending_projection_event_count,
    )


@router.post(
    "/knowledge/document-versions/{version_id}/candidate-batches",
    response_model=CreatedCandidateBatchResponse,
    status_code=201,
)
async def create_rule_based_candidate_batch(
    version_id: str,
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
) -> CreatedCandidateBatchResponse:
    result = await _service(request).create_rule_based_batch(
        version_id,
        request_id=request.state.request_id,
        principal=principal,
    )
    return CreatedCandidateBatchResponse(data=_created_data(result), meta=_meta(request))


@router.get("/knowledge/candidates", response_model=CandidateQueueResponse)
async def list_pending_knowledge_candidates(
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> CandidateQueueResponse:
    candidates = await _service(request).list_pending_candidates(
        limit=limit,
        principal=principal,
    )
    return CandidateQueueResponse(
        data=[_candidate_data(candidate) for candidate in candidates], meta=_meta(request)
    )


@router.post(
    "/knowledge/candidates/{candidate_id}/review", response_model=KnowledgeCandidateResponse
)
async def review_knowledge_candidate(
    candidate_id: str,
    payload: CandidateReviewRequest,
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
) -> KnowledgeCandidateResponse:
    candidate = await _review_service(request).review_candidate(
        candidate_id,
        decision=payload.decision,
        reason=payload.reason,
        request_id=request.state.request_id,
        principal=principal,
    )
    return KnowledgeCandidateResponse(data=_candidate_data(candidate), meta=_meta(request))


@router.post(
    "/knowledge/publish-batches", response_model=KnowledgePublishBatchResponse, status_code=201
)
async def create_knowledge_publish_batch(
    payload: CreatePublishBatchRequest,
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
) -> KnowledgePublishBatchResponse:
    batch = await _review_service(request).create_publish_batch(
        candidate_ids=payload.candidate_ids,
        request_id=request.state.request_id,
        principal=principal,
    )
    return KnowledgePublishBatchResponse(data=_publish_batch_data(batch), meta=_meta(request))


@router.post(
    "/knowledge/publish-batches/{batch_id}/validate", response_model=KnowledgePublishBatchResponse
)
async def validate_knowledge_publish_batch(
    batch_id: str,
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
) -> KnowledgePublishBatchResponse:
    batch = await _review_service(request).validate_publish_batch(
        batch_id,
        request_id=request.state.request_id,
        principal=principal,
    )
    return KnowledgePublishBatchResponse(data=_publish_batch_data(batch), meta=_meta(request))


@router.post(
    "/knowledge/publish-batches/{batch_id}/materialize-snapshot",
    response_model=KnowledgeSnapshotResponse,
    status_code=201,
)
async def materialize_knowledge_snapshot(
    batch_id: str, request: Request, principal: Annotated[Principal, Depends(current_principal)]
) -> KnowledgeSnapshotResponse:
    result = await _snapshot_service(request).materialize_validated_batch(
        batch_id, request_id=request.state.request_id, principal=principal
    )
    return KnowledgeSnapshotResponse(
        data=_snapshot_data(
            result.snapshot,
            pending_projection_event_count=len(result.events),
        ),
        meta=_meta(request),
    )

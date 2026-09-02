from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from typing import Protocol

from taxmind.modules.documents.domain import (
    DocumentChunkRecord,
    SourceDocumentRecord,
)
from taxmind.modules.knowledge.domain import (
    KnowledgeCandidateBatchRecord,
    KnowledgeCandidateRecord,
)
from taxmind.modules.knowledge.infrastructure.repository import SqlAlchemyKnowledgeRepository
from taxmind.modules.knowledge.infrastructure.uow import SqlAlchemyKnowledgeUnitOfWork
from taxmind.shared.domain.errors import DomainError
from taxmind.shared.domain.ids import new_id
from taxmind.shared.domain.principal import Principal

_RULE_EXTRACTION_METHOD = "rule_based"
_RULE_EXTRACTOR_VERSION = "rule_based_v1"
_CANDIDATE_TYPE = "policy_clause"
_PENDING_REVIEW = "pending_review"


class KnowledgeCandidatesUnitOfWorkFactory(Protocol):
    def __call__(self) -> SqlAlchemyKnowledgeUnitOfWork: ...


@dataclass(frozen=True, slots=True)
class CreatedCandidateBatch:
    batch: KnowledgeCandidateBatchRecord
    candidates: list[KnowledgeCandidateRecord]
    created: bool


class KnowledgeCandidatesService:
    def __init__(self, *, uow_factory: KnowledgeCandidatesUnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def create_rule_based_batch(
        self,
        document_version_id: str,
        *,
        request_id: str,
        principal: Principal,
    ) -> CreatedCandidateBatch:
        _require_knowledge_write(principal)
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            version = await repository.get_version(document_version_id, lock=True)
            if version is None:
                raise DomainError(code="RESOURCE_NOT_FOUND", message="资料版本不存在")
            if version.review_status != "draft" or version.parse_status != "parsed":
                raise DomainError(
                    code="POLICY_STATUS_CONFLICT",
                    message="仅已解析的草稿资料可生成知识候选",
                )
            document = await repository.get_document(version.document_id)
            if document is None:
                raise DomainError(code="RESOURCE_CONFLICT", message="资料主记录不存在")
            existing = await repository.get_completed_rule_batch(version.id)
            if existing is not None:
                return CreatedCandidateBatch(
                    batch=existing,
                    candidates=await repository.list_candidates_by_batch(existing.id),
                    created=False,
                )
            chunks = await repository.list_chunks(version.id)
            if not chunks:
                raise DomainError(
                    code="POLICY_STATUS_CONFLICT", message="资料版本至少需要一条可引用条款"
                )
            batch = KnowledgeCandidateBatchRecord(
                id=new_id(),
                document_version_id=version.id,
                extraction_method=_RULE_EXTRACTION_METHOD,
                extractor_version=_RULE_EXTRACTOR_VERSION,
                model_name=None,
                prompt_version=None,
                status="completed",
                candidate_count=len(chunks),
                created_by=principal.user_id,
                created_at=now,
            )
            candidates = [_candidate(chunk, document, batch, now) for chunk in chunks]
            await repository.create_batch(batch)
            await repository.create_candidates(candidates)
            await repository.create_audit_log(
                org_id=principal.org_id,
                actor_user_id=principal.user_id,
                action_code="knowledge.candidate_batch.created",
                resource_id=batch.id,
                request_id=request_id,
                occurred_at=now,
            )
            await uow.commit()
            return CreatedCandidateBatch(batch=batch, candidates=candidates, created=True)

    async def list_pending_candidates(
        self, *, limit: int, principal: Principal
    ) -> list[KnowledgeCandidateRecord]:
        _require_knowledge_read(principal)
        if not 1 <= limit <= 100:
            raise DomainError(code="VALIDATION_FAILED", message="候选队列数量必须在 1 到 100 之间")
        async with self._uow_factory() as uow:
            return await _repository(uow).list_pending_candidates(limit=limit)

    async def list_approved_candidates(
        self, *, limit: int, principal: Principal
    ) -> list[KnowledgeCandidateRecord]:
        _require_knowledge_read(principal)
        if not 1 <= limit <= 100:
            raise DomainError(code="VALIDATION_FAILED", message="候选队列数量必须在 1 到 100 之间")
        async with self._uow_factory() as uow:
            return await _repository(uow).list_approved_candidates(limit=limit)


def _repository(uow: SqlAlchemyKnowledgeUnitOfWork) -> SqlAlchemyKnowledgeRepository:
    if uow.repository is None:
        raise RuntimeError("unit of work repository is unavailable")
    return uow.repository


def _require_knowledge_write(principal: Principal) -> None:
    if not principal.has_permission("knowledge:write"):
        raise DomainError(code="AUTH_FORBIDDEN", message="当前角色无知识维护权限")


def _require_knowledge_read(principal: Principal) -> None:
    if not principal.has_permission("knowledge:read"):
        raise DomainError(code="AUTH_FORBIDDEN", message="当前角色无知识检索权限")


def _candidate(
    chunk: DocumentChunkRecord,
    document: SourceDocumentRecord,
    batch: KnowledgeCandidateBatchRecord,
    now: datetime,
) -> KnowledgeCandidateRecord:
    payload: dict[str, object] = {
        "title": document.title,
        "doc_no": document.doc_no,
        "source_url": document.canonical_url,
        "region_code": chunk.region_code,
        "policy_status": chunk.policy_status,
        "heading_path": chunk.heading_path,
        "clause_label": chunk.clause_label,
        "text_excerpt": chunk.content_text[:1000],
        "effective_start": chunk.effective_start.isoformat() if chunk.effective_start else None,
        "effective_end": chunk.effective_end.isoformat() if chunk.effective_end else None,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return KnowledgeCandidateRecord(
        id=new_id(),
        batch_id=batch.id,
        candidate_type=_CANDIDATE_TYPE,
        payload=payload,
        source_document_id=document.id,
        source_chunk_id=chunk.source_chunk_id,
        extraction_method=_RULE_EXTRACTION_METHOD,
        extraction_confidence=Decimal("0.9500"),
        normalization_status="not_required",
        review_status=_PENDING_REVIEW,
        review_reason_safe=None,
        reviewed_by=None,
        reviewed_at=None,
        content_hash=sha256(encoded.encode("utf-8")).hexdigest(),
        created_at=now,
    )

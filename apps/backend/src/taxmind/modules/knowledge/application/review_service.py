from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha256
from typing import Protocol

from taxmind.modules.knowledge.domain import (
    KnowledgeCandidateRecord,
    KnowledgePublishBatchItemRecord,
    KnowledgePublishBatchRecord,
)
from taxmind.modules.knowledge.infrastructure.repository import SqlAlchemyKnowledgeRepository
from taxmind.modules.knowledge.infrastructure.uow import SqlAlchemyKnowledgeUnitOfWork
from taxmind.shared.domain.errors import DomainError
from taxmind.shared.domain.ids import new_id
from taxmind.shared.domain.principal import Principal


class KnowledgeReviewUnitOfWorkFactory(Protocol):
    def __call__(self) -> SqlAlchemyKnowledgeUnitOfWork: ...


class KnowledgeReviewService:
    def __init__(self, *, uow_factory: KnowledgeReviewUnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def review_candidate(
        self,
        candidate_id: str,
        *,
        decision: str,
        reason: str | None,
        request_id: str,
        principal: Principal,
    ) -> KnowledgeCandidateRecord:
        _require_knowledge_review(principal)
        if decision not in {"approved", "rejected"}:
            raise DomainError(code="VALIDATION_FAILED", message="候选审核决定无效")
        normalized_reason = _review_reason(decision, reason)
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            candidate = await repository.get_candidate(candidate_id, lock=True)
            if candidate is None:
                raise DomainError(code="RESOURCE_NOT_FOUND", message="知识候选不存在")
            if candidate.review_status != "pending_review":
                raise DomainError(code="POLICY_STATUS_CONFLICT", message="候选当前不能再次审核")
            source_batch = await repository.get_candidate_batch(candidate.batch_id)
            if source_batch is None:
                raise DomainError(code="RESOURCE_CONFLICT", message="候选批次不存在")
            if source_batch.created_by == principal.user_id:
                raise DomainError(code="AUTH_FORBIDDEN", message="候选抽取者不得审核自己的候选")
            reviewed = replace(
                candidate,
                review_status=decision,
                review_reason_safe=normalized_reason,
                reviewed_by=principal.user_id,
                reviewed_at=now,
            )
            await repository.set_candidate_review(reviewed)
            await repository.create_audit_log(
                org_id=principal.org_id,
                actor_user_id=principal.user_id,
                action_code="knowledge.candidate.reviewed",
                resource_id=reviewed.id,
                request_id=request_id,
                occurred_at=now,
            )
            await uow.commit()
            return reviewed

    async def create_publish_batch(
        self,
        *,
        candidate_ids: list[str],
        request_id: str,
        principal: Principal,
    ) -> KnowledgePublishBatchRecord:
        _require_knowledge_review(principal)
        _validate_candidate_ids(candidate_ids)
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            candidates = await repository.list_candidates_by_ids(candidate_ids)
            if len(candidates) != len(candidate_ids):
                raise DomainError(code="RESOURCE_NOT_FOUND", message="存在不存在的知识候选")
            if any(candidate.review_status != "approved" for candidate in candidates):
                raise DomainError(
                    code="POLICY_STATUS_CONFLICT", message="仅已审核通过的候选可进入发布批次"
                )
            manifest_hash = _manifest_hash(candidates)
            batch = KnowledgePublishBatchRecord(
                id=new_id(),
                batch_type="knowledge_candidate",
                scope="public",
                org_id=None,
                status="pending_validation",
                candidate_count=len(candidates),
                approved_count=len(candidates),
                rejected_count=0,
                validation_report={},
                manifest_hash=manifest_hash,
                submitted_by=principal.user_id,
                approved_by=None,
                submitted_at=now,
                published_at=None,
                created_at=now,
            )
            items = [
                KnowledgePublishBatchItemRecord(
                    id=new_id(),
                    batch_id=batch.id,
                    candidate_id=candidate.id,
                    decision="approved",
                    checksum=candidate.content_hash,
                )
                for candidate in candidates
            ]
            await repository.create_publish_batch(batch)
            await repository.flush()
            await repository.create_publish_items(items)
            await repository.create_audit_log(
                org_id=principal.org_id,
                actor_user_id=principal.user_id,
                action_code="knowledge.publish_batch.created",
                resource_id=batch.id,
                request_id=request_id,
                occurred_at=now,
            )
            await uow.commit()
            return batch

    async def validate_publish_batch(
        self,
        batch_id: str,
        *,
        request_id: str,
        principal: Principal,
    ) -> KnowledgePublishBatchRecord:
        _require_knowledge_review(principal)
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            batch = await repository.get_publish_batch(batch_id, lock=True)
            if batch is None:
                raise DomainError(code="RESOURCE_NOT_FOUND", message="发布批次不存在")
            if batch.status not in {"pending_validation", "validation_failed", "validated"}:
                raise DomainError(code="POLICY_STATUS_CONFLICT", message="发布批次当前不能验证")
            candidates = await repository.list_publish_candidates(batch.id)
            failures = _validation_failures(batch, candidates)
            report: dict[str, object] = {
                "passed": not failures,
                "checked_candidate_count": len(candidates),
                "failures": failures,
                "validated_at": now.isoformat(),
            }
            validated = replace(
                batch,
                status="validated" if not failures else "validation_failed",
                validation_report=report,
            )
            await repository.set_publish_batch_validation(validated)
            await repository.create_audit_log(
                org_id=principal.org_id,
                actor_user_id=principal.user_id,
                action_code="knowledge.publish_batch.validated",
                resource_id=batch.id,
                request_id=request_id,
                occurred_at=now,
            )
            await uow.commit()
            return validated


def _repository(uow: SqlAlchemyKnowledgeUnitOfWork) -> SqlAlchemyKnowledgeRepository:
    if uow.repository is None:
        raise RuntimeError("unit of work repository is unavailable")
    return uow.repository


def _require_knowledge_review(principal: Principal) -> None:
    if not principal.has_permission("knowledge:review"):
        raise DomainError(code="AUTH_FORBIDDEN", message="当前角色无知识审核权限")


def _review_reason(decision: str, reason: str | None) -> str | None:
    normalized = reason.strip() if reason else ""
    if decision == "rejected" and len(normalized) < 3:
        raise DomainError(
            code="VALIDATION_FAILED", message="驳回候选必须填写不少于 3 个字符的安全原因"
        )
    if len(normalized) > 1000:
        raise DomainError(code="VALIDATION_FAILED", message="审核原因不能超过 1000 个字符")
    return normalized or None


def _validate_candidate_ids(candidate_ids: list[str]) -> None:
    if not candidate_ids or len(candidate_ids) > 100:
        raise DomainError(code="VALIDATION_FAILED", message="发布批次候选数量必须在 1 到 100 之间")
    if len(set(candidate_ids)) != len(candidate_ids):
        raise DomainError(code="VALIDATION_FAILED", message="发布批次候选不得重复")


def _manifest_hash(candidates: list[KnowledgeCandidateRecord]) -> str:
    payload = [
        {"candidate_id": candidate.id, "checksum": candidate.content_hash}
        for candidate in sorted(candidates, key=lambda item: item.id)
    ]
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


def _validation_failures(
    batch: KnowledgePublishBatchRecord, candidates: list[KnowledgeCandidateRecord]
) -> list[str]:
    failures: list[str] = []
    if len(candidates) != batch.candidate_count:
        failures.append("candidate_count_mismatch")
    if any(candidate.review_status != "approved" for candidate in candidates):
        failures.append("candidate_not_approved")
    if any(
        not candidate.source_document_id or not candidate.source_chunk_id
        for candidate in candidates
    ):
        failures.append("source_reference_missing")
    if _manifest_hash(candidates) != batch.manifest_hash:
        failures.append("manifest_checksum_mismatch")
    return failures

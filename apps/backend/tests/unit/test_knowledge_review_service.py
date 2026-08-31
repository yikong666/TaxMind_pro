from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from taxmind.modules.knowledge.application.review_service import KnowledgeReviewService
from taxmind.modules.knowledge.domain import (
    KnowledgeCandidateBatchRecord,
    KnowledgeCandidateRecord,
    KnowledgePublishBatchItemRecord,
    KnowledgePublishBatchRecord,
)
from taxmind.shared.domain.errors import DomainError
from taxmind.shared.domain.principal import Principal

_NOW = datetime(2026, 8, 31, tzinfo=UTC)
_AUTHOR_ID = "018f4cc1-7852-7d5d-8c1c-dbd404e8e101"
_REVIEWER_ID = "018f4cc1-7852-7d5d-8c1c-dbd404e8e102"
_CANDIDATE_ID = "018f4cc1-7852-7d5d-8c1c-dbd404e8e201"


class _Repository:
    def __init__(self) -> None:
        self.batch = KnowledgeCandidateBatchRecord(
            id="018f4cc1-7852-7d5d-8c1c-dbd404e8e301",
            document_version_id="018f4cc1-7852-7d5d-8c1c-dbd404e8e302",
            extraction_method="rule_based",
            extractor_version="rule_based_v1",
            model_name=None,
            prompt_version=None,
            status="completed",
            candidate_count=1,
            created_by=_AUTHOR_ID,
            created_at=_NOW,
        )
        self.candidate = KnowledgeCandidateRecord(
            id=_CANDIDATE_ID,
            batch_id=self.batch.id,
            candidate_type="policy_clause",
            payload={"source_url": "https://example.invalid/stage5/review"},
            source_document_id="018f4cc1-7852-7d5d-8c1c-dbd404e8e401",
            source_chunk_id="stage5-review:1",
            extraction_method="rule_based",
            extraction_confidence=Decimal("0.9500"),
            normalization_status="not_required",
            review_status="pending_review",
            review_reason_safe=None,
            reviewed_by=None,
            reviewed_at=None,
            content_hash="a" * 64,
            created_at=_NOW,
        )
        self.updated_candidate: KnowledgeCandidateRecord | None = None
        self.publish_batch: KnowledgePublishBatchRecord | None = None
        self.publish_items: list[KnowledgePublishBatchItemRecord] = []
        self.flushed = False
        self.audit_actions: list[str] = []

    async def get_candidate(
        self, candidate_id: str, *, lock: bool = False
    ) -> KnowledgeCandidateRecord | None:
        del lock
        return self.candidate if candidate_id == self.candidate.id else None

    async def get_candidate_batch(self, batch_id: str) -> KnowledgeCandidateBatchRecord | None:
        return self.batch if batch_id == self.batch.id else None

    async def set_candidate_review(self, record: KnowledgeCandidateRecord) -> None:
        self.updated_candidate = record
        self.candidate = record

    async def list_candidates_by_ids(
        self, candidate_ids: list[str]
    ) -> list[KnowledgeCandidateRecord]:
        return [self.candidate] if candidate_ids == [self.candidate.id] else []

    async def create_publish_batch(self, record: KnowledgePublishBatchRecord) -> None:
        self.publish_batch = record

    async def flush(self) -> None:
        self.flushed = True

    async def create_publish_items(self, records: list[KnowledgePublishBatchItemRecord]) -> None:
        self.publish_items.extend(records)

    async def get_publish_batch(
        self, batch_id: str, *, lock: bool = False
    ) -> KnowledgePublishBatchRecord | None:
        del lock
        if self.publish_batch is not None and self.publish_batch.id == batch_id:
            return self.publish_batch
        return None

    async def list_publish_candidates(self, batch_id: str) -> list[KnowledgeCandidateRecord]:
        if self.publish_batch is not None and self.publish_batch.id == batch_id:
            return [self.candidate]
        return []

    async def set_publish_batch_validation(self, record: KnowledgePublishBatchRecord) -> None:
        self.publish_batch = record

    async def create_audit_log(self, **kwargs: object) -> None:
        action_code = kwargs["action_code"]
        assert isinstance(action_code, str)
        self.audit_actions.append(action_code)


class _UnitOfWork:
    def __init__(self, repository: _Repository) -> None:
        self.repository = repository
        self.committed = False

    async def __aenter__(self) -> _UnitOfWork:
        return self

    async def commit(self) -> None:
        self.committed = True

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


def _principal(user_id: str, permissions: frozenset[str] | None = None) -> Principal:
    return Principal(
        user_id=user_id,
        org_id="018f4cc1-7852-7d5d-8c1c-dbd404e8e001",
        session_id="018f4cc1-7852-7d5d-8c1c-dbd404e8e002",
        roles=frozenset({"knowledge_admin"}),
        permissions=permissions or frozenset({"knowledge:review"}),
    )


async def test_reviewer_approves_pending_candidate_with_auditable_identity() -> None:
    repository = _Repository()
    unit_of_work = _UnitOfWork(repository)
    service = KnowledgeReviewService(uow_factory=lambda: unit_of_work)  # type: ignore[arg-type]

    result = await service.review_candidate(
        _CANDIDATE_ID,
        decision="approved",
        reason=None,
        request_id="request-stage5-review-approved",
        principal=_principal(_REVIEWER_ID),
    )

    assert result.review_status == "approved"
    assert result.reviewed_by == _REVIEWER_ID
    assert result.reviewed_at is not None
    assert repository.audit_actions == ["knowledge.candidate.reviewed"]
    assert unit_of_work.committed is True


async def test_extractor_cannot_review_own_candidate_and_rejection_needs_reason() -> None:
    service = KnowledgeReviewService(
        uow_factory=lambda: _UnitOfWork(_Repository())  # type: ignore[arg-type]
    )
    with pytest.raises(DomainError) as self_review:
        await service.review_candidate(
            _CANDIDATE_ID,
            decision="approved",
            reason=None,
            request_id="request-stage5-self-review",
            principal=_principal(_AUTHOR_ID),
        )
    with pytest.raises(DomainError) as missing_reason:
        await service.review_candidate(
            _CANDIDATE_ID,
            decision="rejected",
            reason=" ",
            request_id="request-stage5-reject",
            principal=_principal(_REVIEWER_ID),
        )

    assert self_review.value.code == "AUTH_FORBIDDEN"
    assert missing_reason.value.code == "VALIDATION_FAILED"


async def test_approved_candidate_creates_and_validates_non_publishing_batch() -> None:
    repository = _Repository()
    repository.candidate = replace(
        repository.candidate,
        review_status="approved",
        reviewed_by=_REVIEWER_ID,
        reviewed_at=_NOW,
    )
    service = KnowledgeReviewService(
        uow_factory=lambda: _UnitOfWork(repository)  # type: ignore[arg-type]
    )
    principal = _principal(_REVIEWER_ID)

    created = await service.create_publish_batch(
        candidate_ids=[_CANDIDATE_ID],
        request_id="request-stage5-publish-batch",
        principal=principal,
    )
    validated = await service.validate_publish_batch(
        created.id,
        request_id="request-stage5-publish-validate",
        principal=principal,
    )

    assert created.status == "pending_validation"
    assert created.manifest_hash is not None
    assert repository.flushed is True
    assert len(repository.publish_items) == 1
    assert validated.status == "validated"
    assert validated.validation_report["passed"] is True
    assert repository.audit_actions == [
        "knowledge.publish_batch.created",
        "knowledge.publish_batch.validated",
    ]

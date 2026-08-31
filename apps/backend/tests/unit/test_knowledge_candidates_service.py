from __future__ import annotations

from datetime import UTC, datetime

import pytest

from taxmind.modules.documents.domain import (
    DocumentChunkRecord,
    DocumentVersionRecord,
    SourceDocumentRecord,
)
from taxmind.modules.knowledge.application.service import KnowledgeCandidatesService
from taxmind.modules.knowledge.domain import (
    KnowledgeCandidateBatchRecord,
    KnowledgeCandidateRecord,
)
from taxmind.shared.domain.errors import DomainError
from taxmind.shared.domain.principal import Principal

_NOW = datetime(2026, 8, 31, tzinfo=UTC)
_DOCUMENT_ID = "018f4cc1-7852-7d5d-8c1c-dbd404e8c201"
_VERSION_ID = "018f4cc1-7852-7d5d-8c1c-dbd404e8c202"


class _Repository:
    def __init__(self, *, version_status: str = "draft") -> None:
        self.document = SourceDocumentRecord(
            id=_DOCUMENT_ID,
            canonical_key="虚构机关::STAGE5-CANDIDATE-001",
            title="阶段五虚构候选资料",
            doc_no="STAGE5-CANDIDATE-001",
            doc_type="announcement",
            source_level="A",
            issuing_authority="虚构机关",
            region_code="440300",
            publish_date=None,
            effective_start=None,
            effective_end=None,
            policy_status="active",
            canonical_url="https://example.invalid/stage5/candidates",
            current_version_id=None,
            review_status=version_status,
            created_by=_principal().user_id,
            created_at=_NOW,
            updated_at=_NOW,
        )
        self.version = DocumentVersionRecord(
            id=_VERSION_ID,
            document_id=_DOCUMENT_ID,
            version_no=1,
            captured_at=_NOW,
            source_url="https://example.invalid/stage5/candidates",
            raw_object_key="stage5/raw.txt",
            parsed_object_key=None,
            mime_type="text/plain",
            content_hash_sha256="a" * 64,
            parse_status="parsed",
            ocr_status="not_required",
            review_status=version_status,
            published_at=None,
            supersedes_version_id=None,
            created_by=_principal().user_id,
        )
        self.chunks = [
            _chunk("stage5-candidate:1", 0, "第一条", "第一条 本资料仅用于候选抽取测试。"),
            _chunk("stage5-candidate:2", 1, "第二条", "第二条 未审核候选不得进入正式检索。"),
        ]
        self.batches: list[KnowledgeCandidateBatchRecord] = []
        self.candidates: list[KnowledgeCandidateRecord] = []
        self.audit_actions: list[str] = []

    async def get_version(
        self, version_id: str, *, lock: bool = False
    ) -> DocumentVersionRecord | None:
        del lock
        return self.version if version_id == self.version.id else None

    async def get_document(self, document_id: str) -> SourceDocumentRecord | None:
        return self.document if document_id == self.document.id else None

    async def list_chunks(self, version_id: str) -> list[DocumentChunkRecord]:
        return self.chunks if version_id == self.version.id else []

    async def get_completed_rule_batch(
        self, document_version_id: str
    ) -> KnowledgeCandidateBatchRecord | None:
        return next(
            (
                batch
                for batch in self.batches
                if batch.document_version_id == document_version_id and batch.status == "completed"
            ),
            None,
        )

    async def create_batch(self, record: KnowledgeCandidateBatchRecord) -> None:
        self.batches.append(record)

    async def create_candidates(self, records: list[KnowledgeCandidateRecord]) -> None:
        self.candidates.extend(records)

    async def list_candidates_by_batch(self, batch_id: str) -> list[KnowledgeCandidateRecord]:
        return [candidate for candidate in self.candidates if candidate.batch_id == batch_id]

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


def _principal(*, can_write: bool = True) -> Principal:
    return Principal(
        user_id="018f4cc1-7852-7d5d-8c1c-dbd404e8c101",
        org_id="018f4cc1-7852-7d5d-8c1c-dbd404e8c102",
        session_id="018f4cc1-7852-7d5d-8c1c-dbd404e8c103",
        roles=frozenset({"knowledge_admin"}),
        permissions=frozenset({"knowledge:write"}) if can_write else frozenset(),
    )


def _chunk(source_chunk_id: str, order: int, label: str, content: str) -> DocumentChunkRecord:
    return DocumentChunkRecord(
        id=f"018f4cc1-7852-7d5d-8c1c-dbd404e8c30{order + 1}",
        document_id=_DOCUMENT_ID,
        document_version_id=_VERSION_ID,
        source_chunk_id=source_chunk_id,
        chunk_order=order,
        chunk_type="article",
        heading_path=label,
        clause_label=label,
        content_text=content,
        content_hash_sha256=f"{order + 1:x}" * 64,
        token_count=len(content),
        effective_start=None,
        effective_end=None,
        region_code="440300",
        policy_status="active",
        review_status="draft",
        index_status="pending",
    )


async def test_rule_extraction_creates_traceable_pending_review_candidates() -> None:
    repository = _Repository()
    unit_of_work = _UnitOfWork(repository)
    service = KnowledgeCandidatesService(uow_factory=lambda: unit_of_work)  # type: ignore[arg-type]

    result = await service.create_rule_based_batch(
        _VERSION_ID,
        request_id="request-stage5-candidates",
        principal=_principal(),
    )

    assert result.created is True
    assert result.batch.status == "completed"
    assert result.batch.extraction_method == "rule_based"
    assert result.batch.model_name is None
    assert result.batch.candidate_count == 2
    assert [candidate.review_status for candidate in result.candidates] == [
        "pending_review",
        "pending_review",
    ]
    assert [candidate.source_document_id for candidate in result.candidates] == [
        _DOCUMENT_ID,
        _DOCUMENT_ID,
    ]
    assert [candidate.source_chunk_id for candidate in result.candidates] == [
        "stage5-candidate:1",
        "stage5-candidate:2",
    ]
    assert result.candidates[0].payload["source_url"] == "https://example.invalid/stage5/candidates"
    assert all(candidate.reviewed_by is None for candidate in result.candidates)
    assert all(candidate.reviewed_at is None for candidate in result.candidates)
    assert unit_of_work.committed is True
    assert repository.audit_actions == ["knowledge.candidate_batch.created"]


async def test_rule_extraction_is_idempotent_for_the_same_draft_version() -> None:
    repository = _Repository()
    service = KnowledgeCandidatesService(
        uow_factory=lambda: _UnitOfWork(repository)  # type: ignore[arg-type]
    )

    first = await service.create_rule_based_batch(
        _VERSION_ID, request_id="request-stage5-first", principal=_principal()
    )
    repeated = await service.create_rule_based_batch(
        _VERSION_ID, request_id="request-stage5-repeat", principal=_principal()
    )

    assert first.created is True
    assert repeated.created is False
    assert repeated.batch.id == first.batch.id
    assert len(repository.batches) == 1
    assert len(repository.candidates) == 2


async def test_rule_extraction_rejects_published_version_and_missing_permission() -> None:
    published_repository = _Repository(version_status="published")
    published_service = KnowledgeCandidatesService(
        uow_factory=lambda: _UnitOfWork(published_repository)  # type: ignore[arg-type]
    )
    with pytest.raises(DomainError) as published_error:
        await published_service.create_rule_based_batch(
            _VERSION_ID, request_id="request-stage5-published", principal=_principal()
        )

    draft_repository = _Repository()
    draft_service = KnowledgeCandidatesService(
        uow_factory=lambda: _UnitOfWork(draft_repository)  # type: ignore[arg-type]
    )
    with pytest.raises(DomainError) as permission_error:
        await draft_service.create_rule_based_batch(
            _VERSION_ID,
            request_id="request-stage5-permission",
            principal=_principal(can_write=False),
        )

    assert published_error.value.code == "POLICY_STATUS_CONFLICT"
    assert permission_error.value.code == "AUTH_FORBIDDEN"

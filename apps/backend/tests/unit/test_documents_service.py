from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock

import pytest

from taxmind.modules.documents.application.service import (
    ChunkInput,
    DocumentMetadataInput,
    DocumentsService,
    _canonical_key,
    _validate_chunk_inputs,
    _validate_metadata,
)
from taxmind.modules.documents.domain import (
    DocumentChunkRecord,
    DocumentVersionRecord,
    SourceDocumentRecord,
)
from taxmind.shared.domain.errors import DomainError
from taxmind.shared.domain.principal import Principal

_HASH = "a" * 64


def _metadata(**overrides: object) -> DocumentMetadataInput:
    values: dict[str, object] = {
        "title": "虚构资料标题",
        "doc_no": "TEST-2026-001",
        "doc_type": "announcement",
        "source_level": "A",
        "issuing_authority": "虚构测试机关",
        "region_code": "000000",
        "publish_date": date(2026, 1, 1),
        "effective_start": date(2026, 1, 1),
        "effective_end": None,
        "policy_status": "active",
        "canonical_url": "https://example.invalid/virtual-policy",
    }
    values.update(overrides)
    return DocumentMetadataInput(**values)  # type: ignore[arg-type]


def test_document_metadata_uses_document_number_before_url_for_canonical_key() -> None:
    metadata = _metadata()

    _validate_metadata(metadata)

    assert _canonical_key(metadata) == "虚构测试机关::TEST-2026-001"


def test_document_metadata_rejects_non_https_source() -> None:
    with pytest.raises(DomainError) as error:
        _validate_metadata(_metadata(canonical_url="http://example.invalid/virtual-policy"))

    assert error.value.code == "VALIDATION_FAILED"


def test_document_chunks_reject_duplicate_order_and_invalid_effective_range() -> None:
    chunk = ChunkInput(
        source_chunk_id="virtual:v1:article_1",
        chunk_order=1,
        chunk_type="article",
        heading_path="第一条",
        clause_label="第一条",
        content_text="仅用于测试的虚构条款。",
        content_hash_sha256=_HASH,
        token_count=10,
        effective_start=date(2026, 2, 1),
        effective_end=date(2026, 1, 1),
    )

    with pytest.raises(DomainError) as error:
        _validate_chunk_inputs([chunk, chunk])

    assert error.value.code == "VALIDATION_FAILED"


class _StubUnitOfWork:
    def __init__(self, repository: AsyncMock) -> None:
        self.repository = repository
        self.commit = AsyncMock()

    async def __aenter__(self) -> _StubUnitOfWork:
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


def _principal(*, user_id: str, permission: str) -> Principal:
    return Principal(
        user_id=user_id,
        org_id="018f4cc1-7852-7d5d-8c1c-dbd404e8a102",
        session_id="018f4cc1-7852-7d5d-8c1c-dbd404e8a103",
        roles=frozenset({"knowledge_admin" if permission == "knowledge:write" else "reviewer"}),
        permissions=frozenset({permission}),
    )


async def test_pending_document_requires_different_reviewer_before_publish() -> None:
    now = datetime.now(UTC)
    document = SourceDocumentRecord(
        id="018f4cc1-7852-7d5d-8c1c-dbd404e8a201",
        canonical_key="虚构测试机关::TEST-2026-001",
        title="虚构资料标题",
        doc_no="TEST-2026-001",
        doc_type="announcement",
        source_level="A",
        issuing_authority="虚构测试机关",
        region_code="000000",
        publish_date=date(2026, 1, 1),
        effective_start=date(2026, 1, 1),
        effective_end=None,
        policy_status="active",
        canonical_url="https://example.invalid/virtual-policy",
        current_version_id=None,
        review_status="draft",
        created_by="018f4cc1-7852-7d5d-8c1c-dbd404e8a202",
        created_at=now,
        updated_at=now,
    )
    draft = DocumentVersionRecord(
        id="018f4cc1-7852-7d5d-8c1c-dbd404e8a203",
        document_id=document.id,
        version_no=1,
        captured_at=now,
        source_url=document.canonical_url,
        raw_object_key=None,
        parsed_object_key=None,
        mime_type="text/plain",
        content_hash_sha256=_HASH,
        parse_status="parsed",
        ocr_status="not_required",
        review_status="draft",
        published_at=None,
        supersedes_version_id=None,
        created_by=document.created_by,
    )
    chunk = DocumentChunkRecord(
        id="018f4cc1-7852-7d5d-8c1c-dbd404e8a204",
        document_id=document.id,
        document_version_id=draft.id,
        source_chunk_id="virtual:v1:article_1",
        chunk_order=1,
        chunk_type="article",
        heading_path="第一条",
        clause_label="第一条",
        content_text="仅用于测试的虚构条款。",
        content_hash_sha256=_HASH,
        token_count=10,
        effective_start=date(2026, 1, 1),
        effective_end=None,
        region_code="000000",
        policy_status="active",
        review_status="draft",
        index_status="pending",
    )
    repository = AsyncMock()
    repository.get_document.return_value = document
    repository.get_version.return_value = draft
    repository.list_chunks.return_value = [chunk]
    uow = _StubUnitOfWork(repository)
    service = DocumentsService(uow_factory=lambda: uow)  # type: ignore[arg-type]
    author = _principal(user_id=document.created_by, permission="knowledge:write")

    pending = await service.submit_review(draft.id, request_id="request-1", principal=author)

    assert pending.version.review_status == "pending_review"
    repository.set_pending_review.assert_awaited_once()

    repository.get_version.return_value = replace(draft, review_status="pending_review")
    self_reviewer = _principal(user_id=document.created_by, permission="knowledge:review")
    with pytest.raises(DomainError) as error:
        await service.publish(draft.id, request_id="request-2", principal=self_reviewer)
    assert error.value.code == "AUTH_FORBIDDEN"

    reviewer = _principal(
        user_id="018f4cc1-7852-7d5d-8c1c-dbd404e8a205", permission="knowledge:review"
    )
    published = await service.publish(draft.id, request_id="request-3", principal=reviewer)

    assert published.version.review_status == "published"
    repository.publish.assert_awaited_once()

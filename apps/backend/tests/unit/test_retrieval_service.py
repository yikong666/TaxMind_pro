from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from taxmind.modules.documents.domain import (
    DocumentChunkRecord,
    DocumentVersionRecord,
    PolicyEvidence,
    SourceDocumentRecord,
)
from taxmind.modules.retrieval.application.service import (
    PolicyRetrievalService,
    RetrievalUnavailable,
)
from taxmind.modules.retrieval.domain import PolicyEvidenceCandidate, PolicyRetrievalRequest
from taxmind.modules.retrieval.infrastructure.mysql_exact import MySqlPolicyExactSearchAdapter


def _evidence() -> PolicyEvidence:
    now = datetime(2026, 8, 31, tzinfo=UTC)
    document = SourceDocumentRecord(
        id="document-1",
        canonical_key="guangdong-policy-1",
        title="小微企业税收优惠",
        doc_no="GD-TAX-2026-1",
        doc_type="policy",
        source_level="provincial",
        issuing_authority="广东省税务局",
        region_code="440000",
        publish_date=date(2026, 1, 1),
        effective_start=date(2026, 1, 1),
        effective_end=None,
        policy_status="active",
        canonical_url="https://example.invalid/policy-1",
        current_version_id="version-1",
        review_status="published",
        created_by="reviewer-1",
        created_at=now,
        updated_at=now,
    )
    version = DocumentVersionRecord(
        id="version-1",
        document_id=document.id,
        version_no=1,
        captured_at=now,
        source_url=document.canonical_url,
        raw_object_key=None,
        parsed_object_key=None,
        mime_type="text/html",
        content_hash_sha256="a" * 64,
        parse_status="succeeded",
        ocr_status="not_required",
        review_status="published",
        published_at=now,
        supersedes_version_id=None,
        created_by="reviewer-1",
    )
    chunk = DocumentChunkRecord(
        id="chunk-1",
        document_id=document.id,
        document_version_id=version.id,
        source_chunk_id="source-chunk-1",
        chunk_order=1,
        chunk_type="body",
        heading_path="第一条",
        clause_label=None,
        content_text="小微企业所得税优惠",
        content_hash_sha256="b" * 64,
        token_count=12,
        effective_start=date(2026, 1, 1),
        effective_end=None,
        region_code="440300",
        policy_status="active",
        review_status="published",
        index_status="ready",
    )
    return PolicyEvidence(document=document, version=version, chunk=chunk, region_match="local")


class _DocumentsRepository:
    async def search_published(self, **_: object) -> list[PolicyEvidence]:
        return [_evidence()]


class _UnavailableSemanticSearch:
    async def search(
        self, _: PolicyRetrievalRequest, *, limit: int
    ) -> list[PolicyEvidenceCandidate]:
        raise RetrievalUnavailable("milvus is unavailable")


@pytest.mark.asyncio
async def test_mysql_exact_evidence_is_returned_when_semantic_retrieval_is_unavailable() -> None:
    request = PolicyRetrievalRequest(
        query="小微企业", region_code="440300", business_date=date(2026, 8, 31)
    )
    service = PolicyRetrievalService(
        exact_search=MySqlPolicyExactSearchAdapter(repository=_DocumentsRepository()),
        semantic_search=_UnavailableSemanticSearch(),
    )

    result = await service.search(request, limit=5)

    assert result.degraded is True
    assert result.degradation_reason == "semantic_retrieval_unavailable"
    assert result.exact_candidates[0].chunk_id == "chunk-1"
    assert result.exact_candidates[0].source_url == "https://example.invalid/policy-1"

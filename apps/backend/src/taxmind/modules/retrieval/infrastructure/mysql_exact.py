from __future__ import annotations

from datetime import date
from typing import Protocol

from taxmind.modules.documents.domain import PolicyEvidence
from taxmind.modules.retrieval.domain import PolicyEvidenceCandidate, PolicyRetrievalRequest


class PublishedPolicySearchRepository(Protocol):
    async def search_published(
        self, *, query: str, region_code: str, business_date: date, limit: int
    ) -> list[PolicyEvidence]: ...


class MySqlPolicyExactSearchAdapter:
    """Maps already-authoritative MySQL evidence into retrieval candidates."""

    def __init__(self, *, repository: PublishedPolicySearchRepository) -> None:
        self._repository = repository

    async def search(
        self, request: PolicyRetrievalRequest, *, limit: int
    ) -> list[PolicyEvidenceCandidate]:
        evidence = await self._repository.search_published(
            query=request.query,
            region_code=request.region_code,
            business_date=request.business_date,
            limit=limit,
        )
        return [
            PolicyEvidenceCandidate(
                chunk_id=item.chunk.id,
                document_version_id=item.version.id,
                source_url=item.version.source_url,
                region_match=item.region_match,
                policy_status=item.chunk.policy_status,
                review_status=item.chunk.review_status,
                retrieval_reason="mysql_exact",
            )
            for item in evidence
        ]

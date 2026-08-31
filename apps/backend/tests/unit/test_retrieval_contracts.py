from __future__ import annotations

from datetime import date

import pytest

from taxmind.modules.retrieval.domain import PolicyEvidenceCandidate, PolicyRetrievalRequest


def test_policy_retrieval_request_requires_query_region_and_business_date() -> None:
    request = PolicyRetrievalRequest(
        query="小微企业所得税优惠", region_code="440300", business_date=date(2026, 8, 31)
    )
    assert request.region_code == "440300"

    with pytest.raises(ValueError, match="region"):
        PolicyRetrievalRequest(
            query="小微企业所得税优惠", region_code="", business_date=date(2026, 8, 31)
        )


def test_evidence_candidate_rejects_unpublished_or_inactive_policy() -> None:
    with pytest.raises(ValueError, match="active"):
        PolicyEvidenceCandidate(
            chunk_id="chunk-1",
            document_version_id="version-1",
            source_url="https://example.invalid/1",
            region_match="local",
            policy_status="retired",
            review_status="published",
            retrieval_reason="exact",
        )

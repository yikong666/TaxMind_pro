from __future__ import annotations

from datetime import date

import pytest

from taxmind.modules.retrieval.domain import PolicyRetrievalRequest
from taxmind.modules.retrieval.infrastructure.milvus_policy import MilvusPolicySearchAdapter


class _Embedder:
    async def embed_query(self, _: str) -> list[float]:
        return [0.2, 0.8]


class _MilvusClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def search(self, **kwargs: object) -> list[list[dict[str, object]]]:
        self.calls.append(kwargs)
        return [
            [
                {
                    "entity": {
                        "chunk_id": "chunk-semantic-1",
                        "document_version_id": "version-1",
                        "source_url": "https://example.invalid/policy-1",
                        "region_code": "440300",
                        "policy_status": "active",
                        "review_status": "published",
                    }
                }
            ]
        ]


@pytest.mark.asyncio
async def test_milvus_search_uses_scope_gate_and_returns_traceable_candidate() -> None:
    client = _MilvusClient()
    adapter = MilvusPolicySearchAdapter(
        client=client,
        embedder=_Embedder(),
        collection_name="policy_chunks_current",
    )

    candidates = await adapter.search(
        PolicyRetrievalRequest(
            query="小微企业", region_code="440300", business_date=date(2026, 8, 31)
        ),
        limit=3,
    )

    assert candidates[0].chunk_id == "chunk-semantic-1"
    assert candidates[0].retrieval_reason == "milvus_semantic"
    assert client.calls[0]["limit"] == 3
    filter_expression = str(client.calls[0]["filter"])
    assert 'review_status == "published"' in filter_expression
    assert 'policy_status == "active"' in filter_expression
    assert 'region_code in ["440300", "000000"]' in filter_expression
    assert 'effective_start <= "2026-08-31"' in filter_expression
    assert 'effective_end >= "2026-08-31"' in filter_expression

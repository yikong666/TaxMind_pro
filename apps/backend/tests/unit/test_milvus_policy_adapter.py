from __future__ import annotations

from taxmind.infrastructure.projections.contracts import PolicyChunkProjectionRecord
from taxmind.infrastructure.projections.milvus_policy import MilvusPolicyProjectionAdapter


class _Client:
    def __init__(self) -> None:
        self.upserts: list[tuple[str, list[dict[str, object]]]] = []

    def upsert(self, collection_name: str, data: list[dict[str, object]]) -> dict[str, int]:
        self.upserts.append((collection_name, data))
        return {"upsert_count": len(data)}


async def test_milvus_adapter_writes_versioned_snapshot_records_idempotently() -> None:
    client = _Client()
    adapter = MilvusPolicyProjectionAdapter(client=client, collection_name="policy_chunks_v1")
    record = PolicyChunkProjectionRecord(
        snapshot_id="snapshot-1",
        snapshot_code="public-1",
        chunk_id="chunk-1",
        source_chunk_id="doc-1:1",
        document_id="document-1",
        document_version_id="version-1",
        source_url="https://example.invalid/policy/1",
        region_code="440300",
        effective_start=None,
        effective_end=None,
        policy_status="active",
        review_status="published",
        content_hash="a" * 64,
        embedding_version="pending-v1",
        dense_vector=(0.1, 0.2),
    )

    result = await adapter.upsert_policy_snapshot([record], idempotency_key="snapshot-1:a" * 32)

    assert result.status == "succeeded"
    assert result.projected_count == 1
    assert client.upserts[0][0] == "policy_chunks_v1"
    assert client.upserts[0][1][0]["snapshot_id"] == "snapshot-1"
    assert client.upserts[0][1][0]["content_hash"] == "a" * 64
    assert client.upserts[0][1][0]["dense_vector"] == [0.1, 0.2]

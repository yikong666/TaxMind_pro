from __future__ import annotations

from taxmind.infrastructure.projections.contracts import PolicyChunkProjectionRecord
from taxmind.infrastructure.projections.milvus_smoke import MilvusSnapshotSmokeVerifier
from taxmind.modules.knowledge.application.projection_payload_service import (
    SnapshotProjectionPayload,
)
from taxmind.modules.knowledge.domain import KnowledgeSnapshotRecord


class _Loader:
    async def load(self, snapshot_id: str) -> SnapshotProjectionPayload:
        return SnapshotProjectionPayload(policy_records=[_record(snapshot_id)], graph_records=[])


class _Client:
    def get(self, collection_name: str, ids: list[str]) -> list[dict[str, object]]:
        assert collection_name == "policy_chunks_v1"
        assert ids == ["chunk-1"]
        return [{"chunk_id": "chunk-1", "snapshot_id": "snapshot-1"}]


async def test_smoke_verifier_requires_sample_record_to_match_snapshot() -> None:
    assert await MilvusSnapshotSmokeVerifier(
        loader=_Loader(), client=_Client(), collection_name="policy_chunks_v1"
    ).verify(_snapshot())


def _snapshot() -> KnowledgeSnapshotRecord:
    from datetime import UTC, datetime

    return KnowledgeSnapshotRecord(
        id="snapshot-1",
        org_id=None,
        snapshot_code="public-1",
        snapshot_type="public",
        status="pending_activation",
        base_snapshot_id=None,
        description="test",
        manifest_hash="a" * 64,
        activated_at=None,
        activated_by=None,
        created_at=datetime(2026, 8, 31, tzinfo=UTC),
    )


def _record(snapshot_id: str) -> PolicyChunkProjectionRecord:
    return PolicyChunkProjectionRecord(
        snapshot_id=snapshot_id,
        snapshot_code="public-1",
        chunk_id="chunk-1",
        source_chunk_id="d:1",
        document_id="document-1",
        document_version_id="version-1",
        source_url="https://example.invalid/1",
        region_code="440300",
        effective_start=None,
        effective_end=None,
        policy_status="active",
        review_status="published",
        content_hash="b" * 64,
        embedding_version="v1",
        dense_vector=(0.1, 0.2),
    )

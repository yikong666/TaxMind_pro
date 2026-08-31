from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import cast

from taxmind.modules.knowledge.application.projection_payload_service import (
    ProjectionPayloadUowFactory,
    SnapshotProjectionPayloadLoader,
    SnapshotProjectionPayloadService,
)
from taxmind.modules.knowledge.domain import (
    KnowledgeCandidateRecord,
    KnowledgeSnapshotRecord,
    SnapshotProjectionCandidateRecord,
)

_NOW = datetime(2026, 8, 31, tzinfo=UTC)


class _Embedding:
    async def embed(self, text: str) -> tuple[float, ...]:
        assert text == "第一条 虚构政策条款。"
        return (0.1, 0.2)


class _Repository:
    async def get_snapshot(
        self, snapshot_id: str, *, lock: bool = False
    ) -> KnowledgeSnapshotRecord | None:
        del lock
        return _snapshot() if snapshot_id == "snapshot-1" else None

    async def list_snapshot_projection_candidates(
        self, snapshot_id: str
    ) -> list[SnapshotProjectionCandidateRecord]:
        return (
            [
                SnapshotProjectionCandidateRecord(
                    candidate=_candidate(), document_version_id="version-1"
                )
            ]
            if snapshot_id == "snapshot-1"
            else []
        )


class _Uow:
    repository = _Repository()

    async def __aenter__(self) -> _Uow:
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


async def test_builds_traceable_policy_and_graph_records_from_snapshot_candidates() -> None:
    result = await SnapshotProjectionPayloadService(embedding=_Embedding()).build(
        _snapshot(),
        [
            SnapshotProjectionCandidateRecord(
                candidate=_candidate(), document_version_id="version-1"
            )
        ],
    )

    assert result.policy_records[0].snapshot_id == "snapshot-1"
    assert result.policy_records[0].review_status == "published"
    assert result.policy_records[0].source_chunk_id == "doc-1:1"
    assert result.policy_records[0].document_version_id == "version-1"
    assert result.policy_records[0].dense_vector == (0.1, 0.2)
    assert result.graph_records[0].relation_type == "DOCUMENT_CONTAINS_CLAUSE"
    assert result.graph_records[0].source_url == "https://example.invalid/policy/1"


async def test_loader_reads_pending_snapshot_and_its_controlled_candidates() -> None:
    result = await SnapshotProjectionPayloadLoader(
        uow_factory=cast(ProjectionPayloadUowFactory, lambda: _Uow()),
        payload_service=SnapshotProjectionPayloadService(embedding=_Embedding()),
    ).load("snapshot-1")

    assert len(result.policy_records) == 1


def _snapshot() -> KnowledgeSnapshotRecord:
    return KnowledgeSnapshotRecord(
        id="snapshot-1",
        org_id=None,
        snapshot_code="public-test",
        snapshot_type="public",
        status="pending_activation",
        base_snapshot_id=None,
        description="虚构快照",
        manifest_hash="a" * 64,
        activated_at=None,
        activated_by=None,
        created_at=_NOW,
    )


def _candidate() -> KnowledgeCandidateRecord:
    return KnowledgeCandidateRecord(
        id="candidate-1",
        batch_id="batch-1",
        candidate_type="policy_clause",
        payload={
            "source_url": "https://example.invalid/policy/1",
            "region_code": "440300",
            "policy_status": "active",
            "effective_start": "2026-01-01",
            "effective_end": None,
            "text_excerpt": "第一条 虚构政策条款。",
        },
        source_document_id="document-1",
        source_chunk_id="doc-1:1",
        extraction_method="rule_based",
        extraction_confidence=Decimal("0.9500"),
        normalization_status="not_required",
        review_status="approved",
        review_reason_safe=None,
        reviewed_by="reviewer",
        reviewed_at=_NOW,
        content_hash="b" * 64,
        created_at=_NOW,
    )

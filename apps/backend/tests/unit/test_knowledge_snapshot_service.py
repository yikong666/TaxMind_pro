from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

import pytest

from taxmind.modules.knowledge.application.snapshot_service import (
    KnowledgeSnapshotService,
    SnapshotUowFactory,
)
from taxmind.modules.knowledge.domain import (
    KnowledgeCandidateRecord,
    KnowledgePublishBatchRecord,
    KnowledgeSnapshotItemRecord,
    KnowledgeSnapshotRecord,
    OutboxEventRecord,
)
from taxmind.shared.domain.errors import DomainError
from taxmind.shared.domain.principal import Principal

_NOW = datetime(2026, 8, 31, tzinfo=UTC)
_BATCH_ID = "018f4cc1-7852-7d5d-8c1c-dbd404e8f201"


class _Repository:
    def __init__(self, *, status: str = "validated") -> None:
        self.batch = KnowledgePublishBatchRecord(
            id=_BATCH_ID,
            batch_type="knowledge_candidate",
            scope="public",
            org_id=None,
            status=status,
            candidate_count=1,
            approved_count=1,
            rejected_count=0,
            validation_report={"passed": status == "validated"},
            manifest_hash="a" * 64,
            submitted_by="018f4cc1-7852-7d5d-8c1c-dbd404e8f101",
            approved_by=None,
            submitted_at=_NOW,
            published_at=None,
            created_at=_NOW,
        )
        self.candidates = [
            KnowledgeCandidateRecord(
                id="018f4cc1-7852-7d5d-8c1c-dbd404e8f301",
                batch_id=_BATCH_ID,
                candidate_type="policy_clause",
                payload={},
                source_document_id="doc-1",
                source_chunk_id="chunk-1",
                extraction_method="rule_based",
                extraction_confidence=__import__("decimal").Decimal("0.9500"),
                normalization_status="not_required",
                review_status="approved",
                review_reason_safe=None,
                reviewed_by="reviewer",
                reviewed_at=_NOW,
                content_hash="b" * 64,
                created_at=_NOW,
            )
        ]
        self.snapshot: KnowledgeSnapshotRecord | None = None
        self.items: list[KnowledgeSnapshotItemRecord] = []
        self.events: list[OutboxEventRecord] = []
        self.audit_actions: list[str] = []

    async def get_publish_batch(self, batch_id: str, *, lock: bool = False) -> object | None:
        del lock
        return self.batch if batch_id == self.batch.id else None

    async def list_publish_candidates(self, batch_id: str) -> list[KnowledgeCandidateRecord]:
        return self.candidates if batch_id == self.batch.id else []

    async def create_snapshot(self, record: KnowledgeSnapshotRecord) -> None:
        self.snapshot = record

    async def flush(self) -> None:
        return None

    async def create_snapshot_items(self, records: list[KnowledgeSnapshotItemRecord]) -> None:
        self.items.extend(records)

    async def create_outbox_events(self, records: list[OutboxEventRecord]) -> None:
        self.events.extend(records)

    async def create_audit_log(self, **kwargs: object) -> None:
        self.audit_actions.append(str(kwargs["action_code"]))


class _Uow:
    def __init__(self, repository: _Repository) -> None:
        self.repository = repository

    async def __aenter__(self) -> _Uow:
        return self

    async def commit(self) -> None:
        return None

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


def _principal() -> Principal:
    return Principal(
        user_id="reviewer",
        org_id="org",
        session_id="session",
        roles=frozenset({"knowledge_reviewer"}),
        permissions=frozenset({"knowledge:review"}),
    )


async def test_validated_batch_materializes_pending_snapshot_and_two_outbox_events() -> None:
    repository = _Repository()
    result = await KnowledgeSnapshotService(
        uow_factory=cast(SnapshotUowFactory, lambda: _Uow(repository))
    ).materialize_validated_batch(_BATCH_ID, request_id="stage5-snapshot", principal=_principal())
    assert result.snapshot.status == "pending_activation"
    assert result.snapshot.activated_at is None
    assert len(repository.items) == 1
    assert {event.event_type for event in repository.events} == {
        "projection.policy_snapshot.requested",
        "projection.graph_snapshot.requested",
    }
    assert all(event.status == "pending" for event in repository.events)
    assert repository.audit_actions == ["knowledge.snapshot.materialized"]


async def test_non_validated_batch_cannot_materialize_snapshot() -> None:
    with pytest.raises(DomainError) as error:
        await KnowledgeSnapshotService(
            uow_factory=cast(
                SnapshotUowFactory, lambda: _Uow(_Repository(status="pending_validation"))
            )
        ).materialize_validated_batch(
            _BATCH_ID, request_id="stage5-invalid", principal=_principal()
        )
    assert error.value.code == "POLICY_STATUS_CONFLICT"

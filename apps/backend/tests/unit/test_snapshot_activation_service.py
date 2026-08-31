from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

import pytest

from taxmind.modules.knowledge.application.activation_service import (
    KnowledgeSnapshotActivationService,
    ProjectionSmokeVerifier,
    SnapshotActivationUowFactory,
)
from taxmind.modules.knowledge.domain import KnowledgeSnapshotRecord, ProjectionSyncStateRecord
from taxmind.shared.domain.errors import DomainError
from taxmind.shared.domain.principal import Principal

_NOW = datetime(2026, 8, 31, tzinfo=UTC)
_SNAPSHOT_ID = "018f4cc1-7852-7d5d-8c1c-dbd404e8f401"
_MANIFEST_HASH = "a" * 64


class _Repository:
    def __init__(self, *, graph_status: str = "succeeded") -> None:
        self.snapshot = KnowledgeSnapshotRecord(
            id=_SNAPSHOT_ID,
            org_id=None,
            snapshot_code="public-stage64",
            snapshot_type="public",
            status="pending_activation",
            base_snapshot_id=None,
            description="虚构阶段六快照",
            manifest_hash=_MANIFEST_HASH,
            activated_at=None,
            activated_by=None,
            created_at=_NOW,
        )
        self.states = [
            _sync_state("milvus_policy", "succeeded"),
            _sync_state("neo4j_graph", graph_status),
        ]
        self.audit_actions: list[str] = []

    async def get_snapshot(self, snapshot_id: str, *, lock: bool = False) -> object | None:
        del lock
        return self.snapshot if snapshot_id == self.snapshot.id else None

    async def list_projection_sync_states(
        self, snapshot_id: str
    ) -> list[ProjectionSyncStateRecord]:
        return self.states if snapshot_id == self.snapshot.id else []

    async def activate_snapshot(self, record: KnowledgeSnapshotRecord) -> None:
        self.snapshot = record

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


class _Verifier:
    def __init__(self, *, passed: bool) -> None:
        self._passed = passed

    async def verify(self, snapshot: KnowledgeSnapshotRecord) -> bool:
        return self._passed and snapshot.id == _SNAPSHOT_ID


def _sync_state(projection_type: str, status: str) -> ProjectionSyncStateRecord:
    return ProjectionSyncStateRecord(
        id=f"state-{projection_type}",
        projection_type=projection_type,
        aggregate_type="knowledge_snapshot",
        aggregate_id=_SNAPSHOT_ID,
        source_version=_MANIFEST_HASH,
        target_version="adapter-managed",
        status=status,
        last_event_id=f"event-{projection_type}",
        synced_at=_NOW if status == "succeeded" else None,
        error_safe=None,
        updated_at=_NOW,
    )


def _principal() -> Principal:
    return Principal(
        user_id="reviewer",
        org_id="org",
        session_id="session",
        roles=frozenset({"knowledge_reviewer"}),
        permissions=frozenset({"knowledge:review"}),
    )


async def test_activation_requires_successful_projection_states_and_sample_check() -> None:
    repository = _Repository()
    result = await KnowledgeSnapshotActivationService(
        uow_factory=cast(SnapshotActivationUowFactory, lambda: _Uow(repository)),
        projection_smoke_verifier=cast(ProjectionSmokeVerifier, _Verifier(passed=True)),
        clock=lambda: _NOW,
    ).activate_snapshot(_SNAPSHOT_ID, request_id="stage64-activate", principal=_principal())

    assert result.snapshot.status == "active"
    assert result.snapshot.activated_at == _NOW
    assert result.snapshot.activated_by == "reviewer"
    assert repository.audit_actions == ["knowledge.snapshot.activated"]


async def test_activation_keeps_snapshot_pending_when_a_projection_has_not_succeeded() -> None:
    repository = _Repository(graph_status="retryable")

    with pytest.raises(DomainError) as error:
        await KnowledgeSnapshotActivationService(
            uow_factory=cast(SnapshotActivationUowFactory, lambda: _Uow(repository)),
            projection_smoke_verifier=cast(ProjectionSmokeVerifier, _Verifier(passed=True)),
            clock=lambda: _NOW,
        ).activate_snapshot(_SNAPSHOT_ID, request_id="stage64-blocked", principal=_principal())

    assert error.value.code == "POLICY_STATUS_CONFLICT"
    assert repository.snapshot.status == "pending_activation"
    assert repository.snapshot.activated_at is None


async def test_activation_keeps_snapshot_pending_when_sample_check_fails() -> None:
    repository = _Repository()

    with pytest.raises(DomainError) as error:
        await KnowledgeSnapshotActivationService(
            uow_factory=cast(SnapshotActivationUowFactory, lambda: _Uow(repository)),
            projection_smoke_verifier=cast(ProjectionSmokeVerifier, _Verifier(passed=False)),
            clock=lambda: _NOW,
        ).activate_snapshot(
            _SNAPSHOT_ID, request_id="stage64-sample-failed", principal=_principal()
        )

    assert error.value.code == "POLICY_STATUS_CONFLICT"
    assert repository.snapshot.status == "pending_activation"

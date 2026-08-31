from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol

from taxmind.modules.knowledge.domain import KnowledgeSnapshotRecord, ProjectionSyncStateRecord
from taxmind.modules.knowledge.infrastructure.uow import SqlAlchemyKnowledgeUnitOfWork
from taxmind.shared.domain.errors import DomainError
from taxmind.shared.domain.principal import Principal

_REQUIRED_PROJECTIONS = frozenset({"milvus_policy", "neo4j_graph"})


class SnapshotActivationUowFactory(Protocol):
    def __call__(self) -> SqlAlchemyKnowledgeUnitOfWork: ...


class ProjectionSmokeVerifier(Protocol):
    """Checks a small, controlled projection sample before snapshot activation."""

    async def verify(self, snapshot: KnowledgeSnapshotRecord) -> bool: ...


class SnapshotActivationResult:
    def __init__(self, snapshot: KnowledgeSnapshotRecord) -> None:
        self.snapshot = snapshot


class KnowledgeSnapshotActivationService:
    def __init__(
        self,
        *,
        uow_factory: SnapshotActivationUowFactory,
        projection_smoke_verifier: ProjectionSmokeVerifier,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._projection_smoke_verifier = projection_smoke_verifier
        self._clock = clock or (lambda: datetime.now(UTC))

    async def activate_snapshot(
        self, snapshot_id: str, *, request_id: str, principal: Principal
    ) -> SnapshotActivationResult:
        if not principal.has_permission("knowledge:review"):
            raise DomainError(code="AUTH_FORBIDDEN", message="当前角色无知识审核权限")
        async with self._uow_factory() as uow:
            repository = uow.repository
            if repository is None:
                raise RuntimeError("unit of work repository is unavailable")
            snapshot = await repository.get_snapshot(snapshot_id, lock=True)
            if snapshot is None:
                raise DomainError(code="RESOURCE_NOT_FOUND", message="知识快照不存在")
            if snapshot.status != "pending_activation":
                raise DomainError(
                    code="POLICY_STATUS_CONFLICT", message="仅待激活知识快照可执行激活"
                )
            states = await repository.list_projection_sync_states(snapshot.id)
            if not _has_completed_required_projections(snapshot, states):
                raise DomainError(
                    code="POLICY_STATUS_CONFLICT", message="知识投影尚未全部成功, 不能激活快照"
                )
            if not await self._projection_smoke_verifier.verify(snapshot):
                raise DomainError(
                    code="POLICY_STATUS_CONFLICT", message="知识投影抽样校验未通过, 不能激活快照"
                )
            now = self._clock()
            activated_snapshot = KnowledgeSnapshotRecord(
                id=snapshot.id,
                org_id=snapshot.org_id,
                snapshot_code=snapshot.snapshot_code,
                snapshot_type=snapshot.snapshot_type,
                status="active",
                base_snapshot_id=snapshot.base_snapshot_id,
                description=snapshot.description,
                manifest_hash=snapshot.manifest_hash,
                activated_at=now,
                activated_by=principal.user_id,
                created_at=snapshot.created_at,
            )
            await repository.activate_snapshot(activated_snapshot)
            await repository.create_audit_log(
                org_id=principal.org_id,
                actor_user_id=principal.user_id,
                action_code="knowledge.snapshot.activated",
                resource_type="knowledge_snapshot",
                resource_id=snapshot.id,
                request_id=request_id,
                occurred_at=now,
            )
            await uow.commit()
            return SnapshotActivationResult(activated_snapshot)


def _has_completed_required_projections(
    snapshot: KnowledgeSnapshotRecord, states: list[ProjectionSyncStateRecord]
) -> bool:
    succeeded = {
        state.projection_type
        for state in states
        if state.aggregate_type == "knowledge_snapshot"
        and state.aggregate_id == snapshot.id
        and state.source_version == snapshot.manifest_hash
        and state.target_version == "adapter-managed"
        and state.status == "succeeded"
    }
    return succeeded == _REQUIRED_PROJECTIONS

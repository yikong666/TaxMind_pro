from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from taxmind.modules.knowledge.domain import (
    KnowledgeSnapshotItemRecord,
    KnowledgeSnapshotRecord,
    OutboxEventRecord,
)
from taxmind.modules.knowledge.infrastructure.uow import SqlAlchemyKnowledgeUnitOfWork
from taxmind.shared.domain.errors import DomainError
from taxmind.shared.domain.ids import new_id
from taxmind.shared.domain.principal import Principal


class SnapshotUowFactory(Protocol):
    def __call__(self) -> SqlAlchemyKnowledgeUnitOfWork: ...


class MaterializedSnapshot:
    def __init__(self, snapshot: KnowledgeSnapshotRecord, events: list[OutboxEventRecord]) -> None:
        self.snapshot = snapshot
        self.events = events


class KnowledgeSnapshotService:
    def __init__(self, *, uow_factory: SnapshotUowFactory) -> None:
        self._uow_factory = uow_factory

    async def materialize_validated_batch(
        self, batch_id: str, *, request_id: str, principal: Principal
    ) -> MaterializedSnapshot:
        if not principal.has_permission("knowledge:review"):
            raise DomainError(code="AUTH_FORBIDDEN", message="当前角色无知识审核权限")
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            repo = uow.repository
            if repo is None:
                raise RuntimeError("unit of work repository is unavailable")
            batch = await repo.get_publish_batch(batch_id, lock=True)
            if batch is None:
                raise DomainError(code="RESOURCE_NOT_FOUND", message="发布批次不存在")
            if batch.status != "validated" or batch.validation_report.get("passed") is not True:
                raise DomainError(
                    code="POLICY_STATUS_CONFLICT", message="仅验证通过的发布批次可物化快照"
                )
            candidates = await repo.list_publish_candidates(batch.id)
            if len(candidates) != batch.candidate_count:
                raise DomainError(code="POLICY_STATUS_CONFLICT", message="发布批次候选清单不完整")
            snapshot = KnowledgeSnapshotRecord(
                id=new_id(),
                org_id=None,
                snapshot_code=f"public-{batch.id[:8]}",
                snapshot_type="public",
                status="pending_activation",
                base_snapshot_id=None,
                description=f"发布批次 {batch.id} 的待激活快照",
                manifest_hash=batch.manifest_hash or "",
                activated_at=None,
                activated_by=None,
                created_at=now,
            )
            items = [
                KnowledgeSnapshotItemRecord(
                    id=new_id(),
                    snapshot_id=snapshot.id,
                    item_type="policy_clause",
                    item_id=c.id,
                    item_version=c.batch_id,
                    checksum=c.content_hash,
                )
                for c in candidates
            ]
            events = [
                OutboxEventRecord(
                    id=new_id(),
                    aggregate_type="knowledge_snapshot",
                    aggregate_id=snapshot.id,
                    event_type=event_type,
                    payload={
                        "snapshot_id": snapshot.id,
                        "publish_batch_id": batch.id,
                        "manifest_hash": snapshot.manifest_hash,
                    },
                    dedupe_key=f"{event_type}:{snapshot.id}",
                    status="pending",
                    attempt_count=0,
                    next_attempt_at=None,
                    locked_by=None,
                    locked_at=None,
                    last_error_safe=None,
                    created_at=now,
                    updated_at=now,
                )
                for event_type in (
                    "projection.policy_snapshot.requested",
                    "projection.graph_snapshot.requested",
                )
            ]
            await repo.create_snapshot(snapshot)
            await repo.flush()
            await repo.create_snapshot_items(items)
            await repo.create_outbox_events(events)
            await repo.create_audit_log(
                org_id=principal.org_id,
                actor_user_id=principal.user_id,
                action_code="knowledge.snapshot.materialized",
                resource_id=snapshot.id,
                request_id=request_id,
                occurred_at=now,
            )
            await uow.commit()
            return MaterializedSnapshot(snapshot, events)

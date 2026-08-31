from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Protocol

from taxmind.modules.knowledge.domain import OutboxEventRecord, ProjectionSyncStateRecord
from taxmind.modules.knowledge.infrastructure.repository import SqlAlchemyKnowledgeRepository
from taxmind.modules.knowledge.infrastructure.uow import SqlAlchemyKnowledgeUnitOfWork
from taxmind.shared.domain.ids import new_id


class OutboxDispatchUowFactory(Protocol):
    def __call__(self) -> SqlAlchemyKnowledgeUnitOfWork: ...


class ProjectionExecutor(Protocol):
    async def execute(self, event: OutboxEventRecord) -> None: ...


class ProjectionExecutionError(Exception):
    def __init__(self, safe_code: str) -> None:
        super().__init__(safe_code)
        self.safe_code = safe_code


class OutboxDispatchResult:
    def __init__(
        self, *, claimed_count: int, completed_count: int, retryable_count: int, dead_count: int
    ) -> None:
        self.claimed_count = claimed_count
        self.completed_count = completed_count
        self.retryable_count = retryable_count
        self.dead_count = dead_count


class OutboxDispatchService:
    def __init__(
        self,
        *,
        uow_factory: OutboxDispatchUowFactory,
        projection_executor: ProjectionExecutor,
        max_attempts: int,
        retry_delay_seconds: int,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._projection_executor = projection_executor
        self._max_attempts = max_attempts
        self._retry_delay_seconds = retry_delay_seconds
        self._clock = clock or (lambda: datetime.now(UTC))
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if retry_delay_seconds < 1:
            raise ValueError("retry_delay_seconds must be at least 1")

    async def dispatch_once(self, *, limit: int, worker_id: str) -> OutboxDispatchResult:
        if limit < 1:
            raise ValueError("limit must be at least 1")
        if not worker_id.strip():
            raise ValueError("worker_id is required")
        now = self._clock()
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            events = await repository.claim_outbox_events(
                limit=limit,
                worker_id=worker_id,
                now=now,
            )
            await uow.commit()

        completed_count = 0
        retryable_count = 0
        dead_count = 0
        for event in events:
            try:
                await self._projection_executor.execute(event)
            except ProjectionExecutionError as error:
                if await self._record_failure(event, error.safe_code):
                    dead_count += 1
                else:
                    retryable_count += 1
            except Exception:
                if await self._record_failure(event, "PROJECTION_EXECUTION_FAILED"):
                    dead_count += 1
                else:
                    retryable_count += 1
            else:
                await self._record_success(event)
                completed_count += 1
        return OutboxDispatchResult(
            claimed_count=len(events),
            completed_count=completed_count,
            retryable_count=retryable_count,
            dead_count=dead_count,
        )

    async def _record_success(self, event: OutboxEventRecord) -> None:
        now = self._clock()
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            await repository.mark_outbox_done(event.id, now=now)
            await repository.upsert_projection_sync_state(
                _sync_state(event, status="succeeded", error_safe=None, now=now)
            )
            await uow.commit()

    async def _record_failure(self, event: OutboxEventRecord, safe_error: str) -> bool:
        now = self._clock()
        attempt_number = event.attempt_count + 1
        is_dead = attempt_number >= self._max_attempts
        next_attempt_at = (
            None if is_dead else now + timedelta(seconds=self._retry_delay_seconds * attempt_number)
        )
        status = "dead" if is_dead else "retryable"
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            await repository.mark_outbox_failed(
                event.id,
                status=status,
                safe_error=safe_error,
                next_attempt_at=next_attempt_at,
                now=now,
            )
            await repository.upsert_projection_sync_state(
                _sync_state(event, status=status, error_safe=safe_error, now=now)
            )
            await uow.commit()
        return is_dead


def _repository(uow: SqlAlchemyKnowledgeUnitOfWork) -> SqlAlchemyKnowledgeRepository:
    if uow.repository is None:
        raise RuntimeError("unit of work repository is unavailable")
    return uow.repository


def _sync_state(
    event: OutboxEventRecord, *, status: str, error_safe: str | None, now: datetime
) -> ProjectionSyncStateRecord:
    projection_type = {
        "projection.policy_snapshot.requested": "milvus_policy",
        "projection.graph_snapshot.requested": "neo4j_graph",
    }.get(event.event_type)
    if projection_type is None:
        raise ProjectionExecutionError("OUTBOX_EVENT_UNSUPPORTED")
    source_version = str(event.payload.get("manifest_hash", ""))
    return ProjectionSyncStateRecord(
        id=new_id(),
        projection_type=projection_type,
        aggregate_type=event.aggregate_type,
        aggregate_id=event.aggregate_id,
        source_version=source_version,
        target_version="adapter-managed",
        status=status,
        last_event_id=event.id,
        synced_at=now if status == "succeeded" else None,
        error_safe=error_safe,
        updated_at=now,
    )

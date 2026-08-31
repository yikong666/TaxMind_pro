from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from taxmind.bootstrap.settings import Settings
from taxmind.entrypoints.worker.outbox import build_outbox_dispatch_service
from taxmind.modules.knowledge.application.outbox_dispatch_service import (
    OutboxDispatchService,
    OutboxDispatchUowFactory,
    ProjectionExecutionError,
    ProjectionExecutor,
)
from taxmind.modules.knowledge.domain import OutboxEventRecord, ProjectionSyncStateRecord

_NOW = datetime(2026, 8, 31, tzinfo=UTC)


def _event(*, event_id: str = "event-1", attempt_count: int = 0) -> OutboxEventRecord:
    return OutboxEventRecord(
        id=event_id,
        aggregate_type="knowledge_snapshot",
        aggregate_id="snapshot-1",
        event_type="projection.policy_snapshot.requested",
        payload={"snapshot_id": "snapshot-1", "manifest_hash": "a" * 64},
        dedupe_key=f"projection.policy_snapshot.requested:{event_id}",
        status="pending",
        attempt_count=attempt_count,
        next_attempt_at=None,
        locked_by=None,
        locked_at=None,
        last_error_safe=None,
        created_at=_NOW,
        updated_at=_NOW,
    )


class _Repository:
    def __init__(self, events: list[OutboxEventRecord]) -> None:
        self.events = events
        self.completed: list[str] = []
        self.failures: list[tuple[str, str, datetime | None]] = []
        self.sync_states: list[ProjectionSyncStateRecord] = []

    async def claim_outbox_events(
        self, *, limit: int, worker_id: str, now: datetime
    ) -> list[OutboxEventRecord]:
        del worker_id, now
        return self.events[:limit]

    async def mark_outbox_done(self, event_id: str, *, now: datetime) -> None:
        del now
        self.completed.append(event_id)

    async def mark_outbox_failed(
        self,
        event_id: str,
        *,
        status: str,
        safe_error: str,
        next_attempt_at: datetime | None,
        now: datetime,
    ) -> None:
        del status, now
        self.failures.append((event_id, safe_error, next_attempt_at))

    async def upsert_projection_sync_state(self, record: ProjectionSyncStateRecord) -> None:
        self.sync_states.append(record)


class _Uow:
    def __init__(self, repository: _Repository) -> None:
        self.repository = repository

    async def __aenter__(self) -> _Uow:
        return self

    async def commit(self) -> None:
        return None

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


class _Executor:
    def __init__(self, error: ProjectionExecutionError | None = None) -> None:
        self.error = error
        self.executed: list[str] = []

    async def execute(self, event: OutboxEventRecord) -> None:
        self.executed.append(event.id)
        if self.error is not None:
            raise self.error


def _service(
    repository: _Repository, executor: _Executor, *, max_attempts: int = 3
) -> OutboxDispatchService:
    return OutboxDispatchService(
        uow_factory=cast(OutboxDispatchUowFactory, lambda: _Uow(repository)),
        projection_executor=cast(ProjectionExecutor, executor),
        max_attempts=max_attempts,
        retry_delay_seconds=30,
        clock=lambda: _NOW,
    )


async def test_dispatch_marks_successful_projection_event_done_and_tracks_sync_state() -> None:
    repository = _Repository([_event()])
    executor = _Executor()

    result = await _service(repository, executor).dispatch_once(limit=10, worker_id="worker-a")

    assert result.claimed_count == 1
    assert result.completed_count == 1
    assert result.retryable_count == 0
    assert executor.executed == ["event-1"]
    assert repository.completed == ["event-1"]
    assert repository.failures == []
    assert repository.sync_states[0].status == "succeeded"


async def test_dispatch_schedules_retry_without_recording_external_projection_success() -> None:
    repository = _Repository([_event()])
    executor = _Executor(ProjectionExecutionError("PROJECTION_UNAVAILABLE"))

    result = await _service(repository, executor).dispatch_once(limit=10, worker_id="worker-a")

    assert result.completed_count == 0
    assert result.retryable_count == 1
    assert repository.completed == []
    assert repository.failures == [
        ("event-1", "PROJECTION_UNAVAILABLE", datetime(2026, 8, 31, 0, 0, 30, tzinfo=UTC))
    ]
    assert repository.sync_states[0].status == "retryable"


async def test_dispatch_marks_event_dead_after_retry_limit() -> None:
    repository = _Repository([_event(attempt_count=2)])
    executor = _Executor(ProjectionExecutionError("PROJECTION_UNAVAILABLE"))

    result = await _service(repository, executor, max_attempts=3).dispatch_once(
        limit=10, worker_id="worker-a"
    )

    assert result.dead_count == 1
    assert repository.failures == [("event-1", "PROJECTION_UNAVAILABLE", None)]
    assert repository.sync_states[0].status == "dead"


async def test_dispatch_rejects_invalid_batch_limit() -> None:
    with pytest.raises(ValueError, match="limit"):
        await _service(_Repository([]), _Executor()).dispatch_once(limit=0, worker_id="worker-a")


def test_worker_dispatch_service_uses_bounded_settings() -> None:
    service = build_outbox_dispatch_service(
        Settings(app_env="test", outbox_dispatch_batch_size=5, outbox_max_attempts=4),
        sessions=cast(async_sessionmaker[AsyncSession], object()),
    )

    assert isinstance(service, OutboxDispatchService)

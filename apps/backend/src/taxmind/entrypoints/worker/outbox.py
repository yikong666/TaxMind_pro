from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from taxmind.bootstrap.settings import Settings
from taxmind.modules.knowledge.application.outbox_dispatch_service import (
    OutboxDispatchService,
    ProjectionExecutionError,
    ProjectionExecutor,
)
from taxmind.modules.knowledge.domain import OutboxEventRecord
from taxmind.modules.knowledge.infrastructure.uow import SqlAlchemyKnowledgeUnitOfWorkFactory


class UnconfiguredProjectionExecutor(ProjectionExecutor):
    """Safe default until Milvus and Neo4j adapters are deliberately wired in."""

    async def execute(self, event: OutboxEventRecord) -> None:
        del event
        raise ProjectionExecutionError("PROJECTION_EXECUTOR_UNCONFIGURED")


def build_outbox_dispatch_service(
    settings: Settings, *, sessions: async_sessionmaker[AsyncSession]
) -> OutboxDispatchService:
    return OutboxDispatchService(
        uow_factory=SqlAlchemyKnowledgeUnitOfWorkFactory(sessions),
        projection_executor=UnconfiguredProjectionExecutor(),
        max_attempts=settings.outbox_max_attempts,
        retry_delay_seconds=settings.outbox_retry_delay_seconds,
    )


async def dispatch_pending_projection_events(
    service: OutboxDispatchService, *, limit: int, worker_id: str
) -> tuple[int, int, int]:
    """Worker-compatible dispatch boundary; queue scheduling is intentionally separate."""
    result = await service.dispatch_once(limit=limit, worker_id=worker_id)
    return result.completed_count, result.retryable_count, result.dead_count

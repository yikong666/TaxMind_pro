from __future__ import annotations

from hashlib import sha256
from typing import Protocol, cast

from neo4j import GraphDatabase
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from taxmind.bootstrap.settings import Settings
from taxmind.infrastructure.projections.contracts import (
    MilvusPolicyProjectionPort,
    Neo4jGraphProjectionPort,
)
from taxmind.infrastructure.projections.milvus_policy import (
    MilvusPolicyProjectionAdapter,
    create_milvus_client,
)
from taxmind.infrastructure.projections.neo4j_graph import Neo4jDriver, Neo4jGraphProjectionAdapter
from taxmind.modules.knowledge.application.outbox_dispatch_service import (
    OutboxDispatchService,
    ProjectionExecutionError,
    ProjectionExecutor,
)
from taxmind.modules.knowledge.application.projection_payload_service import (
    SnapshotProjectionPayload,
    SnapshotProjectionPayloadService,
)
from taxmind.modules.knowledge.application.projection_payload_service import (
    SnapshotProjectionPayloadLoader as KnowledgeSnapshotProjectionPayloadLoader,
)
from taxmind.modules.knowledge.domain import OutboxEventRecord
from taxmind.modules.knowledge.infrastructure.uow import SqlAlchemyKnowledgeUnitOfWorkFactory


class UnconfiguredProjectionExecutor(ProjectionExecutor):
    """Safe default until Milvus and Neo4j adapters are deliberately wired in."""

    async def execute(self, event: OutboxEventRecord) -> None:
        del event
        raise ProjectionExecutionError("PROJECTION_EXECUTOR_UNCONFIGURED")


class SnapshotProjectionPayloadLoader(Protocol):
    async def load(self, snapshot_id: str) -> SnapshotProjectionPayload: ...


class SnapshotProjectionExecutor(ProjectionExecutor):
    """Routes a MySQL Outbox event to one rebuildable projection target."""

    def __init__(
        self,
        *,
        loader: SnapshotProjectionPayloadLoader,
        policy_adapter: MilvusPolicyProjectionPort,
        graph_adapter: Neo4jGraphProjectionPort,
    ) -> None:
        self._loader = loader
        self._policy_adapter = policy_adapter
        self._graph_adapter = graph_adapter

    async def execute(self, event: OutboxEventRecord) -> None:
        payload = await self._loader.load(event.aggregate_id)
        if event.event_type == "projection.policy_snapshot.requested":
            await self._policy_adapter.upsert_policy_snapshot(
                payload.policy_records, idempotency_key=event.dedupe_key
            )
            return
        if event.event_type == "projection.graph_snapshot.requested":
            await self._graph_adapter.upsert_graph_snapshot(
                payload.graph_records, idempotency_key=event.dedupe_key
            )
            return
        raise ProjectionExecutionError("OUTBOX_EVENT_UNSUPPORTED")


class DeterministicDevelopmentEmbedding:
    def __init__(self, *, dimension: int) -> None:
        self._dimension = dimension

    async def embed(self, text: str) -> tuple[float, ...]:
        digest = sha256(text.encode("utf-8")).digest()
        return tuple((digest[index % len(digest)] / 127.5) - 1 for index in range(self._dimension))


def build_outbox_dispatch_service(
    settings: Settings, *, sessions: async_sessionmaker[AsyncSession]
) -> OutboxDispatchService:
    executor: ProjectionExecutor = UnconfiguredProjectionExecutor()
    if settings.app_env != "production" and settings.embedding_provider == "fake":
        payload_service = SnapshotProjectionPayloadService(
            embedding=DeterministicDevelopmentEmbedding(dimension=settings.embedding_dimension)
        )
        loader = KnowledgeSnapshotProjectionPayloadLoader(
            uow_factory=SqlAlchemyKnowledgeUnitOfWorkFactory(sessions),
            payload_service=payload_service,
        )
        executor = SnapshotProjectionExecutor(
            loader=loader,
            policy_adapter=MilvusPolicyProjectionAdapter(
                client=create_milvus_client(settings),
                collection_name=f"policy_chunks_{settings.embedding_model_version}",
            ),
            graph_adapter=Neo4jGraphProjectionAdapter(
                driver=cast(
                    Neo4jDriver,
                    GraphDatabase.driver(
                        settings.neo4j_uri,
                        auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value()),
                    ),
                ),
                database=settings.neo4j_database,
            ),
        )
    return OutboxDispatchService(
        uow_factory=SqlAlchemyKnowledgeUnitOfWorkFactory(sessions),
        projection_executor=executor,
        max_attempts=settings.outbox_max_attempts,
        retry_delay_seconds=settings.outbox_retry_delay_seconds,
    )


async def dispatch_pending_projection_events(
    service: OutboxDispatchService, *, limit: int, worker_id: str
) -> tuple[int, int, int]:
    """Worker-compatible dispatch boundary; queue scheduling is intentionally separate."""
    result = await service.dispatch_once(limit=limit, worker_id=worker_id)
    return result.completed_count, result.retryable_count, result.dead_count

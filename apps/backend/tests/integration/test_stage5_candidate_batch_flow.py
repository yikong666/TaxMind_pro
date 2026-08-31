from __future__ import annotations

import os
from datetime import date
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from taxmind.bootstrap.settings import Settings
from taxmind.infrastructure.mysql.session import create_engine
from taxmind.modules.documents.application.service import (
    ChunkInput,
    DocumentMetadataInput,
    DocumentsService,
    DocumentsUnitOfWorkFactory,
    VersionInput,
)
from taxmind.modules.documents.infrastructure.repository import SqlAlchemyDocumentsRepository
from taxmind.modules.identity.infrastructure.models import OrganizationModel, UserModel
from taxmind.modules.knowledge.application.activation_service import (
    KnowledgeSnapshotActivationService,
    ProjectionSmokeVerifier,
    SnapshotActivationUowFactory,
)
from taxmind.modules.knowledge.application.outbox_dispatch_service import (
    OutboxDispatchService,
    OutboxDispatchUowFactory,
)
from taxmind.modules.knowledge.application.review_service import (
    KnowledgeReviewService,
    KnowledgeReviewUnitOfWorkFactory,
)
from taxmind.modules.knowledge.application.service import (
    KnowledgeCandidatesService,
    KnowledgeCandidatesUnitOfWorkFactory,
)
from taxmind.modules.knowledge.application.snapshot_service import (
    KnowledgeSnapshotService,
    SnapshotUowFactory,
)
from taxmind.modules.knowledge.domain import OutboxEventRecord
from taxmind.modules.knowledge.infrastructure.models import (
    KnowledgeSnapshotModel,
    OutboxEventModel,
    ProjectionSyncStateModel,
)
from taxmind.modules.knowledge.infrastructure.repository import SqlAlchemyKnowledgeRepository
from taxmind.shared.domain.ids import new_id
from taxmind.shared.domain.principal import Principal


class _SharedDocumentsUnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.repository: SqlAlchemyDocumentsRepository | None = None

    async def __aenter__(self) -> _SharedDocumentsUnitOfWork:
        self.repository = SqlAlchemyDocumentsRepository(self._session)
        return self

    async def commit(self) -> None:
        await self._session.flush()

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


class _SharedDocumentsUnitOfWorkFactory:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def __call__(self) -> _SharedDocumentsUnitOfWork:
        return _SharedDocumentsUnitOfWork(self._session)


class _SharedKnowledgeUnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.repository: SqlAlchemyKnowledgeRepository | None = None

    async def __aenter__(self) -> _SharedKnowledgeUnitOfWork:
        self.repository = SqlAlchemyKnowledgeRepository(self._session)
        return self

    async def commit(self) -> None:
        await self._session.flush()

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


class _SharedKnowledgeUnitOfWorkFactory:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def __call__(self) -> _SharedKnowledgeUnitOfWork:
        return _SharedKnowledgeUnitOfWork(self._session)


class _SuccessfulProjectionExecutor:
    async def execute(self, event: OutboxEventRecord) -> None:
        assert event.event_type in {
            "projection.policy_snapshot.requested",
            "projection.graph_snapshot.requested",
        }


class _PassingProjectionSmokeVerifier:
    async def verify(self, snapshot: object) -> bool:
        return snapshot is not None


@pytest.mark.skipif(
    os.getenv("TAXMIND_RUN_INTEGRATION") != "1",
    reason="requires the local MySQL Compose service",
)
async def test_candidate_batch_is_reviewed_validated_projected_and_activated() -> None:
    engine = create_engine(Settings(app_env="test"))
    session = AsyncSession(engine, expire_on_commit=False)
    transaction = await session.begin()
    unique = uuid4().hex
    try:
        org_id = new_id()
        user_id = new_id()
        reviewer_id = new_id()
        session.add_all(
            [
                OrganizationModel(
                    id=org_id,
                    code=f"stage5-candidates-{unique}",
                    name="阶段五虚构候选验收机构",
                    status="active",
                    settings_json={},
                    version_no=1,
                ),
                UserModel(
                    id=user_id,
                    email=f"stage5-candidates-{unique}@example.invalid",
                    display_name="阶段五虚构知识管理员",
                    password_hash="not-used-in-integration-test",  # noqa: S106
                    status="active",
                    last_login_at=None,
                ),
                UserModel(
                    id=reviewer_id,
                    email=f"stage5-reviewer-{unique}@example.invalid",
                    display_name="阶段五虚构复核人",
                    password_hash="not-used-in-integration-test",  # noqa: S106
                    status="active",
                    last_login_at=None,
                ),
            ]
        )
        await session.flush()
        principal = Principal(
            user_id=user_id,
            org_id=org_id,
            session_id=new_id(),
            roles=frozenset({"knowledge_admin"}),
            permissions=frozenset({"knowledge:read", "knowledge:write"}),
        )
        reviewer = Principal(
            user_id=reviewer_id,
            org_id=org_id,
            session_id=new_id(),
            roles=frozenset({"knowledge_reviewer"}),
            permissions=frozenset({"knowledge:review"}),
        )
        documents = DocumentsService(
            uow_factory=cast(
                DocumentsUnitOfWorkFactory,
                _SharedDocumentsUnitOfWorkFactory(session),
            )
        )
        detail = await documents.create_document(
            DocumentMetadataInput(
                title="阶段五虚构候选资料",
                doc_no=f"STAGE5-CANDIDATES-{unique[:8]}",
                doc_type="announcement",
                source_level="A",
                issuing_authority="阶段五虚构机关",
                region_code="440300",
                publish_date=date(2026, 8, 31),
                effective_start=None,
                effective_end=None,
                policy_status="active",
                canonical_url=f"https://example.invalid/stage5/candidates/{unique}",
            ),
            VersionInput(
                source_url=f"https://example.invalid/stage5/candidates/{unique}",
                mime_type="text/plain",
                content_hash_sha256="c" * 64,
                raw_object_key="stage5/fake.txt",
                parsed_object_key=None,
            ),
            request_id=new_id(),
            principal=principal,
        )
        await documents.create_chunks(
            detail.version.id,
            [
                ChunkInput(
                    source_chunk_id=f"stage5-candidate-{unique}:1",
                    chunk_order=0,
                    chunk_type="article",
                    heading_path="第一条",
                    clause_label="第一条",
                    content_text="第一条 本资料只用于阶段五候选队列验收。",
                    content_hash_sha256="d" * 64,
                    token_count=20,
                    effective_start=None,
                    effective_end=None,
                )
            ],
            request_id=new_id(),
            principal=principal,
        )
        candidates = KnowledgeCandidatesService(
            uow_factory=cast(
                KnowledgeCandidatesUnitOfWorkFactory,
                _SharedKnowledgeUnitOfWorkFactory(session),
            )
        )

        created = await candidates.create_rule_based_batch(
            detail.version.id,
            request_id=new_id(),
            principal=principal,
        )
        queue = await candidates.list_pending_candidates(limit=10, principal=principal)
        outbox_before = await session.scalar(select(func.count()).select_from(OutboxEventModel))
        review = KnowledgeReviewService(
            uow_factory=cast(
                KnowledgeReviewUnitOfWorkFactory,
                _SharedKnowledgeUnitOfWorkFactory(session),
            )
        )
        approved = await review.review_candidate(
            created.candidates[0].id,
            decision="approved",
            reason=None,
            request_id=new_id(),
            principal=reviewer,
        )
        publish_batch = await review.create_publish_batch(
            candidate_ids=[approved.id],
            request_id=new_id(),
            principal=reviewer,
        )
        validated = await review.validate_publish_batch(
            publish_batch.id,
            request_id=new_id(),
            principal=reviewer,
        )
        outbox_after_validation = await session.scalar(
            select(func.count()).select_from(OutboxEventModel)
        )
        snapshot = await KnowledgeSnapshotService(
            uow_factory=cast(
                SnapshotUowFactory,
                _SharedKnowledgeUnitOfWorkFactory(session),
            )
        ).materialize_validated_batch(
            validated.id,
            request_id=new_id(),
            principal=reviewer,
        )
        outbox_events = list(
            await session.scalars(
                select(OutboxEventModel).where(
                    OutboxEventModel.aggregate_id == snapshot.snapshot.id
                )
            )
        )
        projection_candidates = await SqlAlchemyKnowledgeRepository(
            session
        ).list_snapshot_projection_candidates(snapshot.snapshot.id)

        assert created.created is True
        assert created.batch.model_name is None
        assert created.candidates[0].review_status == "pending_review"
        assert created.candidates[0].source_document_id == detail.document.id
        assert created.candidates[0].source_chunk_id == f"stage5-candidate-{unique}:1"
        assert any(candidate.id == created.candidates[0].id for candidate in queue)
        assert approved.review_status == "approved"
        assert approved.reviewed_by == reviewer_id
        assert validated.status == "validated"
        assert validated.published_at is None
        assert validated.validation_report["passed"] is True
        assert outbox_after_validation == outbox_before
        assert snapshot.snapshot.status == "pending_activation"
        assert snapshot.snapshot.activated_at is None
        assert {event.event_type for event in outbox_events} == {
            "projection.policy_snapshot.requested",
            "projection.graph_snapshot.requested",
        }
        assert all(event.status == "pending" for event in outbox_events)
        assert projection_candidates[0].candidate.id == created.candidates[0].id
        assert projection_candidates[0].document_version_id == detail.version.id
        dispatch_result = await OutboxDispatchService(
            uow_factory=cast(
                OutboxDispatchUowFactory,
                _SharedKnowledgeUnitOfWorkFactory(session),
            ),
            projection_executor=_SuccessfulProjectionExecutor(),
            max_attempts=3,
            retry_delay_seconds=30,
        ).dispatch_once(limit=10, worker_id=f"stage5-worker-{unique[:8]}")
        dispatched_events = list(
            await session.scalars(
                select(OutboxEventModel).where(
                    OutboxEventModel.aggregate_id == snapshot.snapshot.id
                )
            )
        )
        sync_states = list(
            await session.scalars(
                select(ProjectionSyncStateModel).where(
                    ProjectionSyncStateModel.aggregate_id == snapshot.snapshot.id
                )
            )
        )
        assert dispatch_result.completed_count == 2
        assert dispatch_result.retryable_count == 0
        assert {event.status for event in dispatched_events} == {"done"}
        assert {state.status for state in sync_states} == {"succeeded"}
        activated = await KnowledgeSnapshotActivationService(
            uow_factory=cast(
                SnapshotActivationUowFactory,
                _SharedKnowledgeUnitOfWorkFactory(session),
            ),
            projection_smoke_verifier=cast(
                ProjectionSmokeVerifier, _PassingProjectionSmokeVerifier()
            ),
        ).activate_snapshot(
            snapshot.snapshot.id,
            request_id=new_id(),
            principal=reviewer,
        )
        activated_model = await session.get(KnowledgeSnapshotModel, snapshot.snapshot.id)
        assert activated.snapshot.status == "active"
        assert activated.snapshot.activated_by == reviewer_id
        assert activated_model is not None
        assert activated_model.status == "active"
        assert activated_model.activated_at is not None
    finally:
        if transaction.is_active:
            await transaction.rollback()
        await session.close()
        await engine.dispose()

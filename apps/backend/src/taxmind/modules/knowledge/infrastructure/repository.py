from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from taxmind.modules.audit.infrastructure.models import AuditLogModel
from taxmind.modules.documents.domain import (
    DocumentChunkRecord,
    DocumentVersionRecord,
    SourceDocumentRecord,
)
from taxmind.modules.documents.infrastructure.models import (
    DocumentChunkModel,
    DocumentVersionModel,
    SourceDocumentModel,
)
from taxmind.modules.knowledge.domain import (
    KnowledgeCandidateBatchRecord,
    KnowledgeCandidateRecord,
    KnowledgePublishBatchItemRecord,
    KnowledgePublishBatchRecord,
    KnowledgeSnapshotItemRecord,
    KnowledgeSnapshotRecord,
    OutboxEventRecord,
    ProjectionSyncStateRecord,
    SnapshotProjectionCandidateRecord,
)
from taxmind.modules.knowledge.infrastructure.models import (
    KnowledgeCandidateBatchModel,
    KnowledgeCandidateModel,
    KnowledgePublishBatchItemModel,
    KnowledgePublishBatchModel,
    KnowledgeSnapshotItemModel,
    KnowledgeSnapshotModel,
    OutboxEventModel,
    ProjectionSyncStateModel,
)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _document_record(model: SourceDocumentModel) -> SourceDocumentRecord:
    return SourceDocumentRecord(
        id=model.id,
        canonical_key=model.canonical_key,
        title=model.title,
        doc_no=model.doc_no,
        doc_type=model.doc_type,
        source_level=model.source_level,
        issuing_authority=model.issuing_authority,
        region_code=model.region_code,
        publish_date=model.publish_date,
        effective_start=model.effective_start,
        effective_end=model.effective_end,
        policy_status=model.policy_status,
        canonical_url=model.canonical_url,
        current_version_id=model.current_version_id,
        review_status=model.review_status,
        created_by=model.created_by,
        created_at=_as_utc(model.created_at),
        updated_at=_as_utc(model.updated_at),
    )


def _version_record(model: DocumentVersionModel) -> DocumentVersionRecord:
    return DocumentVersionRecord(
        id=model.id,
        document_id=model.document_id,
        version_no=model.version_no,
        captured_at=_as_utc(model.captured_at),
        source_url=model.source_url,
        raw_object_key=model.raw_object_key,
        parsed_object_key=model.parsed_object_key,
        mime_type=model.mime_type,
        content_hash_sha256=model.content_hash_sha256,
        parse_status=model.parse_status,
        ocr_status=model.ocr_status,
        review_status=model.review_status,
        published_at=_as_utc(model.published_at) if model.published_at else None,
        supersedes_version_id=model.supersedes_version_id,
        created_by=model.created_by,
    )


def _chunk_record(model: DocumentChunkModel) -> DocumentChunkRecord:
    return DocumentChunkRecord(
        id=model.id,
        document_id=model.document_id,
        document_version_id=model.document_version_id,
        source_chunk_id=model.source_chunk_id,
        chunk_order=model.chunk_order,
        chunk_type=model.chunk_type,
        heading_path=model.heading_path,
        clause_label=model.clause_label,
        content_text=model.content_text,
        content_hash_sha256=model.content_hash_sha256,
        token_count=model.token_count,
        effective_start=model.effective_start,
        effective_end=model.effective_end,
        region_code=model.region_code,
        policy_status=model.policy_status,
        review_status=model.review_status,
        index_status=model.index_status,
    )


def _outbox_event_record(model: OutboxEventModel) -> OutboxEventRecord:
    return OutboxEventRecord(
        id=model.id,
        aggregate_type=model.aggregate_type,
        aggregate_id=model.aggregate_id,
        event_type=model.event_type,
        payload=model.payload_json,
        dedupe_key=model.dedupe_key,
        status=model.status,
        attempt_count=model.attempt_count,
        next_attempt_at=_as_utc(model.next_attempt_at) if model.next_attempt_at else None,
        locked_by=model.locked_by,
        locked_at=_as_utc(model.locked_at) if model.locked_at else None,
        last_error_safe=model.last_error_safe,
        created_at=_as_utc(model.created_at),
        updated_at=_as_utc(model.updated_at),
    )


def _batch_record(model: KnowledgeCandidateBatchModel) -> KnowledgeCandidateBatchRecord:
    return KnowledgeCandidateBatchRecord(
        id=model.id,
        document_version_id=model.document_version_id,
        extraction_method=model.extraction_method,
        extractor_version=model.extractor_version,
        model_name=model.model_name,
        prompt_version=model.prompt_version,
        status=model.status,
        candidate_count=model.candidate_count,
        created_by=model.created_by,
        created_at=_as_utc(model.created_at),
    )


def _candidate_record(model: KnowledgeCandidateModel) -> KnowledgeCandidateRecord:
    return KnowledgeCandidateRecord(
        id=model.id,
        batch_id=model.batch_id,
        candidate_type=model.candidate_type,
        payload=dict(model.payload_json),
        source_document_id=model.source_document_id,
        source_chunk_id=model.source_chunk_id,
        extraction_method=model.extraction_method,
        extraction_confidence=Decimal(model.extraction_confidence),
        normalization_status=model.normalization_status,
        review_status=model.review_status,
        review_reason_safe=model.review_reason_safe,
        reviewed_by=model.reviewed_by,
        reviewed_at=_as_utc(model.reviewed_at) if model.reviewed_at else None,
        content_hash=model.content_hash,
        created_at=_as_utc(model.created_at),
    )


def _publish_batch_record(model: KnowledgePublishBatchModel) -> KnowledgePublishBatchRecord:
    return KnowledgePublishBatchRecord(
        id=model.id,
        batch_type=model.batch_type,
        scope=model.scope,
        org_id=model.org_id,
        status=model.status,
        candidate_count=model.candidate_count,
        approved_count=model.approved_count,
        rejected_count=model.rejected_count,
        validation_report=dict(model.validation_report_json),
        manifest_hash=model.manifest_hash,
        submitted_by=model.submitted_by,
        approved_by=model.approved_by,
        submitted_at=_as_utc(model.submitted_at),
        published_at=_as_utc(model.published_at) if model.published_at else None,
        created_at=_as_utc(model.created_at),
    )


def _snapshot_record(model: KnowledgeSnapshotModel) -> KnowledgeSnapshotRecord:
    return KnowledgeSnapshotRecord(
        id=model.id,
        org_id=model.org_id,
        snapshot_code=model.snapshot_code,
        snapshot_type=model.snapshot_type,
        status=model.status,
        base_snapshot_id=model.base_snapshot_id,
        description=model.description,
        manifest_hash=model.manifest_hash,
        activated_at=_as_utc(model.activated_at) if model.activated_at else None,
        activated_by=model.activated_by,
        created_at=_as_utc(model.created_at),
    )


def _projection_sync_state_record(model: ProjectionSyncStateModel) -> ProjectionSyncStateRecord:
    return ProjectionSyncStateRecord(
        id=model.id,
        projection_type=model.projection_type,
        aggregate_type=model.aggregate_type,
        aggregate_id=model.aggregate_id,
        source_version=model.source_version,
        target_version=model.target_version,
        status=model.status,
        last_event_id=model.last_event_id,
        synced_at=_as_utc(model.synced_at) if model.synced_at else None,
        error_safe=model.error_safe,
        updated_at=_as_utc(model.updated_at),
    )


class SqlAlchemyKnowledgeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def flush(self) -> None:
        await self._session.flush()

    async def get_version(
        self, version_id: str, *, lock: bool = False
    ) -> DocumentVersionRecord | None:
        statement = select(DocumentVersionModel).where(DocumentVersionModel.id == version_id)
        if lock:
            statement = statement.with_for_update()
        model = await self._session.scalar(statement)
        return _version_record(model) if model else None

    async def get_document(self, document_id: str) -> SourceDocumentRecord | None:
        model = await self._session.get(SourceDocumentModel, document_id)
        return _document_record(model) if model else None

    async def list_chunks(self, version_id: str) -> list[DocumentChunkRecord]:
        models = await self._session.scalars(
            select(DocumentChunkModel)
            .where(DocumentChunkModel.document_version_id == version_id)
            .order_by(DocumentChunkModel.chunk_order, DocumentChunkModel.id)
        )
        return [_chunk_record(model) for model in models]

    async def get_completed_rule_batch(
        self, document_version_id: str
    ) -> KnowledgeCandidateBatchRecord | None:
        model = await self._session.scalar(
            select(KnowledgeCandidateBatchModel)
            .where(
                KnowledgeCandidateBatchModel.document_version_id == document_version_id,
                KnowledgeCandidateBatchModel.extraction_method == "rule_based",
                KnowledgeCandidateBatchModel.extractor_version == "rule_based_v1",
                KnowledgeCandidateBatchModel.status == "completed",
            )
            .order_by(KnowledgeCandidateBatchModel.created_at.desc())
            .limit(1)
        )
        return _batch_record(model) if model else None

    async def create_batch(self, record: KnowledgeCandidateBatchRecord) -> None:
        self._session.add(
            KnowledgeCandidateBatchModel(
                id=record.id,
                document_version_id=record.document_version_id,
                extraction_method=record.extraction_method,
                extractor_version=record.extractor_version,
                model_name=record.model_name,
                prompt_version=record.prompt_version,
                status=record.status,
                candidate_count=record.candidate_count,
                created_by=record.created_by,
                created_at=record.created_at,
            )
        )

    async def create_candidates(self, records: list[KnowledgeCandidateRecord]) -> None:
        self._session.add_all(
            [
                KnowledgeCandidateModel(
                    id=record.id,
                    batch_id=record.batch_id,
                    candidate_type=record.candidate_type,
                    payload_json=record.payload,
                    source_document_id=record.source_document_id,
                    source_chunk_id=record.source_chunk_id,
                    extraction_method=record.extraction_method,
                    extraction_confidence=record.extraction_confidence,
                    normalization_status=record.normalization_status,
                    review_status=record.review_status,
                    review_reason_safe=record.review_reason_safe,
                    content_hash=record.content_hash,
                    created_at=record.created_at,
                )
                for record in records
            ]
        )

    async def list_candidates_by_batch(self, batch_id: str) -> list[KnowledgeCandidateRecord]:
        models = await self._session.scalars(
            select(KnowledgeCandidateModel)
            .where(KnowledgeCandidateModel.batch_id == batch_id)
            .order_by(KnowledgeCandidateModel.created_at, KnowledgeCandidateModel.id)
        )
        return [_candidate_record(model) for model in models]

    async def list_pending_candidates(self, *, limit: int) -> list[KnowledgeCandidateRecord]:
        models = await self._session.scalars(
            select(KnowledgeCandidateModel)
            .where(KnowledgeCandidateModel.review_status == "pending_review")
            .order_by(KnowledgeCandidateModel.created_at, KnowledgeCandidateModel.id)
            .limit(limit)
        )
        return [_candidate_record(model) for model in models]

    async def get_candidate(
        self, candidate_id: str, *, lock: bool = False
    ) -> KnowledgeCandidateRecord | None:
        statement = select(KnowledgeCandidateModel).where(
            KnowledgeCandidateModel.id == candidate_id
        )
        if lock:
            statement = statement.with_for_update()
        model = await self._session.scalar(statement)
        return _candidate_record(model) if model else None

    async def get_candidate_batch(self, batch_id: str) -> KnowledgeCandidateBatchRecord | None:
        model = await self._session.get(KnowledgeCandidateBatchModel, batch_id)
        return _batch_record(model) if model else None

    async def set_candidate_review(self, record: KnowledgeCandidateRecord) -> None:
        model = await self._session.get(KnowledgeCandidateModel, record.id)
        if model is None:
            raise RuntimeError("knowledge candidate disappeared before review")
        model.review_status = record.review_status
        model.review_reason_safe = record.review_reason_safe
        model.reviewed_by = record.reviewed_by
        model.reviewed_at = record.reviewed_at

    async def list_candidates_by_ids(
        self, candidate_ids: list[str]
    ) -> list[KnowledgeCandidateRecord]:
        models = await self._session.scalars(
            select(KnowledgeCandidateModel).where(KnowledgeCandidateModel.id.in_(candidate_ids))
        )
        by_id = {model.id: _candidate_record(model) for model in models}
        return [by_id[candidate_id] for candidate_id in candidate_ids if candidate_id in by_id]

    async def create_publish_batch(self, record: KnowledgePublishBatchRecord) -> None:
        self._session.add(
            KnowledgePublishBatchModel(
                id=record.id,
                batch_type=record.batch_type,
                scope=record.scope,
                org_id=record.org_id,
                status=record.status,
                candidate_count=record.candidate_count,
                approved_count=record.approved_count,
                rejected_count=record.rejected_count,
                validation_report_json=record.validation_report,
                manifest_hash=record.manifest_hash,
                submitted_by=record.submitted_by,
                approved_by=record.approved_by,
                submitted_at=record.submitted_at,
                published_at=record.published_at,
                created_at=record.created_at,
            )
        )

    async def create_publish_items(self, records: list[KnowledgePublishBatchItemRecord]) -> None:
        self._session.add_all(
            [
                KnowledgePublishBatchItemModel(
                    id=record.id,
                    batch_id=record.batch_id,
                    candidate_id=record.candidate_id,
                    decision=record.decision,
                    checksum=record.checksum,
                )
                for record in records
            ]
        )

    async def get_publish_batch(
        self, batch_id: str, *, lock: bool = False
    ) -> KnowledgePublishBatchRecord | None:
        statement = select(KnowledgePublishBatchModel).where(
            KnowledgePublishBatchModel.id == batch_id
        )
        if lock:
            statement = statement.with_for_update()
        model = await self._session.scalar(statement)
        return _publish_batch_record(model) if model else None

    async def list_publish_candidates(self, batch_id: str) -> list[KnowledgeCandidateRecord]:
        models = await self._session.scalars(
            select(KnowledgeCandidateModel)
            .join(
                KnowledgePublishBatchItemModel,
                KnowledgePublishBatchItemModel.candidate_id == KnowledgeCandidateModel.id,
            )
            .where(KnowledgePublishBatchItemModel.batch_id == batch_id)
            .order_by(KnowledgePublishBatchItemModel.id)
        )
        return [_candidate_record(model) for model in models]

    async def set_publish_batch_validation(self, record: KnowledgePublishBatchRecord) -> None:
        model = await self._session.get(KnowledgePublishBatchModel, record.id)
        if model is None:
            raise RuntimeError("knowledge publish batch disappeared before validation")
        model.status = record.status
        model.validation_report_json = record.validation_report

    async def create_snapshot(self, record: KnowledgeSnapshotRecord) -> None:
        self._session.add(
            KnowledgeSnapshotModel(
                id=record.id,
                org_id=record.org_id,
                snapshot_code=record.snapshot_code,
                snapshot_type=record.snapshot_type,
                status=record.status,
                base_snapshot_id=record.base_snapshot_id,
                description=record.description,
                manifest_hash=record.manifest_hash,
                activated_at=record.activated_at,
                activated_by=record.activated_by,
                created_at=record.created_at,
            )
        )

    async def get_snapshot(
        self, snapshot_id: str, *, lock: bool = False
    ) -> KnowledgeSnapshotRecord | None:
        statement = select(KnowledgeSnapshotModel).where(KnowledgeSnapshotModel.id == snapshot_id)
        if lock:
            statement = statement.with_for_update()
        model = await self._session.scalar(statement)
        return _snapshot_record(model) if model else None

    async def activate_snapshot(self, record: KnowledgeSnapshotRecord) -> None:
        model = await self._session.get(KnowledgeSnapshotModel, record.id)
        if model is None:
            raise RuntimeError("knowledge snapshot disappeared before activation")
        model.status = record.status
        model.activated_at = record.activated_at
        model.activated_by = record.activated_by

    async def create_snapshot_items(self, records: list[KnowledgeSnapshotItemRecord]) -> None:
        self._session.add_all(
            [
                KnowledgeSnapshotItemModel(
                    id=r.id,
                    snapshot_id=r.snapshot_id,
                    item_type=r.item_type,
                    item_id=r.item_id,
                    item_version=r.item_version,
                    checksum=r.checksum,
                )
                for r in records
            ]
        )

    async def list_snapshot_projection_candidates(
        self, snapshot_id: str
    ) -> list[SnapshotProjectionCandidateRecord]:
        rows = await self._session.execute(
            select(KnowledgeCandidateModel, KnowledgeCandidateBatchModel.document_version_id)
            .join(
                KnowledgeSnapshotItemModel,
                KnowledgeSnapshotItemModel.item_id == KnowledgeCandidateModel.id,
            )
            .join(
                KnowledgeCandidateBatchModel,
                KnowledgeCandidateBatchModel.id == KnowledgeCandidateModel.batch_id,
            )
            .where(
                KnowledgeSnapshotItemModel.snapshot_id == snapshot_id,
                KnowledgeSnapshotItemModel.item_type == "policy_clause",
            )
            .order_by(KnowledgeSnapshotItemModel.id)
        )
        return [
            SnapshotProjectionCandidateRecord(
                candidate=_candidate_record(candidate),
                document_version_id=document_version_id,
            )
            for candidate, document_version_id in rows.all()
        ]

    async def create_outbox_events(self, records: list[OutboxEventRecord]) -> None:
        self._session.add_all(
            [
                OutboxEventModel(
                    id=r.id,
                    aggregate_type=r.aggregate_type,
                    aggregate_id=r.aggregate_id,
                    event_type=r.event_type,
                    payload_json=r.payload,
                    dedupe_key=r.dedupe_key,
                    status=r.status,
                    attempt_count=r.attempt_count,
                    next_attempt_at=r.next_attempt_at,
                    locked_by=r.locked_by,
                    locked_at=r.locked_at,
                    last_error_safe=r.last_error_safe,
                    created_at=r.created_at,
                    updated_at=r.updated_at,
                )
                for r in records
            ]
        )

    async def claim_outbox_events(
        self, *, limit: int, worker_id: str, now: datetime
    ) -> list[OutboxEventRecord]:
        models = list(
            await self._session.scalars(
                select(OutboxEventModel)
                .where(
                    OutboxEventModel.status.in_(("pending", "retryable")),
                    or_(
                        OutboxEventModel.next_attempt_at.is_(None),
                        OutboxEventModel.next_attempt_at <= now,
                    ),
                )
                .order_by(OutboxEventModel.created_at, OutboxEventModel.id)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        )
        records = [_outbox_event_record(model) for model in models]
        for model in models:
            model.status = "processing"
            model.attempt_count += 1
            model.locked_by = worker_id
            model.locked_at = now
            model.updated_at = now
        return records

    async def mark_outbox_done(self, event_id: str, *, now: datetime) -> None:
        model = await self._session.get(OutboxEventModel, event_id)
        if model is None:
            raise RuntimeError("outbox event disappeared before completion")
        if model.status == "done":
            return
        model.status = "done"
        model.next_attempt_at = None
        model.locked_by = None
        model.locked_at = None
        model.last_error_safe = None
        model.updated_at = now

    async def mark_outbox_failed(
        self,
        event_id: str,
        *,
        status: str,
        safe_error: str,
        next_attempt_at: datetime | None,
        now: datetime,
    ) -> None:
        if status not in {"retryable", "dead"}:
            raise ValueError("outbox failure status is invalid")
        model = await self._session.get(OutboxEventModel, event_id)
        if model is None:
            raise RuntimeError("outbox event disappeared before failure recording")
        model.status = status
        model.next_attempt_at = next_attempt_at
        model.locked_by = None
        model.locked_at = None
        model.last_error_safe = safe_error
        model.updated_at = now

    async def upsert_projection_sync_state(self, record: ProjectionSyncStateRecord) -> None:
        model = await self._session.scalar(
            select(ProjectionSyncStateModel).where(
                ProjectionSyncStateModel.projection_type == record.projection_type,
                ProjectionSyncStateModel.aggregate_type == record.aggregate_type,
                ProjectionSyncStateModel.aggregate_id == record.aggregate_id,
                ProjectionSyncStateModel.source_version == record.source_version,
                ProjectionSyncStateModel.target_version == record.target_version,
            )
        )
        if model is None:
            self._session.add(
                ProjectionSyncStateModel(
                    id=record.id,
                    projection_type=record.projection_type,
                    aggregate_type=record.aggregate_type,
                    aggregate_id=record.aggregate_id,
                    source_version=record.source_version,
                    target_version=record.target_version,
                    status=record.status,
                    last_event_id=record.last_event_id,
                    synced_at=record.synced_at,
                    error_safe=record.error_safe,
                    updated_at=record.updated_at,
                )
            )
            return
        model.status = record.status
        model.last_event_id = record.last_event_id
        model.synced_at = record.synced_at
        model.error_safe = record.error_safe
        model.updated_at = record.updated_at

    async def list_projection_sync_states(
        self, snapshot_id: str
    ) -> list[ProjectionSyncStateRecord]:
        models = await self._session.scalars(
            select(ProjectionSyncStateModel)
            .where(
                ProjectionSyncStateModel.aggregate_type == "knowledge_snapshot",
                ProjectionSyncStateModel.aggregate_id == snapshot_id,
            )
            .order_by(ProjectionSyncStateModel.projection_type, ProjectionSyncStateModel.updated_at)
        )
        return [_projection_sync_state_record(model) for model in models]

    async def create_audit_log(
        self,
        *,
        org_id: str,
        actor_user_id: str,
        action_code: str,
        resource_type: str = "knowledge_candidate_batch",
        resource_id: str,
        request_id: str,
        occurred_at: datetime,
    ) -> None:
        self._session.add(
            AuditLogModel(
                org_id=org_id,
                actor_user_id=actor_user_id,
                action_code=action_code,
                resource_type=resource_type,
                resource_id=resource_id,
                request_id=request_id,
                result="success",
                occurred_at=occurred_at,
            )
        )

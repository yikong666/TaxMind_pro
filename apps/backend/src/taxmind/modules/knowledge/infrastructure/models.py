from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CHAR,
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from taxmind.infrastructure.mysql.base import Base
from taxmind.shared.domain.ids import new_id


class KnowledgeCandidateBatchModel(Base):
    __tablename__ = "knowledge_candidate_batches"
    __table_args__ = (
        Index("ix_candidate_batches_document_status", "document_version_id", "status"),
    )

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=new_id)
    document_version_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("document_versions.id"), nullable=False
    )
    extraction_method: Mapped[str] = mapped_column(String(32), nullable=False)
    extractor_version: Mapped[str] = mapped_column(String(100), nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(100))
    prompt_version: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class KnowledgeCandidateModel(Base):
    __tablename__ = "knowledge_candidates"
    __table_args__ = (
        UniqueConstraint("batch_id", "content_hash", name="uq_candidates_batch_hash"),
        Index("ix_candidates_review_type", "review_status", "candidate_type"),
        Index("ix_candidates_source_chunk", "source_document_id", "source_chunk_id"),
    )

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=new_id)
    batch_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("knowledge_candidate_batches.id"), nullable=False
    )
    candidate_type: Mapped[str] = mapped_column(String(32), nullable=False)
    payload_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    source_document_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("source_documents.id"), nullable=False
    )
    source_chunk_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("document_chunks.source_chunk_id"), nullable=False
    )
    extraction_method: Mapped[str] = mapped_column(String(32), nullable=False)
    extraction_confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    normalization_status: Mapped[str] = mapped_column(String(32), nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False)
    review_reason_safe: Mapped[str | None] = mapped_column(String(1000))
    reviewed_by: Mapped[str | None] = mapped_column(CHAR(36), ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    content_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class KnowledgePublishBatchModel(Base):
    __tablename__ = "knowledge_publish_batches"
    __table_args__ = (Index("ix_publish_batches_scope_status", "scope", "org_id", "status"),)

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=new_id)
    batch_type: Mapped[str] = mapped_column(String(32), nullable=False)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    org_id: Mapped[str | None] = mapped_column(CHAR(36), ForeignKey("organizations.id"))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False)
    approved_count: Mapped[int] = mapped_column(Integer, nullable=False)
    rejected_count: Mapped[int] = mapped_column(Integer, nullable=False)
    validation_report_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    manifest_hash: Mapped[str | None] = mapped_column(CHAR(64))
    submitted_by: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id"), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(CHAR(36), ForeignKey("users.id"))
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class KnowledgePublishBatchItemModel(Base):
    __tablename__ = "knowledge_publish_batch_items"
    __table_args__ = (
        UniqueConstraint("batch_id", "candidate_id", name="uq_publish_items_batch_candidate"),
    )

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=new_id)
    batch_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("knowledge_publish_batches.id"), nullable=False
    )
    candidate_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("knowledge_candidates.id"), nullable=False
    )
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    checksum: Mapped[str] = mapped_column(CHAR(64), nullable=False)


class KnowledgeSnapshotModel(Base):
    __tablename__ = "knowledge_snapshots"
    __table_args__ = (
        UniqueConstraint("snapshot_code", name="uq_knowledge_snapshots_code"),
        Index("ix_knowledge_snapshots_scope_status", "snapshot_type", "org_id", "status"),
    )

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=new_id)
    org_id: Mapped[str | None] = mapped_column(CHAR(36), ForeignKey("organizations.id"))
    snapshot_code: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    base_snapshot_id: Mapped[str | None] = mapped_column(
        CHAR(36), ForeignKey("knowledge_snapshots.id")
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    manifest_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activated_by: Mapped[str | None] = mapped_column(CHAR(36), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class KnowledgeSnapshotItemModel(Base):
    __tablename__ = "knowledge_snapshot_items"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "item_type", "item_id", name="uq_snapshot_items_identity"),
    )

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=new_id)
    snapshot_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("knowledge_snapshots.id"), nullable=False
    )
    item_type: Mapped[str] = mapped_column(String(32), nullable=False)
    item_id: Mapped[str] = mapped_column(CHAR(36), nullable=False)
    item_version: Mapped[str] = mapped_column(String(100), nullable=False)
    checksum: Mapped[str] = mapped_column(CHAR(64), nullable=False)


class OutboxEventModel(Base):
    __tablename__ = "outbox_events"
    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_outbox_events_dedupe_key"),
        Index("ix_outbox_events_status_next", "status", "next_attempt_at"),
        Index("ix_outbox_events_aggregate", "aggregate_type", "aggregate_id"),
    )

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=new_id)
    aggregate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(CHAR(36), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_by: Mapped[str | None] = mapped_column(String(100))
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_safe: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProjectionSyncStateModel(Base):
    __tablename__ = "projection_sync_states"
    __table_args__ = (
        UniqueConstraint(
            "projection_type",
            "aggregate_type",
            "aggregate_id",
            "source_version",
            "target_version",
            name="uq_projection_sync_identity",
        ),
        Index("ix_projection_sync_status", "projection_type", "status"),
    )

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=new_id)
    projection_type: Mapped[str] = mapped_column(String(32), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(CHAR(36), nullable=False)
    source_version: Mapped[str] = mapped_column(String(100), nullable=False)
    target_version: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    last_event_id: Mapped[str | None] = mapped_column(CHAR(36), ForeignKey("outbox_events.id"))
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_safe: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

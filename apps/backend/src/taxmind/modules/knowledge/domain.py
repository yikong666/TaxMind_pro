from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class KnowledgeCandidateBatchRecord:
    id: str
    document_version_id: str
    extraction_method: str
    extractor_version: str
    model_name: str | None
    prompt_version: str | None
    status: str
    candidate_count: int
    created_by: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class KnowledgeCandidateRecord:
    id: str
    batch_id: str
    candidate_type: str
    payload: dict[str, object]
    source_document_id: str
    source_chunk_id: str
    extraction_method: str
    extraction_confidence: Decimal
    normalization_status: str
    review_status: str
    review_reason_safe: str | None
    reviewed_by: str | None
    reviewed_at: datetime | None
    content_hash: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class KnowledgePublishBatchRecord:
    id: str
    batch_type: str
    scope: str
    org_id: str | None
    status: str
    candidate_count: int
    approved_count: int
    rejected_count: int
    validation_report: dict[str, object]
    manifest_hash: str | None
    submitted_by: str
    approved_by: str | None
    submitted_at: datetime
    published_at: datetime | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class KnowledgePublishBatchItemRecord:
    id: str
    batch_id: str
    candidate_id: str
    decision: str
    checksum: str


@dataclass(frozen=True, slots=True)
class KnowledgeSnapshotRecord:
    id: str
    org_id: str | None
    snapshot_code: str
    snapshot_type: str
    status: str
    base_snapshot_id: str | None
    description: str
    manifest_hash: str
    activated_at: datetime | None
    activated_by: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class KnowledgeSnapshotItemRecord:
    id: str
    snapshot_id: str
    item_type: str
    item_id: str
    item_version: str
    checksum: str


@dataclass(frozen=True, slots=True)
class OutboxEventRecord:
    id: str
    aggregate_type: str
    aggregate_id: str
    event_type: str
    payload: dict[str, object]
    dedupe_key: str
    status: str
    attempt_count: int
    next_attempt_at: datetime | None
    locked_by: str | None
    locked_at: datetime | None
    last_error_safe: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ProjectionSyncStateRecord:
    id: str
    projection_type: str
    aggregate_type: str
    aggregate_id: str
    source_version: str
    target_version: str
    status: str
    last_event_id: str | None
    synced_at: datetime | None
    error_safe: str | None
    updated_at: datetime

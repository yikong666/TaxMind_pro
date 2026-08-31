"""create offline knowledge governance contract tables

Revision ID: 20260831_0006
Revises: 20260831_0005
Create Date: 2026-08-31 10:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260831_0006"
down_revision: str | None = "20260831_0005"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "source_sites",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("base_url", sa.String(1500), nullable=False),
        sa.Column("domain", sa.String(253), nullable=False),
        sa.Column("source_level", sa.String(32), nullable=False),
        sa.Column("authority_name", sa.String(200), nullable=False),
        sa.Column("region_code", sa.String(6), nullable=False),
        sa.Column("collection_method", sa.String(32), nullable=False),
        sa.Column("whitelist_rules_json", sa.JSON(), nullable=False),
        sa.Column("crawl_interval_minutes", sa.Integer()),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", sa.CHAR(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.UniqueConstraint("domain", "region_code", name="uq_source_sites_domain_region"),
    )
    op.create_index("ix_source_sites_status_level", "source_sites", ["status", "source_level"])
    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("source_site_id", sa.CHAR(36), nullable=False),
        sa.Column("job_type", sa.String(32), nullable=False),
        sa.Column("trigger_type", sa.String(32), nullable=False),
        sa.Column("source_url", sa.String(1500)),
        sa.Column("input_object_key", sa.String(512)),
        sa.Column("dedupe_key", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("discovered_count", sa.Integer(), nullable=False),
        sa.Column("changed_count", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(100)),
        sa.Column("error_detail_safe", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", sa.CHAR(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_site_id"], ["source_sites.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.UniqueConstraint("dedupe_key", name="uq_ingestion_jobs_dedupe_key"),
    )
    op.create_index("ix_ingestion_jobs_status_created", "ingestion_jobs", ["status", "created_at"])
    op.create_index(
        "ix_ingestion_jobs_source_status", "ingestion_jobs", ["source_site_id", "status"]
    )
    op.create_table(
        "knowledge_candidate_batches",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("document_version_id", sa.CHAR(36), nullable=False),
        sa.Column("extraction_method", sa.String(32), nullable=False),
        sa.Column("extractor_version", sa.String(100), nullable=False),
        sa.Column("model_name", sa.String(100)),
        sa.Column("prompt_version", sa.String(100)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("candidate_count", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.CHAR(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_version_id"], ["document_versions.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
    )
    op.create_index(
        "ix_candidate_batches_document_status",
        "knowledge_candidate_batches",
        ["document_version_id", "status"],
    )
    op.create_table(
        "knowledge_candidates",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("batch_id", sa.CHAR(36), nullable=False),
        sa.Column("candidate_type", sa.String(32), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("source_document_id", sa.CHAR(36), nullable=False),
        sa.Column("source_chunk_id", sa.String(100), nullable=False),
        sa.Column("extraction_method", sa.String(32), nullable=False),
        sa.Column("extraction_confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("normalization_status", sa.String(32), nullable=False),
        sa.Column("review_status", sa.String(32), nullable=False),
        sa.Column("review_reason_safe", sa.String(1000)),
        sa.Column("content_hash", sa.CHAR(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["knowledge_candidate_batches.id"]),
        sa.ForeignKeyConstraint(["source_document_id"], ["source_documents.id"]),
        sa.ForeignKeyConstraint(["source_chunk_id"], ["document_chunks.source_chunk_id"]),
        sa.UniqueConstraint("batch_id", "content_hash", name="uq_candidates_batch_hash"),
    )
    op.create_index(
        "ix_candidates_review_type", "knowledge_candidates", ["review_status", "candidate_type"]
    )
    op.create_index(
        "ix_candidates_source_chunk",
        "knowledge_candidates",
        ["source_document_id", "source_chunk_id"],
    )
    op.create_table(
        "knowledge_publish_batches",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("batch_type", sa.String(32), nullable=False),
        sa.Column("scope", sa.String(32), nullable=False),
        sa.Column("org_id", sa.CHAR(36)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("candidate_count", sa.Integer(), nullable=False),
        sa.Column("approved_count", sa.Integer(), nullable=False),
        sa.Column("rejected_count", sa.Integer(), nullable=False),
        sa.Column("validation_report_json", sa.JSON(), nullable=False),
        sa.Column("manifest_hash", sa.CHAR(64)),
        sa.Column("submitted_by", sa.CHAR(36), nullable=False),
        sa.Column("approved_by", sa.CHAR(36)),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["submitted_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"]),
    )
    op.create_index(
        "ix_publish_batches_scope_status",
        "knowledge_publish_batches",
        ["scope", "org_id", "status"],
    )
    op.create_table(
        "knowledge_publish_batch_items",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("batch_id", sa.CHAR(36), nullable=False),
        sa.Column("candidate_id", sa.CHAR(36), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("checksum", sa.CHAR(64), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["knowledge_publish_batches.id"]),
        sa.ForeignKeyConstraint(["candidate_id"], ["knowledge_candidates.id"]),
        sa.UniqueConstraint("batch_id", "candidate_id", name="uq_publish_items_batch_candidate"),
    )
    op.create_table(
        "knowledge_snapshots",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("org_id", sa.CHAR(36)),
        sa.Column("snapshot_code", sa.String(64), nullable=False),
        sa.Column("snapshot_type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("base_snapshot_id", sa.CHAR(36)),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("manifest_hash", sa.CHAR(64), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True)),
        sa.Column("activated_by", sa.CHAR(36)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["base_snapshot_id"], ["knowledge_snapshots.id"]),
        sa.ForeignKeyConstraint(["activated_by"], ["users.id"]),
        sa.UniqueConstraint("snapshot_code", name="uq_knowledge_snapshots_code"),
    )
    op.create_index(
        "ix_knowledge_snapshots_scope_status",
        "knowledge_snapshots",
        ["snapshot_type", "org_id", "status"],
    )
    op.create_table(
        "knowledge_snapshot_items",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("snapshot_id", sa.CHAR(36), nullable=False),
        sa.Column("item_type", sa.String(32), nullable=False),
        sa.Column("item_id", sa.CHAR(36), nullable=False),
        sa.Column("item_version", sa.String(100), nullable=False),
        sa.Column("checksum", sa.CHAR(64), nullable=False),
        sa.ForeignKeyConstraint(["snapshot_id"], ["knowledge_snapshots.id"]),
        sa.UniqueConstraint(
            "snapshot_id", "item_type", "item_id", name="uq_snapshot_items_identity"
        ),
    )
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("aggregate_type", sa.String(64), nullable=False),
        sa.Column("aggregate_id", sa.CHAR(36), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("dedupe_key", sa.String(160), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("locked_by", sa.String(100)),
        sa.Column("locked_at", sa.DateTime(timezone=True)),
        sa.Column("last_error_safe", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("dedupe_key", name="uq_outbox_events_dedupe_key"),
    )
    op.create_index("ix_outbox_events_status_next", "outbox_events", ["status", "next_attempt_at"])
    op.create_index(
        "ix_outbox_events_aggregate", "outbox_events", ["aggregate_type", "aggregate_id"]
    )
    op.create_table(
        "projection_sync_states",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("projection_type", sa.String(32), nullable=False),
        sa.Column("aggregate_type", sa.String(64), nullable=False),
        sa.Column("aggregate_id", sa.CHAR(36), nullable=False),
        sa.Column("source_version", sa.String(100), nullable=False),
        sa.Column("target_version", sa.String(100), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("last_event_id", sa.CHAR(36)),
        sa.Column("synced_at", sa.DateTime(timezone=True)),
        sa.Column("error_safe", sa.Text()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["last_event_id"], ["outbox_events.id"]),
        sa.UniqueConstraint(
            "projection_type",
            "aggregate_type",
            "aggregate_id",
            "source_version",
            "target_version",
            name="uq_projection_sync_identity",
        ),
    )
    op.create_index(
        "ix_projection_sync_status",
        "projection_sync_states",
        ["projection_type", "status"],
    )


def downgrade() -> None:
    op.drop_table("projection_sync_states")
    op.drop_table("outbox_events")
    op.drop_table("knowledge_snapshot_items")
    op.drop_table("knowledge_snapshots")
    op.drop_table("knowledge_publish_batch_items")
    op.drop_table("knowledge_publish_batches")
    op.drop_table("knowledge_candidates")
    op.drop_table("knowledge_candidate_batches")
    op.drop_table("ingestion_jobs")
    op.drop_table("source_sites")

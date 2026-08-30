"""create versioned source document and clause tables

Revision ID: 20260830_0004
Revises: 20260830_0003
Create Date: 2026-08-30 15:20:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260830_0004"
down_revision: str | None = "20260830_0003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "source_documents",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("canonical_key", sa.String(255), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("doc_no", sa.String(200)),
        sa.Column("doc_type", sa.String(64), nullable=False),
        sa.Column("source_level", sa.String(32), nullable=False),
        sa.Column("issuing_authority", sa.String(200), nullable=False),
        sa.Column("region_code", sa.String(6), nullable=False),
        sa.Column("publish_date", sa.Date()),
        sa.Column("effective_start", sa.Date()),
        sa.Column("effective_end", sa.Date()),
        sa.Column("policy_status", sa.String(32), nullable=False),
        sa.Column("canonical_url", sa.String(1500), nullable=False),
        sa.Column("current_version_id", sa.CHAR(36)),
        sa.Column("review_status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.CHAR(36), nullable=False),
        sa.Column("updated_by", sa.CHAR(36), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.UniqueConstraint("canonical_key", name="uq_source_documents_canonical_key"),
    )
    op.create_index("ix_source_documents_doc_no", "source_documents", ["doc_no"])
    op.create_index(
        "ix_source_documents_scope",
        "source_documents",
        ["region_code", "policy_status", "effective_start", "effective_end"],
    )
    op.create_index(
        "ix_source_documents_level_type", "source_documents", ["source_level", "doc_type"]
    )
    op.create_table(
        "document_versions",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("document_id", sa.CHAR(36), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_url", sa.String(1500), nullable=False),
        sa.Column("raw_object_key", sa.String(512)),
        sa.Column("parsed_object_key", sa.String(512)),
        sa.Column("mime_type", sa.String(128), nullable=False),
        sa.Column("http_etag", sa.String(255)),
        sa.Column("last_modified_header", sa.String(255)),
        sa.Column("content_hash_sha256", sa.CHAR(64), nullable=False),
        sa.Column("parser_version", sa.String(64)),
        sa.Column("parse_status", sa.String(32), nullable=False),
        sa.Column("ocr_status", sa.String(32), nullable=False),
        sa.Column("review_status", sa.String(32), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("supersedes_version_id", sa.CHAR(36)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.CHAR(36), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["source_documents.id"]),
        sa.ForeignKeyConstraint(["supersedes_version_id"], ["document_versions.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.UniqueConstraint("document_id", "version_no", name="uq_document_versions_document_no"),
        sa.UniqueConstraint("document_id", "content_hash_sha256", name="uq_document_versions_hash"),
    )
    op.create_index(
        "ix_document_versions_document_review", "document_versions", ["document_id", "review_status"]
    )
    op.create_foreign_key(
        "fk_source_documents_current_version",
        "source_documents",
        "document_versions",
        ["current_version_id"],
        ["id"],
    )
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("document_id", sa.CHAR(36), nullable=False),
        sa.Column("document_version_id", sa.CHAR(36), nullable=False),
        sa.Column("source_chunk_id", sa.String(100), nullable=False),
        sa.Column("parent_chunk_id", sa.CHAR(36)),
        sa.Column("chunk_order", sa.Integer(), nullable=False),
        sa.Column("chunk_type", sa.String(32), nullable=False),
        sa.Column("heading_path", sa.String(1000), nullable=False),
        sa.Column("clause_label", sa.String(100)),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("content_hash_sha256", sa.CHAR(64), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("char_start", sa.Integer()),
        sa.Column("char_end", sa.Integer()),
        sa.Column("effective_start", sa.Date()),
        sa.Column("effective_end", sa.Date()),
        sa.Column("region_code", sa.String(6), nullable=False),
        sa.Column("policy_status", sa.String(32), nullable=False),
        sa.Column("review_status", sa.String(32), nullable=False),
        sa.Column("index_status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["source_documents.id"]),
        sa.ForeignKeyConstraint(["document_version_id"], ["document_versions.id"]),
        sa.ForeignKeyConstraint(["parent_chunk_id"], ["document_chunks.id"]),
        sa.UniqueConstraint("source_chunk_id", name="uq_document_chunks_source_chunk_id"),
    )
    op.create_index(
        "ix_document_chunks_version_order", "document_chunks", ["document_version_id", "chunk_order"]
    )
    op.create_index("ix_document_chunks_document_clause", "document_chunks", ["document_id", "clause_label"])
    op.create_index(
        "ix_document_chunks_search_scope",
        "document_chunks",
        ["review_status", "policy_status", "region_code"],
    )


def downgrade() -> None:
    op.drop_table("document_chunks")
    op.drop_constraint(
        "fk_source_documents_current_version", "source_documents", type_="foreignkey"
    )
    op.drop_table("document_versions")
    op.drop_table("source_documents")

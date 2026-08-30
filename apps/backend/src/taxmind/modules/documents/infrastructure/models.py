from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    CHAR,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from taxmind.infrastructure.mysql.base import Base
from taxmind.shared.domain.ids import new_id


class SourceDocumentModel(Base):
    __tablename__ = "source_documents"
    __table_args__ = (
        UniqueConstraint("canonical_key", name="uq_source_documents_canonical_key"),
        Index("ix_source_documents_doc_no", "doc_no"),
        Index(
            "ix_source_documents_scope",
            "region_code",
            "policy_status",
            "effective_start",
            "effective_end",
        ),
        Index("ix_source_documents_level_type", "source_level", "doc_type"),
    )

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=new_id)
    canonical_key: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    doc_no: Mapped[str | None] = mapped_column(String(200))
    doc_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_level: Mapped[str] = mapped_column(String(32), nullable=False)
    issuing_authority: Mapped[str] = mapped_column(String(200), nullable=False)
    region_code: Mapped[str] = mapped_column(String(6), nullable=False)
    publish_date: Mapped[date | None] = mapped_column(Date)
    effective_start: Mapped[date | None] = mapped_column(Date)
    effective_end: Mapped[date | None] = mapped_column(Date)
    policy_status: Mapped[str] = mapped_column(String(32), nullable=False)
    canonical_url: Mapped[str] = mapped_column(String(1500), nullable=False)
    current_version_id: Mapped[str | None] = mapped_column(
        CHAR(36), ForeignKey("document_versions.id")
    )
    review_status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id"), nullable=False)
    updated_by: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id"), nullable=False)


class DocumentVersionModel(Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version_no", name="uq_document_versions_document_no"),
        UniqueConstraint("document_id", "content_hash_sha256", name="uq_document_versions_hash"),
        Index("ix_document_versions_document_review", "document_id", "review_status"),
    )

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=new_id)
    document_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("source_documents.id"), nullable=False
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_url: Mapped[str] = mapped_column(String(1500), nullable=False)
    raw_object_key: Mapped[str | None] = mapped_column(String(512))
    parsed_object_key: Mapped[str | None] = mapped_column(String(512))
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    http_etag: Mapped[str | None] = mapped_column(String(255))
    last_modified_header: Mapped[str | None] = mapped_column(String(255))
    content_hash_sha256: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    parser_version: Mapped[str | None] = mapped_column(String(64))
    parse_status: Mapped[str] = mapped_column(String(32), nullable=False)
    ocr_status: Mapped[str] = mapped_column(String(32), nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    supersedes_version_id: Mapped[str | None] = mapped_column(
        CHAR(36), ForeignKey("document_versions.id")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id"), nullable=False)


class DocumentChunkModel(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("source_chunk_id", name="uq_document_chunks_source_chunk_id"),
        Index("ix_document_chunks_version_order", "document_version_id", "chunk_order"),
        Index("ix_document_chunks_document_clause", "document_id", "clause_label"),
        Index("ix_document_chunks_search_scope", "review_status", "policy_status", "region_code"),
    )

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=new_id)
    document_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("source_documents.id"), nullable=False
    )
    document_version_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("document_versions.id"), nullable=False
    )
    source_chunk_id: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_chunk_id: Mapped[str | None] = mapped_column(CHAR(36), ForeignKey("document_chunks.id"))
    chunk_order: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_type: Mapped[str] = mapped_column(String(32), nullable=False)
    heading_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    clause_label: Mapped[str | None] = mapped_column(String(100))
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash_sha256: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    char_start: Mapped[int | None] = mapped_column(Integer)
    char_end: Mapped[int | None] = mapped_column(Integer)
    effective_start: Mapped[date | None] = mapped_column(Date)
    effective_end: Mapped[date | None] = mapped_column(Date)
    region_code: Mapped[str] = mapped_column(String(6), nullable=False)
    policy_status: Mapped[str] = mapped_column(String(32), nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False)
    index_status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

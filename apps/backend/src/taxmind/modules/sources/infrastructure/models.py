from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CHAR,
    JSON,
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


class SourceSiteModel(Base):
    __tablename__ = "source_sites"
    __table_args__ = (
        UniqueConstraint("domain", "region_code", name="uq_source_sites_domain_region"),
        Index("ix_source_sites_status_level", "status", "source_level"),
    )

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    base_url: Mapped[str] = mapped_column(String(1500), nullable=False)
    domain: Mapped[str] = mapped_column(String(253), nullable=False)
    source_level: Mapped[str] = mapped_column(String(32), nullable=False)
    authority_name: Mapped[str] = mapped_column(String(200), nullable=False)
    region_code: Mapped[str] = mapped_column(String(6), nullable=False)
    collection_method: Mapped[str] = mapped_column(String(32), nullable=False)
    whitelist_rules_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    crawl_interval_minutes: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class IngestionJobModel(Base):
    __tablename__ = "ingestion_jobs"
    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_ingestion_jobs_dedupe_key"),
        Index("ix_ingestion_jobs_status_created", "status", "created_at"),
        Index("ix_ingestion_jobs_source_status", "source_site_id", "status"),
    )

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=new_id)
    source_site_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("source_sites.id"), nullable=False
    )
    job_type: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1500))
    input_object_key: Mapped[str | None] = mapped_column(String(512))
    dedupe_key: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False)
    discovered_count: Mapped[int] = mapped_column(Integer, nullable=False)
    changed_count: Mapped[int] = mapped_column(Integer, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_detail_safe: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

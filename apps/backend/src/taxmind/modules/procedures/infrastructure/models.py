from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import CHAR, JSON, Date, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from taxmind.infrastructure.mysql.base import Base
from taxmind.shared.domain.ids import new_id


class ProcedureVersionModel(Base):
    __tablename__ = "procedure_versions"
    __table_args__ = (
        Index(
            "ix_procedure_versions_published_scope",
            "review_status",
            "region_code",
            "effective_start",
            "effective_end",
        ),
        Index(
            "ix_procedure_versions_code_version",
            "procedure_code",
            "version_no",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=new_id)
    procedure_code: Mapped[str] = mapped_column(String(100), nullable=False)
    version_no: Mapped[int] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    region_code: Mapped[str] = mapped_column(String(6), nullable=False)
    effective_start: Mapped[date | None] = mapped_column(Date)
    effective_end: Mapped[date | None] = mapped_column(Date)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False)
    official_url: Mapped[str] = mapped_column(String(1500), nullable=False)
    source_chunk_ids_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    materials_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    channels_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_by: Mapped[str] = mapped_column(CHAR(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

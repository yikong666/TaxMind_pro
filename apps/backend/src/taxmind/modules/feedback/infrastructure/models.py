from __future__ import annotations

from datetime import datetime

from sqlalchemy import CHAR, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from taxmind.infrastructure.mysql.base import Base
from taxmind.shared.domain.ids import new_id


class FeedbackItemModel(Base):
    __tablename__ = "feedback_items"
    __table_args__ = (
        Index(
            "ix_feedback_items_org_submitter_submitted", "org_id", "submitted_by", "submitted_at"
        ),
        Index("ix_feedback_items_org_status_submitted", "org_id", "status", "submitted_at"),
        Index("ix_feedback_items_resource", "resource_type", "resource_id"),
    )

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=new_id)
    org_id: Mapped[str] = mapped_column(CHAR(36), nullable=False)
    case_id: Mapped[str | None] = mapped_column(CHAR(36), ForeignKey("consultation_cases.id"))
    profile_version: Mapped[int | None] = mapped_column(Integer)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str] = mapped_column(CHAR(36), nullable=False)
    location_key: Mapped[str | None] = mapped_column(String(128))
    error_type: Mapped[str] = mapped_column(String(32), nullable=False)
    description_safe: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    linked_knowledge_object_id: Mapped[str | None] = mapped_column(CHAR(36))
    resolution_safe: Mapped[str | None] = mapped_column(String(1000))
    submitted_by: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id"), nullable=False)
    handled_by: Mapped[str | None] = mapped_column(CHAR(36), ForeignKey("users.id"))
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

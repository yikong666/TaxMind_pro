from __future__ import annotations

from datetime import datetime

from sqlalchemy import CHAR, JSON, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from taxmind.infrastructure.mysql.base import Base
from taxmind.shared.domain.ids import new_id


class ReviewTaskModel(Base):
    __tablename__ = "review_tasks"
    __table_args__ = (
        Index("ix_review_tasks_org_status_submitted", "org_id", "status", "submitted_at"),
        Index("ix_review_tasks_case_profile", "case_id", "profile_version"),
    )

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=new_id)
    org_id: Mapped[str] = mapped_column(CHAR(36), nullable=False)
    case_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("consultation_cases.id"),
        nullable=False,
    )
    profile_version: Mapped[int] = mapped_column(Integer, nullable=False)
    query_run_id: Mapped[str | None] = mapped_column(CHAR(36))
    submitted_by: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id"), nullable=False)
    assigned_to: Mapped[str | None] = mapped_column(CHAR(36), ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    priority: Mapped[str] = mapped_column(String(32), nullable=False)
    package_summary: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReviewActionModel(Base):
    __tablename__ = "review_actions"
    __table_args__ = (UniqueConstraint("task_id", "action_no", name="uq_review_actions_task_no"),)

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=new_id)
    task_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("review_tasks.id"),
        nullable=False,
    )
    action_no: Mapped[int] = mapped_column(Integer, nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    comment_safe: Mapped[str | None] = mapped_column(String(1000))
    actor_user_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id"), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

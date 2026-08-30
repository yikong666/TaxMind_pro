from datetime import datetime

from sqlalchemy import CHAR, JSON, DateTime, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from taxmind.infrastructure.mysql.base import Base
from taxmind.shared.domain.ids import new_id


class AuditLogModel(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_org_occurred", "org_id", "occurred_at"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
        UniqueConstraint("request_id", "id", name="uq_audit_logs_request_id_id"),
    )

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=new_id)
    org_id: Mapped[str | None] = mapped_column(CHAR(36))
    actor_user_id: Mapped[str | None] = mapped_column(CHAR(36))
    action_code: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(CHAR(36))
    request_id: Mapped[str] = mapped_column(CHAR(36), nullable=False)
    result: Mapped[str] = mapped_column(String(32), nullable=False)
    ip_hash: Mapped[str | None] = mapped_column(CHAR(64))
    user_agent_hash: Mapped[str | None] = mapped_column(CHAR(64))
    before_json: Mapped[dict[str, object] | None] = mapped_column(JSON)
    after_json: Mapped[dict[str, object] | None] = mapped_column(JSON)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

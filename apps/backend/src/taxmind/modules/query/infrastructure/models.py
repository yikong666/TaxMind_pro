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
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import Mapped, mapped_column

from taxmind.infrastructure.mysql.base import Base
from taxmind.shared.domain.ids import new_id


class AnalysisRunModel(Base):
    __tablename__ = "analysis_runs"
    __table_args__ = (
        UniqueConstraint("org_id", "idempotency_key", name="uq_analysis_runs_org_idempotency"),
        Index("ix_analysis_runs_org_case_created", "org_id", "case_id", "created_at"),
        Index("ix_analysis_runs_status_created", "status", "created_at"),
    )

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=new_id)
    org_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("organizations.id"), nullable=False)
    case_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("consultation_cases.id"), nullable=False
    )
    conversation_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("conversations.id"), nullable=False
    )
    request_message_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("messages.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    profile_version: Mapped[int] = mapped_column(Integer, nullable=False)
    query_text: Mapped[str] = mapped_column(
        Text().with_variant(MEDIUMTEXT(), "mysql"), nullable=False
    )
    facts_snapshot_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    public_knowledge_snapshot_id: Mapped[str | None] = mapped_column(
        CHAR(36), ForeignKey("knowledge_snapshots.id")
    )
    org_knowledge_snapshot_id: Mapped[str | None] = mapped_column(
        CHAR(36), ForeignKey("knowledge_snapshots.id")
    )
    retrieval_plan_json: Mapped[dict[str, object] | None] = mapped_column(JSON)
    rule_results_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    rule_version_ids_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    evidence_ids_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    follow_up_fact_keys_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    degradation_events_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    model_profile_id: Mapped[str | None] = mapped_column(String(100))
    prompt_bundle_version: Mapped[str | None] = mapped_column(String(100))
    router_version: Mapped[str] = mapped_column(String(64), nullable=False)
    retrieval_config_version: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    request_id: Mapped[str] = mapped_column(String(100), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_detail_safe: Mapped[str | None] = mapped_column(Text)
    final_answer_message_id: Mapped[str | None] = mapped_column(CHAR(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AnalysisRunEventModel(Base):
    __tablename__ = "analysis_run_events"
    __table_args__ = (
        UniqueConstraint("run_id", "sequence_no", name="uq_analysis_run_events_sequence"),
        Index("ix_analysis_run_events_run_sequence", "run_id", "sequence_no"),
    )

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("analysis_runs.id"), nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    payload_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

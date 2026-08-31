from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CHAR,
    JSON,
    BigInteger,
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


class ConversationModel(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conversations_org_case_last", "org_id", "case_id", "last_message_at"),
    )

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=new_id)
    org_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("organizations.id"), nullable=False)
    case_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("consultation_cases.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    started_by: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id"), nullable=False)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    summary_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MessageModel(Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint(
            "conversation_id", "sequence_no", name="uq_messages_conversation_sequence"
        ),
        UniqueConstraint(
            "conversation_id", "idempotency_key", name="uq_messages_conversation_idempotency"
        ),
        Index("ix_messages_org_case_created", "org_id", "case_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=new_id)
    org_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("organizations.id"), nullable=False)
    conversation_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("conversations.id"), nullable=False
    )
    case_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("consultation_cases.id"), nullable=False
    )
    sequence_no: Mapped[int] = mapped_column(BigInteger, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content_text: Mapped[str] = mapped_column(
        Text().with_variant(MEDIUMTEXT(), "mysql"), nullable=False
    )
    content_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    run_id: Mapped[str | None] = mapped_column(CHAR(36))
    parent_message_id: Mapped[str | None] = mapped_column(CHAR(36), ForeignKey("messages.id"))
    visibility: Mapped[str] = mapped_column(String(32), nullable=False)
    content_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    redaction_status: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ConversationSummaryModel(Base):
    __tablename__ = "conversation_summaries"
    __table_args__ = (
        UniqueConstraint(
            "conversation_id", "summary_version", name="uq_conversation_summaries_version"
        ),
    )

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=new_id)
    org_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("organizations.id"), nullable=False)
    conversation_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("conversations.id"), nullable=False
    )
    summary_version: Mapped[int] = mapped_column(Integer, nullable=False)
    covered_from_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    covered_to_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    confirmed_facts_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    open_questions_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    generated_by_model_version: Mapped[str | None] = mapped_column(String(100))
    review_status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

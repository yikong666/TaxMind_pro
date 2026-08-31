"""create conversations, messages and summary tables

Revision ID: 20260831_0005
Revises: 20260830_0004
Create Date: 2026-08-31 01:15:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "20260831_0005"
down_revision: str | None = "20260830_0004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("org_id", sa.CHAR(36), nullable=False),
        sa.Column("case_id", sa.CHAR(36), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("started_by", sa.CHAR(36), nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True)),
        sa.Column("summary_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["case_id"], ["consultation_cases.id"]),
        sa.ForeignKeyConstraint(["started_by"], ["users.id"]),
    )
    op.create_index(
        "ix_conversations_org_case_last",
        "conversations",
        ["org_id", "case_id", "last_message_at"],
    )
    op.create_table(
        "messages",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("org_id", sa.CHAR(36), nullable=False),
        sa.Column("conversation_id", sa.CHAR(36), nullable=False),
        sa.Column("case_id", sa.CHAR(36), nullable=False),
        sa.Column("sequence_no", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("content_text", mysql.MEDIUMTEXT(), nullable=False),
        sa.Column("content_json", sa.JSON(), nullable=False),
        sa.Column("run_id", sa.CHAR(36)),
        sa.Column("parent_message_id", sa.CHAR(36)),
        sa.Column("visibility", sa.String(32), nullable=False),
        sa.Column("content_hash", sa.CHAR(64), nullable=False),
        sa.Column("redaction_status", sa.String(32), nullable=False),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["case_id"], ["consultation_cases.id"]),
        sa.ForeignKeyConstraint(["parent_message_id"], ["messages.id"]),
        sa.UniqueConstraint(
            "conversation_id", "sequence_no", name="uq_messages_conversation_sequence"
        ),
        sa.UniqueConstraint(
            "conversation_id", "idempotency_key", name="uq_messages_conversation_idempotency"
        ),
    )
    op.create_index("ix_messages_org_case_created", "messages", ["org_id", "case_id", "created_at"])
    op.create_table(
        "conversation_summaries",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("org_id", sa.CHAR(36), nullable=False),
        sa.Column("conversation_id", sa.CHAR(36), nullable=False),
        sa.Column("summary_version", sa.Integer(), nullable=False),
        sa.Column("covered_from_sequence", sa.BigInteger(), nullable=False),
        sa.Column("covered_to_sequence", sa.BigInteger(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("confirmed_facts_json", sa.JSON(), nullable=False),
        sa.Column("open_questions_json", sa.JSON(), nullable=False),
        sa.Column("generated_by_model_version", sa.String(100)),
        sa.Column("review_status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.UniqueConstraint(
            "conversation_id", "summary_version", name="uq_conversation_summaries_version"
        ),
    )


def downgrade() -> None:
    op.drop_table("conversation_summaries")
    op.drop_table("messages")
    op.drop_table("conversations")

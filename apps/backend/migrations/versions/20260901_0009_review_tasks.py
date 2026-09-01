"""add case review tasks and append-only actions

Revision ID: 20260901_0009
Revises: 20260901_0008
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260901_0009"
down_revision: str | None = "20260901_0008"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "review_tasks",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("org_id", sa.CHAR(36), nullable=False),
        sa.Column("case_id", sa.CHAR(36), sa.ForeignKey("consultation_cases.id"), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        sa.Column("query_run_id", sa.CHAR(36)),
        sa.Column("submitted_by", sa.CHAR(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("assigned_to", sa.CHAR(36), sa.ForeignKey("users.id")),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("priority", sa.String(32), nullable=False),
        sa.Column("package_summary", sa.JSON(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_review_tasks_org_status_submitted", "review_tasks", ["org_id", "status", "submitted_at"]
    )
    op.create_index("ix_review_tasks_case_profile", "review_tasks", ["case_id", "profile_version"])
    op.create_table(
        "review_actions",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("task_id", sa.CHAR(36), sa.ForeignKey("review_tasks.id"), nullable=False),
        sa.Column("action_no", sa.Integer(), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("comment_safe", sa.String(1000)),
        sa.Column("actor_user_id", sa.CHAR(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("task_id", "action_no", name="uq_review_actions_task_no"),
    )


def downgrade() -> None:
    op.drop_table("review_actions")
    op.drop_table("review_tasks")

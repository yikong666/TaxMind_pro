"""add feedback items for correction workflow

Revision ID: 20260901_0010
Revises: 20260901_0009
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260901_0010"
down_revision: str | None = "20260901_0009"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "feedback_items",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("org_id", sa.CHAR(36), nullable=False),
        sa.Column("case_id", sa.CHAR(36), sa.ForeignKey("consultation_cases.id")),
        sa.Column("profile_version", sa.Integer()),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.CHAR(36), nullable=False),
        sa.Column("location_key", sa.String(128)),
        sa.Column("error_type", sa.String(32), nullable=False),
        sa.Column("description_safe", sa.String(1000), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("linked_knowledge_object_id", sa.CHAR(36)),
        sa.Column("resolution_safe", sa.String(1000)),
        sa.Column("submitted_by", sa.CHAR(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("handled_by", sa.CHAR(36), sa.ForeignKey("users.id")),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_feedback_items_org_submitter_submitted",
        "feedback_items",
        ["org_id", "submitted_by", "submitted_at"],
    )
    op.create_index(
        "ix_feedback_items_org_status_submitted",
        "feedback_items",
        ["org_id", "status", "submitted_at"],
    )
    op.create_index(
        "ix_feedback_items_resource", "feedback_items", ["resource_type", "resource_id"]
    )


def downgrade() -> None:
    op.drop_table("feedback_items")

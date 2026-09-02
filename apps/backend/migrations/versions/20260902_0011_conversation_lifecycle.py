"""add governed conversation lifecycle

Revision ID: 20260902_0011
Revises: 20260901_0010
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260902_0011"
down_revision: str | None = "20260901_0010"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_conversations_org_status_updated",
        "conversations",
        ["org_id", "status", "updated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_conversations_org_status_updated", table_name="conversations")
    op.drop_column("conversations", "deleted_at")

"""add knowledge candidate reviewer traceability

Revision ID: 20260831_0007
Revises: 20260831_0006
Create Date: 2026-08-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260831_0007"
down_revision: str | None = "20260831_0006"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "knowledge_candidates",
        sa.Column("reviewed_by", sa.CHAR(length=36), nullable=True),
    )
    op.add_column(
        "knowledge_candidates",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_knowledge_candidates_reviewed_by_users",
        "knowledge_candidates",
        "users",
        ["reviewed_by"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_knowledge_candidates_reviewed_by_users",
        "knowledge_candidates",
        type_="foreignkey",
    )
    op.drop_column("knowledge_candidates", "reviewed_at")
    op.drop_column("knowledge_candidates", "reviewed_by")

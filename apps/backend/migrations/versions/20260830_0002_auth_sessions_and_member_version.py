"""add revocable auth sessions and member optimistic locking

Revision ID: 20260830_0002
Revises: 20260830_0001
Create Date: 2026-08-30 00:20:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260830_0002"
down_revision: str | None = "20260830_0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "organization_members",
        sa.Column("version_no", sa.Integer(), nullable=False, server_default="1"),
    )
    op.alter_column("organization_members", "version_no", server_default=None)
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("user_id", sa.CHAR(36), nullable=False),
        sa.Column("org_id", sa.CHAR(36), nullable=False),
        sa.Column("refresh_token_hash", sa.CHAR(64), nullable=False),
        sa.Column("device_label", sa.String(120)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.UniqueConstraint("refresh_token_hash", name="uq_auth_sessions_refresh_token_hash"),
    )
    op.create_index("ix_auth_sessions_user_expires", "auth_sessions", ["user_id", "expires_at"])
    op.create_index("ix_auth_sessions_org_expires", "auth_sessions", ["org_id", "expires_at"])


def downgrade() -> None:
    op.drop_table("auth_sessions")
    op.drop_column("organization_members", "version_no")

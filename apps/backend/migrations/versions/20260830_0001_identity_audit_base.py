"""create identity and audit base tables

Revision ID: 20260830_0001
Revises:
Create Date: 2026-08-30 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260830_0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("settings_json", sa.JSON(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.UniqueConstraint("code", name="uq_organizations_code"),
    )
    op.create_index("ix_organizations_status", "organizations", ["status"])
    op.create_table(
        "users",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("email", sa.String(254)),
        sa.Column("mobile_hash", sa.CHAR(64)),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_mobile_hash", "users", ["mobile_hash"])
    op.create_index("ix_users_status", "users", ["status"])
    op.create_table(
        "organization_members",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("org_id", sa.CHAR(36), nullable=False),
        sa.Column("user_id", sa.CHAR(36), nullable=False),
        sa.Column("role_code", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("org_id", "user_id", name="uq_organization_members_org_user"),
    )
    op.create_index(
        "ix_organization_members_scope", "organization_members", ["org_id", "role_code", "status"]
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("org_id", sa.CHAR(36)),
        sa.Column("actor_user_id", sa.CHAR(36)),
        sa.Column("action_code", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.CHAR(36)),
        sa.Column("request_id", sa.CHAR(36), nullable=False),
        sa.Column("result", sa.String(32), nullable=False),
        sa.Column("ip_hash", sa.CHAR(64)),
        sa.Column("user_agent_hash", sa.CHAR(64)),
        sa.Column("before_json", sa.JSON()),
        sa.Column("after_json", sa.JSON()),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("request_id", "id", name="uq_audit_logs_request_id_id"),
    )
    op.create_index("ix_audit_logs_org_occurred", "audit_logs", ["org_id", "occurred_at"])
    op.create_index("ix_audit_logs_resource", "audit_logs", ["resource_type", "resource_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("organization_members")
    op.drop_table("users")
    op.drop_table("organizations")

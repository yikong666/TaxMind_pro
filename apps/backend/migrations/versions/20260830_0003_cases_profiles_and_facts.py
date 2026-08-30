"""create case, subject profile and fact snapshot tables

Revision ID: 20260830_0003
Revises: 20260830_0002
Create Date: 2026-08-30 13:20:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260830_0003"
down_revision: str | None = "20260830_0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "consultation_cases",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("org_id", sa.CHAR(36), nullable=False),
        sa.Column("case_no", sa.String(64), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("owner_user_id", sa.CHAR(36), nullable=False),
        sa.Column("reviewer_user_id", sa.CHAR(36)),
        sa.Column("default_region_code", sa.String(6), nullable=False),
        sa.Column("current_profile_version", sa.Integer(), nullable=False),
        sa.Column("current_draft_id", sa.CHAR(36)),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.CHAR(36)),
        sa.Column("updated_by", sa.CHAR(36)),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"]),
        sa.UniqueConstraint("org_id", "case_no", name="uq_consultation_cases_org_case_no"),
    )
    op.create_index(
        "ix_consultation_cases_org_scope",
        "consultation_cases",
        ["org_id", "status", "owner_user_id", "updated_at"],
    )
    op.create_table(
        "case_subject_profiles",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("org_id", sa.CHAR(36), nullable=False),
        sa.Column("case_id", sa.CHAR(36), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        sa.Column("legal_form_code", sa.String(64), nullable=False),
        sa.Column("vat_taxpayer_type", sa.String(64), nullable=False),
        sa.Column("small_low_profit_status", sa.String(16), nullable=False),
        sa.Column("industry_code", sa.String(64), nullable=False),
        sa.Column("region_code", sa.String(6), nullable=False),
        sa.Column("business_date", sa.Date(), nullable=False),
        sa.Column("business_action_codes_json", sa.JSON(), nullable=False),
        sa.Column("extra_attributes_json", sa.JSON(), nullable=False),
        sa.Column("data_classification", sa.String(32), nullable=False),
        sa.Column("confirmation_status", sa.String(32), nullable=False),
        sa.Column("confirmed_by", sa.CHAR(36)),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("supersedes_profile_id", sa.CHAR(36)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.CHAR(36)),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["case_id"], ["consultation_cases.id"]),
        sa.ForeignKeyConstraint(["supersedes_profile_id"], ["case_subject_profiles.id"]),
        sa.UniqueConstraint("case_id", "profile_version", name="uq_case_profiles_case_version"),
    )
    op.create_index(
        "ix_case_subject_profiles_org_case",
        "case_subject_profiles",
        ["org_id", "case_id", "profile_version"],
    )
    op.create_table(
        "case_facts",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("org_id", sa.CHAR(36), nullable=False),
        sa.Column("case_id", sa.CHAR(36), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        sa.Column("fact_key", sa.String(100), nullable=False),
        sa.Column("value_type", sa.String(32), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=False),
        sa.Column("unit", sa.String(32)),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("source_message_id", sa.CHAR(36)),
        sa.Column("confirmation_status", sa.String(32), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4)),
        sa.Column("effective_date", sa.Date()),
        sa.Column("confirmed_by", sa.CHAR(36)),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["case_id"], ["consultation_cases.id"]),
    )
    op.create_index(
        "ix_case_facts_org_case_profile",
        "case_facts",
        ["org_id", "case_id", "profile_version", "fact_key", "confirmation_status"],
    )


def downgrade() -> None:
    op.drop_table("case_facts")
    op.drop_table("case_subject_profiles")
    op.drop_table("consultation_cases")

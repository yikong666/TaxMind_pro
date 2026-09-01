"""add published procedure guidance versions

Revision ID: 20260901_0008
Revises: 20260831_0007
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260901_0008"
down_revision: str | None = "20260831_0007"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "procedure_versions",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("procedure_code", sa.String(100), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("region_code", sa.String(6), nullable=False),
        sa.Column("effective_start", sa.Date()),
        sa.Column("effective_end", sa.Date()),
        sa.Column("review_status", sa.String(32), nullable=False),
        sa.Column("official_url", sa.String(1500), nullable=False),
        sa.Column("source_chunk_ids_json", sa.JSON(), nullable=False),
        sa.Column("materials_json", sa.JSON(), nullable=False),
        sa.Column("channels_json", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.CHAR(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "procedure_code",
            "version_no",
            name="uq_procedure_versions_code_version",
        ),
    )
    op.create_index(
        "ix_procedure_versions_published_scope",
        "procedure_versions",
        ["review_status", "region_code", "effective_start", "effective_end"],
    )


def downgrade() -> None:
    op.drop_table("procedure_versions")

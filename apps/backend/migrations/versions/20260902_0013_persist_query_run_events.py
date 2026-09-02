"""persist replayable query run events

Revision ID: 20260902_0013
Revises: 20260902_0012
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260902_0013"
down_revision: str | None = "20260902_0012"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analysis_run_events",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("run_id", sa.CHAR(36), sa.ForeignKey("analysis_runs.id"), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_id", "sequence_no", name="uq_analysis_run_events_sequence"),
    )
    op.create_index(
        "ix_analysis_run_events_run_sequence",
        "analysis_run_events",
        ["run_id", "sequence_no"],
    )


def downgrade() -> None:
    op.drop_index("ix_analysis_run_events_run_sequence", table_name="analysis_run_events")
    op.drop_table("analysis_run_events")

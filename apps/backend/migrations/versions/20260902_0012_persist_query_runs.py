"""persist governed query runs and final answer links

Revision ID: 20260902_0012
Revises: 20260902_0011
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260902_0012"
down_revision: str | None = "20260902_0011"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analysis_runs",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("org_id", sa.CHAR(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("case_id", sa.CHAR(36), sa.ForeignKey("consultation_cases.id"), nullable=False),
        sa.Column(
            "conversation_id",
            sa.CHAR(36),
            sa.ForeignKey("conversations.id"),
            nullable=False,
        ),
        sa.Column("request_message_id", sa.CHAR(36), sa.ForeignKey("messages.id"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("facts_snapshot_json", sa.JSON(), nullable=False),
        sa.Column(
            "public_knowledge_snapshot_id",
            sa.CHAR(36),
            sa.ForeignKey("knowledge_snapshots.id"),
        ),
        sa.Column(
            "org_knowledge_snapshot_id",
            sa.CHAR(36),
            sa.ForeignKey("knowledge_snapshots.id"),
        ),
        sa.Column("retrieval_plan_json", sa.JSON()),
        sa.Column("rule_results_json", sa.JSON(), nullable=False),
        sa.Column("rule_version_ids_json", sa.JSON(), nullable=False),
        sa.Column("evidence_ids_json", sa.JSON(), nullable=False),
        sa.Column("follow_up_fact_keys_json", sa.JSON(), nullable=False),
        sa.Column("degradation_events_json", sa.JSON(), nullable=False),
        sa.Column("model_profile_id", sa.String(100)),
        sa.Column("prompt_bundle_version", sa.String(100)),
        sa.Column("router_version", sa.String(64), nullable=False),
        sa.Column("retrieval_config_version", sa.String(64), nullable=False),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("request_id", sa.String(100), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("error_code", sa.String(100)),
        sa.Column("error_detail_safe", sa.Text()),
        sa.Column("final_answer_message_id", sa.CHAR(36)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("org_id", "idempotency_key", name="uq_analysis_runs_org_idempotency"),
    )
    op.create_index(
        "ix_analysis_runs_org_case_created",
        "analysis_runs",
        ["org_id", "case_id", "created_at"],
    )
    op.create_index(
        "ix_analysis_runs_status_created",
        "analysis_runs",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_analysis_runs_status_created", table_name="analysis_runs")
    op.drop_index("ix_analysis_runs_org_case_created", table_name="analysis_runs")
    op.drop_table("analysis_runs")

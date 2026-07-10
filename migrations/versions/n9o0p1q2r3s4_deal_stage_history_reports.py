"""deal stage history and forecast snapshots for sales reports

Revision ID: n9o0p1q2r3s4
Revises: m8n9o0p1q2r3
Create Date: 2026-07-10
"""

from alembic import op
import sqlalchemy as sa

revision = "n9o0p1q2r3s4"
down_revision = "m8n9o0p1q2r3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "deal_stage_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("deal_id", sa.Integer(), sa.ForeignKey("deals.id"), nullable=False),
        sa.Column("from_stage", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("to_stage", sa.String(length=50), nullable=False),
        sa.Column("changed_at", sa.DateTime(), nullable=True),
        sa.Column("changed_by", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("event_type", sa.String(length=32), nullable=False, server_default="transition"),
        sa.Column("reason_code", sa.String(length=64), nullable=False, server_default=""),
    )
    op.create_index("ix_deal_stage_history_deal_id", "deal_stage_history", ["deal_id"])
    op.create_index("ix_deal_stage_history_to_stage", "deal_stage_history", ["to_stage"])
    op.create_index("ix_deal_stage_history_changed_at", "deal_stage_history", ["changed_at"])
    op.create_index("ix_deal_stage_history_event_type", "deal_stage_history", ["event_type"])

    op.create_table(
        "forecast_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scope_key", sa.String(length=120), nullable=False),
        sa.Column("period_start", sa.DateTime(), nullable=False),
        sa.Column("period_end", sa.DateTime(), nullable=False),
        sa.Column("as_of", sa.DateTime(), nullable=True),
        sa.Column("weighted_forecast", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("open_pipeline", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("open_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("agent_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_forecast_snapshots_scope_key", "forecast_snapshots", ["scope_key"])
    op.create_index(
        "ix_forecast_snapshots_scope_period",
        "forecast_snapshots",
        ["scope_key", "period_start", "period_end"],
        unique=True,
    )


def downgrade():
    op.drop_index("ix_forecast_snapshots_scope_period", table_name="forecast_snapshots")
    op.drop_index("ix_forecast_snapshots_scope_key", table_name="forecast_snapshots")
    op.drop_table("forecast_snapshots")
    op.drop_index("ix_deal_stage_history_event_type", table_name="deal_stage_history")
    op.drop_index("ix_deal_stage_history_changed_at", table_name="deal_stage_history")
    op.drop_index("ix_deal_stage_history_to_stage", table_name="deal_stage_history")
    op.drop_index("ix_deal_stage_history_deal_id", table_name="deal_stage_history")
    op.drop_table("deal_stage_history")

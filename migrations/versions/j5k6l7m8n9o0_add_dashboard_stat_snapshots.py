"""Add dashboard_stat_snapshots for MoM trend history

Revision ID: j5k6l7m8n9o0
Revises: i4j5k6l7m8n9
Create Date: 2026-07-10
"""

from alembic import op
import sqlalchemy as sa

revision = "j5k6l7m8n9o0"
down_revision = "i4j5k6l7m8n9"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "dashboard_stat_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("total_properties", sa.Integer(), server_default="0"),
        sa.Column("active_properties", sa.Integer(), server_default="0"),
        sa.Column("total_agents", sa.Integer(), server_default="0"),
        sa.Column("total_customers", sa.Integer(), server_default="0"),
        sa.Column("total_deals", sa.Integer(), server_default="0"),
        sa.Column("active_deals", sa.Integer(), server_default="0"),
        sa.Column("total_deal_value", sa.BigInteger(), server_default="0"),
        sa.Column("active_deal_value", sa.BigInteger(), server_default="0"),
        sa.Column("avg_property_price", sa.Integer(), server_default="0"),
        sa.Column("recent_properties_count", sa.Integer(), server_default="0"),
        sa.Column("recent_deals_count", sa.Integer(), server_default="0"),
    )
    op.create_index(
        "ix_dashboard_stat_snapshots_timestamp",
        "dashboard_stat_snapshots",
        ["timestamp"],
    )


def downgrade():
    op.drop_index("ix_dashboard_stat_snapshots_timestamp", "dashboard_stat_snapshots")
    op.drop_table("dashboard_stat_snapshots")

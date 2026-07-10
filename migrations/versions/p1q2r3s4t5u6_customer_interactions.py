"""customer interactions and activity audit for Customer 360

Revision ID: p1q2r3s4t5u6
Revises: o0p1q2r3s4t5
Create Date: 2026-07-10
"""

from alembic import op
import sqlalchemy as sa

revision = "p1q2r3s4t5u6"
down_revision = "o0p1q2r3s4t5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "customer_interactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("interaction_type", sa.String(length=32), nullable=False),
        sa.Column("subject", sa.String(length=200), server_default=""),
        sa.Column("body", sa.Text(), server_default=""),
        sa.Column("outcome", sa.String(length=64), server_default=""),
        sa.Column("occurred_at", sa.DateTime(), nullable=True),
        sa.Column("follow_up_at", sa.DateTime(), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("actor_label", sa.String(length=120), server_default=""),
        sa.Column("related_deal_id", sa.Integer(), sa.ForeignKey("deals.id"), nullable=True),
        sa.Column("related_property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=True),
        sa.Column("follow_up_task_id", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("source", sa.String(length=20), server_default="manual"),
    )
    op.create_index("ix_customer_interactions_customer_id", "customer_interactions", ["customer_id"])
    op.create_index("ix_customer_interactions_type", "customer_interactions", ["interaction_type"])
    op.create_index("ix_customer_interactions_occurred_at", "customer_interactions", ["occurred_at"])
    op.create_index("ix_customer_interactions_follow_up_at", "customer_interactions", ["follow_up_at"])
    op.create_index("ix_customer_interactions_is_deleted", "customer_interactions", ["is_deleted"])

    op.create_table(
        "activity_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("actor_label", sa.String(length=120), server_default=""),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("interaction_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("changed_fields", sa.String(length=255), server_default=""),
        sa.Column("request_id", sa.String(length=64), server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_activity_audit_logs_customer_id", "activity_audit_logs", ["customer_id"])
    op.create_index("ix_activity_audit_logs_interaction_id", "activity_audit_logs", ["interaction_id"])
    op.create_index("ix_activity_audit_logs_action", "activity_audit_logs", ["action"])
    op.create_index("ix_activity_audit_logs_created_at", "activity_audit_logs", ["created_at"])


def downgrade():
    op.drop_index("ix_activity_audit_logs_created_at", table_name="activity_audit_logs")
    op.drop_index("ix_activity_audit_logs_action", table_name="activity_audit_logs")
    op.drop_index("ix_activity_audit_logs_interaction_id", table_name="activity_audit_logs")
    op.drop_index("ix_activity_audit_logs_customer_id", table_name="activity_audit_logs")
    op.drop_table("activity_audit_logs")
    op.drop_index("ix_customer_interactions_is_deleted", table_name="customer_interactions")
    op.drop_index("ix_customer_interactions_follow_up_at", table_name="customer_interactions")
    op.drop_index("ix_customer_interactions_occurred_at", table_name="customer_interactions")
    op.drop_index("ix_customer_interactions_type", table_name="customer_interactions")
    op.drop_index("ix_customer_interactions_customer_id", table_name="customer_interactions")
    op.drop_table("customer_interactions")

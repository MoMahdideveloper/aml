"""Add client_messages and open_house_checkins tables.

Revision ID: g2h3i4j5k6l7
Revises: f1a2b3c4d5e6
Create Date: 2026-07-09 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "g2h3i4j5k6l7"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "client_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("direction", sa.String(length=20), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_client_messages_customer_id", "client_messages", ["customer_id"])
    op.create_index("ix_client_messages_created_at", "client_messages", ["created_at"])

    op.create_table(
        "open_house_checkins",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=40), nullable=False),
        sa.Column("status_tags", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_open_house_checkins_property_id", "open_house_checkins", ["property_id"])
    op.create_index("ix_open_house_checkins_created_at", "open_house_checkins", ["created_at"])


def downgrade():
    op.drop_index("ix_open_house_checkins_created_at", table_name="open_house_checkins")
    op.drop_index("ix_open_house_checkins_property_id", table_name="open_house_checkins")
    op.drop_table("open_house_checkins")
    op.drop_index("ix_client_messages_created_at", table_name="client_messages")
    op.drop_index("ix_client_messages_customer_id", table_name="client_messages")
    op.drop_table("client_messages")

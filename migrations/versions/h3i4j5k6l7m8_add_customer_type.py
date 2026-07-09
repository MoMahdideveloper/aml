"""Add customer_type for buyer/seller opportunities

Revision ID: h3i4j5k6l7m8
Revises: g2h3i4j5k6l7
Create Date: 2026-07-09
"""

from alembic import op
import sqlalchemy as sa


revision = "h3i4j5k6l7m8"
down_revision = "g2h3i4j5k6l7"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("customers") as batch_op:
        batch_op.add_column(
            sa.Column("customer_type", sa.String(length=20), nullable=True, server_default="buyer")
        )


def downgrade():
    with op.batch_alter_table("customers") as batch_op:
        batch_op.drop_column("customer_type")

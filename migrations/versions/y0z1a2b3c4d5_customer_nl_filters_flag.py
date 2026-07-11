"""add customer_nl_filters toggle to intelligence settings

Revision ID: y0z1a2b3c4d5
Revises: x9y0z1a2b3c4
Create Date: 2026-07-11
"""

from alembic import op
import sqlalchemy as sa

revision = "y0z1a2b3c4d5"
down_revision = "x9y0z1a2b3c4"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("intelligence_settings") as batch:
        batch.add_column(
            sa.Column("customer_nl_filters", sa.Boolean(), server_default=sa.false())
        )


def downgrade():
    with op.batch_alter_table("intelligence_settings") as batch:
        batch.drop_column("customer_nl_filters")

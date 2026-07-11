"""add activity_search toggle to intelligence settings

Revision ID: z1a2b3c4d5e6
Revises: y0z1a2b3c4d5
Create Date: 2026-07-11
"""

from alembic import op
import sqlalchemy as sa

revision = "z1a2b3c4d5e6"
down_revision = "y0z1a2b3c4d5"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("intelligence_settings") as batch:
        batch.add_column(
            sa.Column("activity_search", sa.Boolean(), server_default=sa.false())
        )


def downgrade():
    with op.batch_alter_table("intelligence_settings") as batch:
        batch.drop_column("activity_search")

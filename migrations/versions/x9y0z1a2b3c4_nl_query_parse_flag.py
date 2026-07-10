"""add nl_query_parse toggle to intelligence settings

Revision ID: x9y0z1a2b3c4
Revises: w8x9y0z1a2b3
Create Date: 2026-07-11
"""

from alembic import op
import sqlalchemy as sa

revision = "x9y0z1a2b3c4"
down_revision = "w8x9y0z1a2b3"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("intelligence_settings") as batch:
        batch.add_column(sa.Column("nl_query_parse", sa.Boolean(), server_default=sa.false()))


def downgrade():
    with op.batch_alter_table("intelligence_settings") as batch:
        batch.drop_column("nl_query_parse")

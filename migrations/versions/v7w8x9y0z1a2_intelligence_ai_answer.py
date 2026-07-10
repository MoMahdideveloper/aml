"""add ai_answer toggle to intelligence settings

Revision ID: v7w8x9y0z1a2
Revises: u6v7w8x9y0z1
Create Date: 2026-07-11
"""

from alembic import op
import sqlalchemy as sa

revision = "v7w8x9y0z1a2"
down_revision = "u6v7w8x9y0z1"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("intelligence_settings") as batch:
        batch.add_column(sa.Column("ai_answer", sa.Boolean(), server_default=sa.false()))


def downgrade():
    with op.batch_alter_table("intelligence_settings") as batch:
        batch.drop_column("ai_answer")

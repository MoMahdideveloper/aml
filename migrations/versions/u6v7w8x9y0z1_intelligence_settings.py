"""intelligence settings singleton for admin toggles

Revision ID: u6v7w8x9y0z1
Revises: t5u6v7w8x9y0
Create Date: 2026-07-11
"""

from alembic import op
import sqlalchemy as sa

revision = "u6v7w8x9y0z1"
down_revision = "t5u6v7w8x9y0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "intelligence_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("vocab_enrichment", sa.Boolean(), server_default=sa.false()),
        sa.Column("vocab_occurrences", sa.Boolean(), server_default=sa.false()),
        sa.Column("hybrid_search", sa.Boolean(), server_default=sa.false()),
        sa.Column("ai_context", sa.Boolean(), server_default=sa.false()),
        sa.Column("derived_edges", sa.Boolean(), server_default=sa.false()),
        sa.Column("global_search", sa.Boolean(), server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("updated_by", sa.String(length=120), server_default=""),
    )


def downgrade():
    op.drop_table("intelligence_settings")

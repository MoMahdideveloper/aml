"""residual intelligence: shadow flag, description search, related terms

Revision ID: w8x9y0z1a2b3
Revises: v7w8x9y0z1a2
Create Date: 2026-07-11
"""

from alembic import op
import sqlalchemy as sa

revision = "w8x9y0z1a2b3"
down_revision = "v7w8x9y0z1a2"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("intelligence_settings") as batch:
        batch.add_column(sa.Column("search_shadow", sa.Boolean(), server_default=sa.false()))
        batch.add_column(
            sa.Column("description_search", sa.Boolean(), server_default=sa.false())
        )

    op.create_table(
        "vocab_related_terms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("term_id", sa.Integer(), sa.ForeignKey("vocab_terms.id"), nullable=False),
        sa.Column("related_key", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("term_id", "related_key", name="uq_vocab_related_term_key"),
    )
    op.create_index("ix_vocab_related_terms_related_key", "vocab_related_terms", ["related_key"])


def downgrade():
    op.drop_table("vocab_related_terms")
    with op.batch_alter_table("intelligence_settings") as batch:
        batch.drop_column("description_search")
        batch.drop_column("search_shadow")

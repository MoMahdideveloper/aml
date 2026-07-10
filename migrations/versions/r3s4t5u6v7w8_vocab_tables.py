"""vocab terms, synonyms, and directional replacements

Revision ID: r3s4t5u6v7w8
Revises: q2r3s4t5u6v7
Create Date: 2026-07-11
"""

from alembic import op
import sqlalchemy as sa

revision = "r3s4t5u6v7w8"
down_revision = "q2r3s4t5u6v7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "vocab_terms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("canonical", sa.String(length=120), nullable=False),
        sa.Column("normalized_key", sa.String(length=120), nullable=False),
        sa.Column("lang", sa.String(length=8), server_default="en"),
        sa.Column("status", sa.String(length=20), server_default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_vocab_terms_normalized_key", "vocab_terms", ["normalized_key"], unique=True)
    op.create_index("ix_vocab_terms_status", "vocab_terms", ["status"])

    op.create_table(
        "vocab_synonyms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("term_id", sa.Integer(), sa.ForeignKey("vocab_terms.id"), nullable=False),
        sa.Column("synonym_key", sa.String(length=120), nullable=False),
        sa.Column("bidirectional", sa.Boolean(), server_default=sa.true()),
        sa.Column("status", sa.String(length=20), server_default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("term_id", "synonym_key", name="uq_vocab_synonym_term_key"),
    )
    op.create_index("ix_vocab_synonyms_synonym_key", "vocab_synonyms", ["synonym_key"])
    op.create_index("ix_vocab_synonyms_status", "vocab_synonyms", ["status"])

    op.create_table(
        "vocab_replacements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("from_key", sa.String(length=120), nullable=False),
        sa.Column("to_key", sa.String(length=120), nullable=False),
        sa.Column("priority", sa.Integer(), server_default="0"),
        sa.Column("status", sa.String(length=20), server_default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("from_key", "to_key", name="uq_vocab_replacement_from_to"),
    )
    op.create_index("ix_vocab_replacements_from_key", "vocab_replacements", ["from_key"])
    op.create_index("ix_vocab_replacements_status", "vocab_replacements", ["status"])


def downgrade():
    op.drop_table("vocab_replacements")
    op.drop_table("vocab_synonyms")
    op.drop_table("vocab_terms")

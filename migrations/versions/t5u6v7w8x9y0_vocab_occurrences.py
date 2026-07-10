"""vocab term occurrences for extraction index

Revision ID: t5u6v7w8x9y0
Revises: s4t5u6v7w8x9
Create Date: 2026-07-11
"""

from alembic import op
import sqlalchemy as sa

revision = "t5u6v7w8x9y0"
down_revision = "s4t5u6v7w8x9"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "vocab_occurrences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_type", sa.String(length=20), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("field", sa.String(length=40), nullable=False),
        sa.Column("term_id", sa.Integer(), sa.ForeignKey("vocab_terms.id"), nullable=True),
        sa.Column("normalized_key", sa.String(length=120), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="1.0"),
        sa.Column("status", sa.String(length=20), server_default="active"),
        sa.Column("source_hash", sa.String(length=64), server_default=""),
        sa.Column("extracted_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "entity_type",
            "entity_id",
            "field",
            "normalized_key",
            name="uq_vocab_occurrence_entity_field_key",
        ),
    )
    op.create_index(
        "ix_vocab_occurrences_entity",
        "vocab_occurrences",
        ["entity_type", "entity_id"],
    )
    op.create_index("ix_vocab_occurrences_normalized_key", "vocab_occurrences", ["normalized_key"])
    op.create_index("ix_vocab_occurrences_status", "vocab_occurrences", ["status"])

    # Optional edge metadata for v2 graph
    with op.batch_alter_table("relationship_edges") as batch:
        batch.add_column(sa.Column("confidence", sa.Float(), server_default="1.0"))
        batch.add_column(sa.Column("derivation_version", sa.String(length=20), server_default="1"))


def downgrade():
    with op.batch_alter_table("relationship_edges") as batch:
        batch.drop_column("derivation_version")
        batch.drop_column("confidence")
    op.drop_table("vocab_occurrences")

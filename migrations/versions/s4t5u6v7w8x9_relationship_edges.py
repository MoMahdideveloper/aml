"""SQL relationship edges for CRM explainability

Revision ID: s4t5u6v7w8x9
Revises: r3s4t5u6v7w8
Create Date: 2026-07-11
"""

from alembic import op
import sqlalchemy as sa

revision = "s4t5u6v7w8x9"
down_revision = "r3s4t5u6v7w8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "relationship_edges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("src_type", sa.String(length=20), nullable=False),
        sa.Column("src_id", sa.Integer(), nullable=False),
        sa.Column("dst_type", sa.String(length=20), nullable=False),
        sa.Column("dst_id", sa.Integer(), nullable=False),
        sa.Column("edge_type", sa.String(length=40), nullable=False),
        sa.Column("weight", sa.Float(), server_default="1.0"),
        sa.Column("evidence_json", sa.Text(), server_default=""),
        sa.Column("computed_at", sa.DateTime(), nullable=True),
        sa.Column("source_run_id", sa.String(length=64), server_default=""),
        sa.UniqueConstraint(
            "src_type",
            "src_id",
            "dst_type",
            "dst_id",
            "edge_type",
            name="uq_relationship_edge_endpoints",
        ),
    )
    op.create_index(
        "ix_relationship_edges_src",
        "relationship_edges",
        ["src_type", "src_id"],
    )
    op.create_index(
        "ix_relationship_edges_dst",
        "relationship_edges",
        ["dst_type", "dst_id"],
    )
    op.create_index("ix_relationship_edges_edge_type", "relationship_edges", ["edge_type"])


def downgrade():
    op.drop_table("relationship_edges")

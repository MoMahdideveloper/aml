"""add saved_views for unified search

Revision ID: m8n9o0p1q2r3
Revises: l7m8n9o0p1q2
Create Date: 2026-07-10
"""

from alembic import op
import sqlalchemy as sa

revision = "m8n9o0p1q2r3"
down_revision = "l7m8n9o0p1q2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "saved_views",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("entity_scope", sa.String(length=32), nullable=False),
        sa.Column("filter_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("sort_spec", sa.String(length=32), nullable=False, server_default="relevance"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_saved_views_owner_user_id", "saved_views", ["owner_user_id"])
    op.create_index("ix_saved_views_entity_scope", "saved_views", ["entity_scope"])
    op.create_index(
        "ix_saved_views_owner_scope_name",
        "saved_views",
        ["owner_user_id", "entity_scope", "name"],
        unique=True,
    )


def downgrade():
    op.drop_index("ix_saved_views_owner_scope_name", table_name="saved_views")
    op.drop_index("ix_saved_views_entity_scope", table_name="saved_views")
    op.drop_index("ix_saved_views_owner_user_id", table_name="saved_views")
    op.drop_table("saved_views")

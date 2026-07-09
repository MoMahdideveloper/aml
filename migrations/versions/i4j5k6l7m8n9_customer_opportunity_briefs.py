"""Customer opportunity briefs (multiple needs per client)

Revision ID: i4j5k6l7m8n9
Revises: h3i4j5k6l7m8
Create Date: 2026-07-09
"""

from alembic import op
import sqlalchemy as sa


revision = "i4j5k6l7m8n9"
down_revision = "h3i4j5k6l7m8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "customer_opportunity_briefs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False, server_default="Opportunity"),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="buyer"),
        sa.Column("budget_min", sa.BigInteger(), server_default="0"),
        sa.Column("budget_max", sa.BigInteger(), server_default="0"),
        sa.Column("preferred_bedrooms", sa.Integer(), server_default="0"),
        sa.Column("preferred_bathrooms", sa.Integer(), server_default="0"),
        sa.Column("preferred_type", sa.String(length=50), server_default=""),
        sa.Column("location_preference", sa.String(length=255), server_default=""),
        sa.Column("preferences", sa.Text(), server_default=""),
        sa.Column("related_property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=True),
        sa.Column("exchange_notes", sa.Text(), server_default=""),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1")),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )
    op.create_index(
        "ix_customer_opportunity_briefs_customer_id",
        "customer_opportunity_briefs",
        ["customer_id"],
    )
    with op.batch_alter_table("property_matches") as batch_op:
        batch_op.add_column(sa.Column("brief_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_property_matches_brief_id",
            "customer_opportunity_briefs",
            ["brief_id"],
            ["id"],
        )


def downgrade():
    with op.batch_alter_table("property_matches") as batch_op:
        batch_op.drop_constraint("fk_property_matches_brief_id", type_="foreignkey")
        batch_op.drop_column("brief_id")
    op.drop_index("ix_customer_opportunity_briefs_customer_id", "customer_opportunity_briefs")
    op.drop_table("customer_opportunity_briefs")

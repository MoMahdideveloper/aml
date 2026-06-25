"""Add Maskan custom property fields.

Revision ID: a6d1c2e3f4a5
Revises: f1a2b3c4d5e6
Create Date: 2026-02-12 23:40:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a6d1c2e3f4a5"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("properties", schema=None) as batch_op:
        batch_op.add_column(sa.Column("floor_covering", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("facade_type", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("wall_covering", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("cabinet_type", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("property_direction", sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column("is_exchangeable", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("boundary_width", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("density", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("commercial_status", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("usage_type", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("ceiling_count", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("permit_ceiling", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("property_length", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("property_height", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("price_per_meter", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("custom_fields", sa.Text(), nullable=False, server_default=""))

    with op.batch_alter_table("properties", schema=None) as batch_op:
        batch_op.alter_column("is_exchangeable", server_default=None)
        batch_op.alter_column("custom_fields", server_default=None)


def downgrade():
    with op.batch_alter_table("properties", schema=None) as batch_op:
        batch_op.drop_column("custom_fields")
        batch_op.drop_column("price_per_meter")
        batch_op.drop_column("property_height")
        batch_op.drop_column("property_length")
        batch_op.drop_column("permit_ceiling")
        batch_op.drop_column("ceiling_count")
        batch_op.drop_column("usage_type")
        batch_op.drop_column("commercial_status")
        batch_op.drop_column("density")
        batch_op.drop_column("boundary_width")
        batch_op.drop_column("is_exchangeable")
        batch_op.drop_column("property_direction")
        batch_op.drop_column("cabinet_type")
        batch_op.drop_column("wall_covering")
        batch_op.drop_column("facade_type")
        batch_op.drop_column("floor_covering")

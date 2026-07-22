"""Allow properties.price to be NULL (rentals use rahn/ejare).

Revision ID: a0b1c2d3e4f5
Revises: b2c3d4e5f6a7
Create Date: 2026-07-17 11:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "a0b1c2d3e4f5"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("properties") as batch:
        batch.alter_column(
            "price",
            existing_type=sa.BigInteger(),
            nullable=True,
            existing_nullable=False,
            server_default=None,
        )


def downgrade() -> None:
    # Coerce NULL → 0 before re-applying NOT NULL.
    op.execute("UPDATE properties SET price = 0 WHERE price IS NULL")
    with op.batch_alter_table("properties") as batch:
        batch.alter_column(
            "price",
            existing_type=sa.BigInteger(),
            nullable=False,
            existing_nullable=True,
            server_default="0",
        )

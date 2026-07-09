"""Merge divergent Alembic heads for a single upgrade path

Revision ID: k6l7m8n9o0p1
Revises: j5k6l7m8n9o0, e8f9a0b1c2d3, 20250825_add_indexes
Create Date: 2026-07-10
"""

# Merge only — no schema changes.
revision = "k6l7m8n9o0p1"
down_revision = ("j5k6l7m8n9o0", "e8f9a0b1c2d3", "20250825_add_indexes")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass

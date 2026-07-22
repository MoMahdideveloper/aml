"""Add missing properties columns used by Property model.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-15

Columns were present on the ORM (sqlalchemy_models.Property) but never
migrated, causing dashboard/property queries to fail on Postgres with
UndefinedColumn: properties.is_ai_extracted (and related gap-fill fields).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def _existing_columns(table: str) -> set[str]:
    bind = op.get_bind()
    return {c["name"] for c in inspect(bind).get_columns(table)}


def upgrade():
    existing = _existing_columns("properties")
    with op.batch_alter_table("properties", schema=None) as batch_op:
        if "is_ai_extracted" not in existing:
            batch_op.add_column(
                sa.Column(
                    "is_ai_extracted",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.false(),
                )
            )
        if "source" not in existing:
            batch_op.add_column(
                sa.Column(
                    "source",
                    sa.String(length=20),
                    nullable=False,
                    server_default="manual",
                )
            )
        if "file_code" not in existing:
            batch_op.add_column(sa.Column("file_code", sa.String(length=20), nullable=True))
        if "floor_number" not in existing:
            batch_op.add_column(sa.Column("floor_number", sa.Integer(), nullable=True))
        if "has_storage" not in existing:
            batch_op.add_column(
                sa.Column(
                    "has_storage",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.false(),
                )
            )
        if "has_elevator" not in existing:
            batch_op.add_column(
                sa.Column(
                    "has_elevator",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.false(),
                )
            )
        if "document_type" not in existing:
            batch_op.add_column(sa.Column("document_type", sa.String(length=50), nullable=True))
        if "built_area" not in existing:
            batch_op.add_column(sa.Column("built_area", sa.Integer(), nullable=True))
        if "land_area" not in existing:
            batch_op.add_column(sa.Column("land_area", sa.Integer(), nullable=True))

    # Unique on file_code (nullable allowed) if not already present
    existing_idxs = {ix["name"] for ix in inspect(op.get_bind()).get_indexes("properties")}
    if "file_code" in _existing_columns("properties") and "ix_properties_file_code" not in existing_idxs:
        # Some DBs already have a unique constraint under another name; skip if column unique fails later.
        try:
            op.create_index("ix_properties_file_code", "properties", ["file_code"], unique=True)
        except Exception:
            pass

    # Drop server defaults after backfill so ORM defaults own the contract
    with op.batch_alter_table("properties", schema=None) as batch_op:
        if "is_ai_extracted" in _existing_columns("properties"):
            batch_op.alter_column("is_ai_extracted", server_default=None)
        if "source" in _existing_columns("properties"):
            batch_op.alter_column("source", server_default=None)
        if "has_storage" in _existing_columns("properties"):
            batch_op.alter_column("has_storage", server_default=None)
        if "has_elevator" in _existing_columns("properties"):
            batch_op.alter_column("has_elevator", server_default=None)


def downgrade():
    existing = _existing_columns("properties")
    existing_idxs = {ix["name"] for ix in inspect(op.get_bind()).get_indexes("properties")}
    if "ix_properties_file_code" in existing_idxs:
        op.drop_index("ix_properties_file_code", table_name="properties")
    with op.batch_alter_table("properties", schema=None) as batch_op:
        for col in (
            "land_area",
            "built_area",
            "document_type",
            "has_elevator",
            "has_storage",
            "floor_number",
            "file_code",
            "source",
            "is_ai_extracted",
        ):
            if col in existing:
                batch_op.drop_column(col)

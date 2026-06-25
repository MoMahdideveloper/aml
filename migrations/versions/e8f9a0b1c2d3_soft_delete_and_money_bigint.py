"""Add soft-delete fields and migrate money columns to BigInteger (toman).

Revision ID: e8f9a0b1c2d3
Revises: f1a2b3c4d5e6
Create Date: 2026-02-17 16:32:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e8f9a0b1c2d3"
down_revision = "a6d1c2e3f4a5"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _table_exists(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = _inspector()
    if table_name not in inspector.get_table_names():
        return False
    return column_name in {col["name"] for col in inspector.get_columns(table_name)}


def _index_exists(table_name: str, index_name: str) -> bool:
    inspector = _inspector()
    if table_name not in inspector.get_table_names():
        return False
    return index_name in {idx["name"] for idx in inspector.get_indexes(table_name)}


def _alter_money_column(table_name: str, column_name: str, nullable: bool) -> None:
    if not _column_exists(table_name, column_name):
        return

    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute(
            sa.text(
                f"""
                ALTER TABLE {table_name}
                ALTER COLUMN {column_name}
                TYPE BIGINT
                USING (
                    CASE
                        WHEN {column_name} IS NULL THEN NULL
                        ELSE ROUND({column_name})::BIGINT
                    END
                )
                """
            )
        )
        return

    with op.batch_alter_table(table_name) as batch_op:
        batch_op.alter_column(
            column_name,
            existing_type=sa.Float(),
            type_=sa.BigInteger(),
            existing_nullable=nullable,
            nullable=nullable,
        )


def _revert_money_column(table_name: str, column_name: str, nullable: bool) -> None:
    if not _column_exists(table_name, column_name):
        return

    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute(
            sa.text(
                f"""
                ALTER TABLE {table_name}
                ALTER COLUMN {column_name}
                TYPE DOUBLE PRECISION
                USING (
                    CASE
                        WHEN {column_name} IS NULL THEN NULL
                        ELSE {column_name}::DOUBLE PRECISION
                    END
                )
                """
            )
        )
        return

    with op.batch_alter_table(table_name) as batch_op:
        batch_op.alter_column(
            column_name,
            existing_type=sa.BigInteger(),
            type_=sa.Float(),
            existing_nullable=nullable,
            nullable=nullable,
        )


def upgrade():
    core_tables = ["properties", "customers", "agents", "deals", "tasks"]
    for table_name in core_tables:
        if not _table_exists(table_name):
            continue
        with op.batch_alter_table(table_name) as batch_op:
            if not _column_exists(table_name, "is_deleted"):
                batch_op.add_column(
                    sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false())
                )
            if not _column_exists(table_name, "deleted_at"):
                batch_op.add_column(sa.Column("deleted_at", sa.DateTime(), nullable=True))
        index_name = f"ix_{table_name}_is_deleted"
        if not _index_exists(table_name, index_name):
            op.create_index(index_name, table_name, ["is_deleted"], unique=False)

    # Monetary fields now use integer toman to avoid overflow/precision issues.
    _alter_money_column("properties", "price", nullable=False)
    _alter_money_column("properties", "rahn", nullable=True)
    _alter_money_column("properties", "ejare", nullable=True)
    _alter_money_column("properties", "rental_price", nullable=True)
    _alter_money_column("properties", "price_per_meter", nullable=True)
    _alter_money_column("customers", "budget_min", nullable=False)
    _alter_money_column("customers", "budget_max", nullable=False)
    _alter_money_column("deals", "offer_amount", nullable=False)
    _alter_money_column("public_property_submissions", "price", nullable=True)
    _alter_money_column("public_property_submissions", "rahn", nullable=True)
    _alter_money_column("public_property_submissions", "ejare", nullable=True)


def downgrade():
    _revert_money_column("public_property_submissions", "ejare", nullable=True)
    _revert_money_column("public_property_submissions", "rahn", nullable=True)
    _revert_money_column("public_property_submissions", "price", nullable=True)
    _revert_money_column("deals", "offer_amount", nullable=False)
    _revert_money_column("customers", "budget_max", nullable=False)
    _revert_money_column("customers", "budget_min", nullable=False)
    _revert_money_column("properties", "price_per_meter", nullable=True)
    _revert_money_column("properties", "rental_price", nullable=True)
    _revert_money_column("properties", "ejare", nullable=True)
    _revert_money_column("properties", "rahn", nullable=True)
    _revert_money_column("properties", "price", nullable=False)

    core_tables = ["tasks", "deals", "agents", "customers", "properties"]
    for table_name in core_tables:
        if not _table_exists(table_name):
            continue
        index_name = f"ix_{table_name}_is_deleted"
        if _index_exists(table_name, index_name):
            op.drop_index(index_name, table_name=table_name)
        with op.batch_alter_table(table_name) as batch_op:
            if _column_exists(table_name, "deleted_at"):
                batch_op.drop_column("deleted_at")
            if _column_exists(table_name, "is_deleted"):
                batch_op.drop_column("is_deleted")

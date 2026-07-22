"""Reconcile ORM schema gaps after the canonical migration head.

Revision ID: c3d4e5f6a7b8
Revises: a0b1c2d3e4f5
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "c3d4e5f6a7b8"
down_revision = "a0b1c2d3e4f5"
branch_labels = None
depends_on = None


CREATED_TABLES = (
    "suggestion_items",
    "analysis_templates",
    "analysis_reports",
    "builders",
    "customer_groups",
    "property_images",
    "property_activity_log",
    "contact_reveals",
    "public_property_submissions",
    "property_ai_history",
    "model_performance_metrics",
    "ai_metadata",
    "sync_state",
)


def _existing_tables() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def _create_missing_tables() -> None:
    existing = _existing_tables()

    if "suggestion_items" not in existing:
        op.create_table(
            "suggestion_items",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=255), nullable=False),
        )

    if "analysis_templates" not in existing:
        op.create_table(
            "analysis_templates",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("analysis_type", sa.String(length=50), nullable=False),
            sa.Column("configuration", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )

    if "analysis_reports" not in existing:
        op.create_table(
            "analysis_reports",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("template_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["template_id"], ["analysis_templates.id"], name="fk_analysis_reports_template_id"
            ),
        )

    if "builders" not in existing:
        op.create_table(
            "builders",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("company_name", sa.String(length=255), nullable=True),
            sa.Column("phone", sa.String(length=20), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=True),
            sa.Column("address", sa.Text(), nullable=True),
            sa.Column("speciality", sa.String(length=100), nullable=False, server_default="residential"),
            sa.Column("active_projects", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("completed_projects", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("rating", sa.Float(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    if "customer_groups" not in existing:
        op.create_table(
            "customer_groups",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("color", sa.String(length=7), nullable=False, server_default="#6366f1"),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("name", name="uq_customer_groups_name"),
        )

    if "property_images" not in existing:
        op.create_table(
            "property_images",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("property_id", sa.Integer(), nullable=False),
            sa.Column("filename", sa.String(length=255), nullable=False),
            sa.Column("caption", sa.String(length=255), nullable=True),
            sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["property_id"], ["properties.id"], name="fk_property_images_property_id"
            ),
        )

    if "property_activity_log" not in existing:
        op.create_table(
            "property_activity_log",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("property_id", sa.Integer(), nullable=False),
            sa.Column("action", sa.String(length=50), nullable=False),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("old_value", sa.Text(), nullable=True),
            sa.Column("new_value", sa.Text(), nullable=True),
            sa.Column("change_source", sa.String(length=20), nullable=False, server_default="manual"),
            sa.Column("changed_by", sa.String(length=100), nullable=True),
            sa.Column("sync_version", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["property_id"], ["properties.id"], name="fk_property_activity_log_property_id"
            ),
        )

    if "contact_reveals" not in existing:
        op.create_table(
            "contact_reveals",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("property_id", sa.Integer(), nullable=False),
            sa.Column("viewer_ip", sa.String(length=45), nullable=True),
            sa.Column("viewer_user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["property_id"], ["properties.id"], name="fk_contact_reveals_property_id"
            ),
        )

    if "public_property_submissions" not in existing:
        op.create_table(
            "public_property_submissions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("submitter_name", sa.String(length=255), nullable=False),
            sa.Column("submitter_phone", sa.String(length=20), nullable=False),
            sa.Column("submitter_email", sa.String(length=255), nullable=True),
            sa.Column("property_title", sa.String(length=255), nullable=False),
            sa.Column("property_type", sa.String(length=50), nullable=False, server_default="apartment"),
            sa.Column("listing_type", sa.String(length=20), nullable=False, server_default="sale"),
            sa.Column("address", sa.Text(), nullable=False),
            sa.Column("price", sa.BigInteger(), nullable=True),
            sa.Column("rahn", sa.BigInteger(), nullable=True),
            sa.Column("ejare", sa.BigInteger(), nullable=True),
            sa.Column("bedrooms", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("square_feet", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
            sa.Column("admin_notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    if "property_ai_history" not in existing:
        op.create_table(
            "property_ai_history",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("property_id", sa.Integer(), nullable=False),
            sa.Column("raw_data", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("user_note", sa.String(length=255), nullable=True),
            sa.ForeignKeyConstraint(
                ["property_id"], ["properties.id"], name="fk_property_ai_history_property_id"
            ),
        )

    if "model_performance_metrics" not in existing:
        op.create_table(
            "model_performance_metrics",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("model_name", sa.String(length=100), nullable=False),
            sa.Column("metric_type", sa.String(length=50), nullable=False),
            sa.Column("metric_value", sa.Float(), nullable=False),
            sa.Column("timestamp", sa.DateTime(), nullable=False),
            sa.Column("metadata_", sa.Text(), nullable=True),
        )

    if "ai_metadata" not in existing:
        op.create_table(
            "ai_metadata",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("operation_type", sa.String(length=100), nullable=False),
            sa.Column("model_name", sa.String(length=100), nullable=False),
            sa.Column("input_tokens", sa.Integer(), nullable=True),
            sa.Column("output_tokens", sa.Integer(), nullable=True),
            sa.Column("total_tokens", sa.Integer(), nullable=True),
            sa.Column("latency_ms", sa.Float(), nullable=True),
            sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("timestamp", sa.DateTime(), nullable=False),
            sa.Column("property_id", sa.Integer(), nullable=True),
            sa.Column("customer_id", sa.Integer(), nullable=True),
            sa.Column("deal_id", sa.Integer(), nullable=True),
            sa.Column("task_id", sa.Integer(), nullable=True),
            sa.Column("context_data", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["property_id"], ["properties.id"], name="fk_ai_metadata_property_id"),
            sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], name="fk_ai_metadata_customer_id"),
            sa.ForeignKeyConstraint(["deal_id"], ["deals.id"], name="fk_ai_metadata_deal_id"),
            sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], name="fk_ai_metadata_task_id"),
        )

    if "sync_state" not in existing:
        op.create_table(
            "sync_state",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("last_sync_at", sa.DateTime(), nullable=True),
            sa.Column("last_sync_cursor", sa.String(length=255), nullable=True),
            sa.Column("properties_synced", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("properties_created", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("properties_updated", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("fields_changed", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="idle"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("duration_seconds", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )


# Missing-column specs for existing tables. Each tuple is:
# (name, SQLAlchemy type, final nullable, temporary server default, backfill SQL).
EXISTING_TABLE_COLUMNS = {
    "suggestion_items": (("name", sa.String(length=255), False, "", ""),),
    "analysis_templates": (
        ("name", sa.String(length=255), False, "", ""),
        ("description", sa.Text(), True, None, None),
        ("analysis_type", sa.String(length=50), False, "", ""),
        ("configuration", sa.Text(), True, None, None),
        ("is_active", sa.Boolean(), False, "0", "0"),
        ("created_at", sa.DateTime(), False, "CURRENT_TIMESTAMP", "CURRENT_TIMESTAMP"),
        ("updated_at", sa.DateTime(), False, "CURRENT_TIMESTAMP", "CURRENT_TIMESTAMP"),
    ),
    "analysis_reports": (
        ("template_id", sa.Integer(), False, "0", None),
        ("created_at", sa.DateTime(), False, "CURRENT_TIMESTAMP", "CURRENT_TIMESTAMP"),
    ),
    "builders": (
        ("name", sa.String(length=255), False, "", ""),
        ("company_name", sa.String(length=255), True, None, None),
        ("phone", sa.String(length=20), False, "", ""),
        ("email", sa.String(length=255), True, None, None),
        ("address", sa.Text(), True, None, None),
        ("speciality", sa.String(length=100), False, "residential", "residential"),
        ("active_projects", sa.Integer(), False, "0", "0"),
        ("completed_projects", sa.Integer(), False, "0", "0"),
        ("rating", sa.Float(), True, None, None),
        ("notes", sa.Text(), False, "", ""),
        ("status", sa.String(length=20), False, "active", "active"),
        ("created_at", sa.DateTime(), False, "CURRENT_TIMESTAMP", "CURRENT_TIMESTAMP"),
    ),
    "customer_groups": (
        ("name", sa.String(length=100), False, "", ""),
        ("color", sa.String(length=7), False, "#6366f1", "#6366f1"),
        ("description", sa.Text(), False, "", ""),
        ("created_at", sa.DateTime(), False, "CURRENT_TIMESTAMP", "CURRENT_TIMESTAMP"),
    ),
    "property_images": (
        ("property_id", sa.Integer(), False, "0", None),
        ("filename", sa.String(length=255), False, "", ""),
        ("caption", sa.String(length=255), True, None, None),
        ("display_order", sa.Integer(), False, "0", "0"),
        ("is_primary", sa.Boolean(), False, "0", "0"),
        ("created_at", sa.DateTime(), False, "CURRENT_TIMESTAMP", "CURRENT_TIMESTAMP"),
    ),
    "property_activity_log": (
        ("property_id", sa.Integer(), False, "0", None),
        ("action", sa.String(length=50), False, "", ""),
        ("description", sa.Text(), False, "", ""),
        ("old_value", sa.Text(), True, None, None),
        ("new_value", sa.Text(), True, None, None),
        ("change_source", sa.String(length=20), False, "manual", "manual"),
        ("changed_by", sa.String(length=100), True, None, None),
        ("sync_version", sa.Integer(), True, None, None),
        ("created_at", sa.DateTime(), False, "CURRENT_TIMESTAMP", "CURRENT_TIMESTAMP"),
    ),
    "contact_reveals": (
        ("property_id", sa.Integer(), False, "0", None),
        ("viewer_ip", sa.String(length=45), True, None, None),
        ("viewer_user_id", sa.Integer(), True, None, None),
        ("created_at", sa.DateTime(), False, "CURRENT_TIMESTAMP", "CURRENT_TIMESTAMP"),
    ),
    "public_property_submissions": (
        ("submitter_name", sa.String(length=255), False, "", ""),
        ("submitter_phone", sa.String(length=20), False, "", ""),
        ("submitter_email", sa.String(length=255), True, None, None),
        ("property_title", sa.String(length=255), False, "", ""),
        ("property_type", sa.String(length=50), False, "apartment", "apartment"),
        ("listing_type", sa.String(length=20), False, "sale", "sale"),
        ("address", sa.Text(), False, "", ""),
        ("price", sa.BigInteger(), True, None, None),
        ("rahn", sa.BigInteger(), True, None, None),
        ("ejare", sa.BigInteger(), True, None, None),
        ("bedrooms", sa.Integer(), False, "0", "0"),
        ("square_feet", sa.Integer(), False, "0", "0"),
        ("description", sa.Text(), False, "", ""),
        ("status", sa.String(length=20), False, "pending", "pending"),
        ("admin_notes", sa.Text(), False, "", ""),
        ("created_at", sa.DateTime(), False, "CURRENT_TIMESTAMP", "CURRENT_TIMESTAMP"),
    ),
    "property_ai_history": (
        ("property_id", sa.Integer(), False, "0", None),
        ("raw_data", sa.Text(), False, "", ""),
        ("created_at", sa.DateTime(), False, "CURRENT_TIMESTAMP", "CURRENT_TIMESTAMP"),
        ("user_note", sa.String(length=255), True, None, None),
    ),
    "model_performance_metrics": (
        ("model_name", sa.String(length=100), False, "", ""),
        ("metric_type", sa.String(length=50), False, "", ""),
        ("metric_value", sa.Float(), False, "0", "0"),
        ("timestamp", sa.DateTime(), False, "CURRENT_TIMESTAMP", "CURRENT_TIMESTAMP"),
        ("metadata_", sa.Text(), True, None, None),
    ),
    "ai_metadata": (
        ("operation_type", sa.String(length=100), False, "", ""),
        ("model_name", sa.String(length=100), False, "", ""),
        ("input_tokens", sa.Integer(), True, None, None),
        ("output_tokens", sa.Integer(), True, None, None),
        ("total_tokens", sa.Integer(), True, None, None),
        ("latency_ms", sa.Float(), True, None, None),
        ("success", sa.Boolean(), False, "1", "1"),
        ("error_message", sa.Text(), True, None, None),
        ("timestamp", sa.DateTime(), False, "CURRENT_TIMESTAMP", "CURRENT_TIMESTAMP"),
        ("property_id", sa.Integer(), True, None, None),
        ("customer_id", sa.Integer(), True, None, None),
        ("deal_id", sa.Integer(), True, None, None),
        ("task_id", sa.Integer(), True, None, None),
        ("context_data", sa.Text(), True, None, None),
    ),
    "sync_state": (
        ("last_sync_at", sa.DateTime(), True, None, None),
        ("last_sync_cursor", sa.String(length=255), True, None, None),
        ("properties_synced", sa.Integer(), False, "0", "0"),
        ("properties_created", sa.Integer(), False, "0", "0"),
        ("properties_updated", sa.Integer(), False, "0", "0"),
        ("fields_changed", sa.Integer(), False, "0", "0"),
        ("status", sa.String(length=20), False, "idle", "idle"),
        ("error_message", sa.Text(), True, None, None),
        ("duration_seconds", sa.Float(), True, None, None),
        ("created_at", sa.DateTime(), False, "CURRENT_TIMESTAMP", "CURRENT_TIMESTAMP"),
    ),
}


def _complete_existing_tables() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())
    added = {}

    for table_name, specs in EXISTING_TABLE_COLUMNS.items():
        if table_name not in existing_tables:
            continue
        existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
        missing = [spec for spec in specs if spec[0] not in existing_columns]
        if not missing:
            continue
        added[table_name] = missing
        with op.batch_alter_table(table_name, schema=None) as batch_op:
            for name, column_type, nullable, temporary_default, _ in missing:
                batch_op.add_column(
                    sa.Column(
                        name,
                        column_type,
                        nullable=True if not nullable else True,
                        server_default=temporary_default,
                    )
                )

    for table_name, specs in added.items():
        for name, _, nullable, _, backfill in specs:
            if not nullable and backfill is not None:
                if backfill == "CURRENT_TIMESTAMP":
                    value_sql = "CURRENT_TIMESTAMP"
                elif backfill in {"0", "1"}:
                    value_sql = backfill
                else:
                    value_sql = "'" + backfill.replace("'", "''") + "'"
                op.execute(
                    sa.text(
                        f"UPDATE {table_name} SET {name} = {value_sql} "
                        f"WHERE {name} IS NULL"
                    )
                )
        with op.batch_alter_table(table_name, schema=None) as batch_op:
            for name, column_type, nullable, _, backfill in specs:
                if not nullable:
                    batch_op.alter_column(
                        name,
                        existing_type=column_type,
                        nullable=False,
                        server_default=None,
                    )

def _add_indexes() -> None:
    inspector = inspect(op.get_bind())
    index_names = {
        (table_name, index["name"])
        for table_name in CREATED_TABLES
        for index in inspector.get_indexes(table_name)
    }
    indexes = (
        ("ai_metadata", "ix_ai_metadata_operation_type", ["operation_type"]),
        ("ai_metadata", "ix_ai_metadata_model_name", ["model_name"]),
        ("ai_metadata", "ix_ai_metadata_timestamp", ["timestamp"]),
        ("model_performance_metrics", "ix_model_performance_metrics_model_name", ["model_name"]),
        ("model_performance_metrics", "ix_model_performance_metrics_metric_type", ["metric_type"]),
        ("model_performance_metrics", "ix_model_performance_metrics_timestamp", ["timestamp"]),
        ("property_activity_log", "idx_activity_log_property_id", ["property_id"]),
        ("property_activity_log", "idx_activity_log_change_source", ["change_source"]),
    )
    for table_name, index_name, columns in indexes:
        if (table_name, index_name) not in index_names:
            op.create_index(index_name, table_name, columns, unique=False)


def _reconcile_customer_columns() -> None:
    inspector = inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("customers")}

    if "customer_group_id" not in columns:
        with op.batch_alter_table("customers", schema=None) as batch_op:
            batch_op.add_column(sa.Column("customer_group_id", sa.Integer(), nullable=True))

    if "preferences" not in columns:
        with op.batch_alter_table("customers", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("preferences", sa.Text(), nullable=True, server_default="")
            )
        op.execute("UPDATE customers SET preferences = '' WHERE preferences IS NULL")
        with op.batch_alter_table("customers", schema=None) as batch_op:
            batch_op.alter_column(
                "preferences",
                existing_type=sa.Text(),
                nullable=False,
                server_default=None,
            )

    if "customer_type" not in columns:
        with op.batch_alter_table("customers", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "customer_type",
                    sa.String(length=20),
                    nullable=True,
                    server_default="buyer",
                )
            )
        op.execute("UPDATE customers SET customer_type = 'buyer' WHERE customer_type IS NULL")
        with op.batch_alter_table("customers", schema=None) as batch_op:
            batch_op.alter_column(
                "customer_type",
                existing_type=sa.String(length=20),
                nullable=False,
                server_default=None,
            )
    else:
        customer_type = next(
            column for column in inspector.get_columns("customers")
            if column["name"] == "customer_type"
        )
        if customer_type["nullable"]:
            op.execute("UPDATE customers SET customer_type = 'buyer' WHERE customer_type IS NULL")
            with op.batch_alter_table("customers", schema=None) as batch_op:
                batch_op.alter_column(
                    "customer_type",
                    existing_type=sa.String(length=20),
                    nullable=False,
                    server_default=None,
                )

    inspector = inspect(op.get_bind())
    foreign_keys = {
        (
            foreign_key.get("constrained_columns", [None])[0],
            foreign_key.get("referred_table"),
            foreign_key.get("referred_columns", [None])[0],
        )
        for foreign_key in inspector.get_foreign_keys("customers")
    }
    if ("customer_group_id", "customer_groups", "id") not in foreign_keys:
        with op.batch_alter_table("customers", schema=None) as batch_op:
            batch_op.create_foreign_key(
                "fk_customers_customer_group_id",
                "customer_groups",
                ["customer_group_id"],
                ["id"],
            )


def upgrade() -> None:
    _create_missing_tables()
    _complete_existing_tables()
    _reconcile_customer_columns()
    _add_indexes()


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if "customers" in inspector.get_table_names():
        foreign_keys = {foreign_key.get("name") for foreign_key in inspector.get_foreign_keys("customers")}
        if "fk_customers_customer_group_id" in foreign_keys:
            with op.batch_alter_table("customers", schema=None) as batch_op:
                batch_op.drop_constraint("fk_customers_customer_group_id", type_="foreignkey")
        columns = {column["name"] for column in inspector.get_columns("customers")}
        with op.batch_alter_table("customers", schema=None) as batch_op:
            if "preferences" in columns:
                batch_op.drop_column("preferences")
            if "customer_group_id" in columns:
                batch_op.drop_column("customer_group_id")

    for table_name in reversed(CREATED_TABLES):
        if table_name in inspect(bind).get_table_names():
            for index in inspect(bind).get_indexes(table_name):
                if index["name"] in {
                    "ix_ai_metadata_operation_type",
                    "ix_ai_metadata_model_name",
                    "ix_ai_metadata_timestamp",
                    "ix_model_performance_metrics_model_name",
                    "ix_model_performance_metrics_metric_type",
                    "ix_model_performance_metrics_timestamp",
                    "idx_activity_log_property_id",
                    "idx_activity_log_change_source",
                }:
                    op.drop_index(index["name"], table_name=table_name)
            op.drop_table(table_name)

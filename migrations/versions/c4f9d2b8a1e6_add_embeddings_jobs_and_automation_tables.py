"""Add embeddings, matching job, rematch queue, and automation tables.

Revision ID: c4f9d2b8a1e6
Revises: 5b578ff077cb
Create Date: 2026-02-08 15:25:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c4f9d2b8a1e6"
down_revision = "5b578ff077cb"
branch_labels = None
depends_on = None


def _is_postgres() -> bool:
    bind = op.get_bind()
    return bind.dialect.name == "postgresql"


def upgrade():
    op.create_table(
        "property_embeddings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("embedding_data", sa.Text(), nullable=False),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("dimension", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("property_id"),
    )
    op.create_index(
        "ix_property_embeddings_source_hash",
        "property_embeddings",
        ["source_hash"],
        unique=False,
    )

    if _is_postgres():
        op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
        op.execute(
            sa.text(
                "ALTER TABLE property_embeddings "
                "ADD COLUMN IF NOT EXISTS embedding_vector vector(768)"
            )
        )
        op.execute(
            sa.text(
                "CREATE INDEX IF NOT EXISTS ix_property_embeddings_vector_hnsw "
                "ON property_embeddings USING hnsw (embedding_vector vector_cosine_ops)"
            )
        )

    op.create_table(
        "matching_job_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("trigger_source", sa.String(length=30), nullable=False),
        sa.Column("property_ids", sa.Text(), nullable=True),
        sa.Column("customer_ids", sa.Text(), nullable=True),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )

    op.create_table(
        "rematch_queue",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=20), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("retries", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("dedupe_key", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedupe_key"),
    )
    op.create_index("ix_rematch_queue_status", "rematch_queue", ["status"], unique=False)
    op.create_index(
        "ix_rematch_queue_entity",
        "rematch_queue",
        ["entity_type", "entity_id"],
        unique=False,
    )

    op.create_table(
        "automation_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("trigger_type", sa.String(length=50), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("conditions", sa.Text(), nullable=False),
        sa.Column("actions", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(
        "ix_automation_rules_trigger_enabled",
        "automation_rules",
        ["trigger_type", "enabled"],
        unique=False,
    )

    op.create_table(
        "automation_audit_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rule_id", sa.Integer(), nullable=True),
        sa.Column("trigger_type", sa.String(length=50), nullable=False),
        sa.Column("trigger_ref", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["rule_id"], ["automation_rules.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_automation_audit_trigger_created",
        "automation_audit_log",
        ["trigger_type", "created_at"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_automation_audit_trigger_created", table_name="automation_audit_log")
    op.drop_table("automation_audit_log")

    op.drop_index("ix_automation_rules_trigger_enabled", table_name="automation_rules")
    op.drop_table("automation_rules")

    op.drop_index("ix_rematch_queue_entity", table_name="rematch_queue")
    op.drop_index("ix_rematch_queue_status", table_name="rematch_queue")
    op.drop_table("rematch_queue")

    op.drop_table("matching_job_runs")

    if _is_postgres():
        op.execute(sa.text("DROP INDEX IF EXISTS ix_property_embeddings_vector_hnsw"))
        op.execute(
            sa.text(
                "ALTER TABLE property_embeddings "
                "DROP COLUMN IF EXISTS embedding_vector"
            )
        )

    op.drop_index("ix_property_embeddings_source_hash", table_name="property_embeddings")
    op.drop_table("property_embeddings")

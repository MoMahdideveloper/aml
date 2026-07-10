"""automation outbox, runs, settings, rule/task extensions

Revision ID: o0p1q2r3s4t5
Revises: n9o0p1q2r3s4
Create Date: 2026-07-10
"""

from alembic import op
import sqlalchemy as sa

revision = "o0p1q2r3s4t5"
down_revision = "n9o0p1q2r3s4"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("automation_rules") as batch:
        batch.add_column(sa.Column("rule_key", sa.String(length=80), nullable=True))
        batch.add_column(sa.Column("cooldown_hours", sa.Integer(), server_default="24"))
        batch.add_column(sa.Column("priority", sa.Integer(), server_default="100"))
        batch.add_column(sa.Column("version", sa.Integer(), server_default="1"))
        batch.add_column(sa.Column("is_template", sa.Boolean(), server_default=sa.false()))
    op.create_index("ix_automation_rules_rule_key", "automation_rules", ["rule_key"], unique=True)

    with op.batch_alter_table("tasks") as batch:
        batch.add_column(sa.Column("automation_run_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("automation_rule_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("automation_title_key", sa.String(length=40), nullable=True))
        batch.add_column(sa.Column("source_entity_type", sa.String(length=32), nullable=True))
        batch.add_column(sa.Column("source_entity_id", sa.Integer(), nullable=True))
    op.create_index("ix_tasks_automation_run_id", "tasks", ["automation_run_id"])
    op.create_index("ix_tasks_automation_rule_id", "tasks", ["automation_rule_id"])

    op.create_table(
        "automation_outbox_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("aggregate_type", sa.String(length=32), nullable=False),
        sa.Column("aggregate_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), server_default=""),
        sa.Column("changed_fields", sa.String(length=255), server_default=""),
        sa.Column("schema_version", sa.Integer(), server_default="1"),
        sa.Column("context_json", sa.Text(), server_default="{}"),
        sa.Column("status", sa.String(length=20), server_default="pending"),
        sa.Column("attempts", sa.Integer(), server_default="0"),
        sa.Column("last_error", sa.String(length=255), server_default=""),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_automation_outbox_events_event_id", "automation_outbox_events", ["event_id"], unique=True)
    op.create_index("ix_automation_outbox_events_status", "automation_outbox_events", ["status"])
    op.create_index("ix_automation_outbox_events_event_type", "automation_outbox_events", ["event_type"])
    op.create_index("ix_automation_outbox_events_aggregate_id", "automation_outbox_events", ["aggregate_id"])

    op.create_table(
        "automation_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("rule_id", sa.Integer(), sa.ForeignKey("automation_rules.id"), nullable=True),
        sa.Column("rule_version", sa.Integer(), server_default="1"),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="matched"),
        sa.Column("reason_code", sa.String(length=64), server_default=""),
        sa.Column("action_type", sa.String(length=40), server_default=""),
        sa.Column("action_ref", sa.String(length=120), server_default=""),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("dry_run", sa.Boolean(), server_default=sa.false()),
        sa.Column("attempt_count", sa.Integer(), server_default="1"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("failure_category", sa.String(length=40), nullable=True),
    )
    op.create_index("ix_automation_runs_idempotency_key", "automation_runs", ["idempotency_key"], unique=True)
    op.create_index("ix_automation_runs_event_id", "automation_runs", ["event_id"])
    op.create_index("ix_automation_runs_rule_id", "automation_runs", ["rule_id"])
    op.create_index("ix_automation_runs_status", "automation_runs", ["status"])

    op.create_table(
        "automation_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("global_enabled", sa.Boolean(), server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("updated_by", sa.String(length=120), server_default=""),
    )
    op.execute(
        "INSERT INTO automation_settings (id, global_enabled, updated_by) VALUES (1, 1, 'migration')"
    )


def downgrade():
    op.drop_table("automation_settings")
    op.drop_index("ix_automation_runs_status", table_name="automation_runs")
    op.drop_index("ix_automation_runs_rule_id", table_name="automation_runs")
    op.drop_index("ix_automation_runs_event_id", table_name="automation_runs")
    op.drop_index("ix_automation_runs_idempotency_key", table_name="automation_runs")
    op.drop_table("automation_runs")
    op.drop_index("ix_automation_outbox_events_aggregate_id", table_name="automation_outbox_events")
    op.drop_index("ix_automation_outbox_events_event_type", table_name="automation_outbox_events")
    op.drop_index("ix_automation_outbox_events_status", table_name="automation_outbox_events")
    op.drop_index("ix_automation_outbox_events_event_id", table_name="automation_outbox_events")
    op.drop_table("automation_outbox_events")
    op.drop_index("ix_tasks_automation_rule_id", table_name="tasks")
    op.drop_index("ix_tasks_automation_run_id", table_name="tasks")
    with op.batch_alter_table("tasks") as batch:
        batch.drop_column("source_entity_id")
        batch.drop_column("source_entity_type")
        batch.drop_column("automation_title_key")
        batch.drop_column("automation_rule_id")
        batch.drop_column("automation_run_id")
    op.drop_index("ix_automation_rules_rule_key", table_name="automation_rules")
    with op.batch_alter_table("automation_rules") as batch:
        batch.drop_column("is_template")
        batch.drop_column("version")
        batch.drop_column("priority")
        batch.drop_column("cooldown_hours")
        batch.drop_column("rule_key")

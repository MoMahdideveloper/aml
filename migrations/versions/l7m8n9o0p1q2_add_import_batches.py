"""add import_batches and import_row_results

Revision ID: l7m8n9o0p1q2
Revises: k6l7m8n9o0p1
Create Date: 2026-07-10
"""

from alembic import op
import sqlalchemy as sa

revision = "l7m8n9o0p1q2"
down_revision = "k6l7m8n9o0p1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "import_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="uploaded"),
        sa.Column("original_filename", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("file_hash", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("uploader_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("uploader_label", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("mapping_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("mode", sa.String(length=32), nullable=False, server_default="create_only"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valid_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("invalid_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("possible_duplicate_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("imported_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failure_category", sa.String(length=64), nullable=True),
        sa.Column("rollback_status", sa.String(length=32), nullable=False, server_default="none"),
        sa.Column("temp_path", sa.String(length=512), nullable=False, server_default=""),
    )
    op.create_index("ix_import_batches_status", "import_batches", ["status"])
    op.create_index("ix_import_batches_file_hash", "import_batches", ["file_hash"])

    op.create_table(
        "import_row_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("import_batches.id"), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("error_codes", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("diagnostic", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("match_key", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("created_record_id", sa.Integer(), nullable=True),
        sa.Column("decision", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("decision_by", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("decision_at", sa.DateTime(), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_import_row_results_batch_id", "import_row_results", ["batch_id"])
    op.create_index("ix_import_row_results_outcome", "import_row_results", ["outcome"])


def downgrade():
    op.drop_index("ix_import_row_results_outcome", table_name="import_row_results")
    op.drop_index("ix_import_row_results_batch_id", table_name="import_row_results")
    op.drop_table("import_row_results")
    op.drop_index("ix_import_batches_file_hash", table_name="import_batches")
    op.drop_index("ix_import_batches_status", table_name="import_batches")
    op.drop_table("import_batches")

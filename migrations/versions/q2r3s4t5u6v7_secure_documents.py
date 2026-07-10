"""secure CRM documents and document audit logs

Revision ID: q2r3s4t5u6v7
Revises: p1q2r3s4t5u6
Create Date: 2026-07-11
"""

from alembic import op
import sqlalchemy as sa

revision = "q2r3s4t5u6v7"
down_revision = "p1q2r3s4t5u6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_type", sa.String(length=20), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("display_name", sa.String(length=200), server_default=""),
        sa.Column("original_filename", sa.String(length=255), server_default=""),
        sa.Column("storage_key", sa.String(length=80), nullable=False),
        sa.Column("media_type", sa.String(length=80), server_default=""),
        sa.Column("byte_size", sa.Integer(), server_default="0"),
        sa.Column("sha256", sa.String(length=64), server_default=""),
        sa.Column("status", sa.String(length=20), server_default="pending_scan"),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("document_group_id", sa.String(length=40), nullable=False),
        sa.Column("is_latest", sa.Boolean(), server_default=sa.true()),
        sa.Column("uploaded_by", sa.Integer(), nullable=True),
        sa.Column("uploaded_by_label", sa.String(length=120), server_default=""),
        sa.Column("uploaded_at", sa.DateTime(), nullable=True),
        sa.Column("archived_by", sa.Integer(), nullable=True),
        sa.Column("archived_at", sa.DateTime(), nullable=True),
        sa.Column("retention_until", sa.DateTime(), nullable=True),
        sa.Column("scan_engine", sa.String(length=40), server_default=""),
        sa.Column("scan_result", sa.String(length=40), server_default=""),
        sa.Column("metadata_version", sa.Integer(), server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_documents_owner_type", "documents", ["owner_type"])
    op.create_index("ix_documents_owner_id", "documents", ["owner_id"])
    op.create_index("ix_documents_owner_lookup", "documents", ["owner_type", "owner_id"])
    op.create_index("ix_documents_category", "documents", ["category"])
    op.create_index("ix_documents_status", "documents", ["status"])
    op.create_index("ix_documents_uploaded_at", "documents", ["uploaded_at"])
    op.create_index("ix_documents_sha256", "documents", ["sha256"])
    op.create_index("ix_documents_storage_key", "documents", ["storage_key"], unique=True)
    op.create_index(
        "ix_documents_group_version",
        "documents",
        ["document_group_id", "version"],
        unique=True,
    )
    op.create_index("ix_documents_group_id", "documents", ["document_group_id"])
    op.create_index("ix_documents_is_latest", "documents", ["is_latest"])

    op.create_table(
        "document_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), nullable=True),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("actor_label", sa.String(length=120), server_default=""),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("result", sa.String(length=20), server_default="ok"),
        sa.Column("request_id", sa.String(length=64), server_default=""),
        sa.Column("owner_type", sa.String(length=20), server_default=""),
        sa.Column("category", sa.String(length=40), server_default=""),
        sa.Column("size_band", sa.String(length=20), server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_document_audit_logs_document_id", "document_audit_logs", ["document_id"])
    op.create_index("ix_document_audit_logs_action", "document_audit_logs", ["action"])
    op.create_index("ix_document_audit_logs_created_at", "document_audit_logs", ["created_at"])


def downgrade():
    op.drop_index("ix_document_audit_logs_created_at", table_name="document_audit_logs")
    op.drop_index("ix_document_audit_logs_action", table_name="document_audit_logs")
    op.drop_index("ix_document_audit_logs_document_id", table_name="document_audit_logs")
    op.drop_table("document_audit_logs")
    op.drop_index("ix_documents_is_latest", table_name="documents")
    op.drop_index("ix_documents_group_id", table_name="documents")
    op.drop_index("ix_documents_group_version", table_name="documents")
    op.drop_index("ix_documents_storage_key", table_name="documents")
    op.drop_index("ix_documents_sha256", table_name="documents")
    op.drop_index("ix_documents_uploaded_at", table_name="documents")
    op.drop_index("ix_documents_status", table_name="documents")
    op.drop_index("ix_documents_category", table_name="documents")
    op.drop_index("ix_documents_owner_lookup", table_name="documents")
    op.drop_index("ix_documents_owner_id", table_name="documents")
    op.drop_index("ix_documents_owner_type", table_name="documents")
    op.drop_table("documents")

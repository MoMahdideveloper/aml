"""add ai form extraction audit tables

Revision ID: a1b2c3d4e5f6
Revises: z1a2b3c4d5e6
Create Date: 2026-07-13
"""

from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "z1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ai_form_extractions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("actor_label", sa.String(length=120), server_default=""),
        sa.Column("form_name", sa.String(length=40), nullable=False),
        sa.Column("target_record_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="pending"),
        sa.Column("source_type", sa.String(length=20), server_default="text"),
        sa.Column("model_id", sa.String(length=80), server_default=""),
        sa.Column("idempotency_key", sa.String(length=80), server_default=""),
        sa.Column("input_meta_json", sa.Text(), server_default=""),
        sa.Column("error_code", sa.String(length=40), server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ai_form_extractions_actor_user_id", "ai_form_extractions", ["actor_user_id"])
    op.create_index("ix_ai_form_extractions_form_name", "ai_form_extractions", ["form_name"])
    op.create_index("ix_ai_form_extractions_status", "ai_form_extractions", ["status"])
    op.create_index("ix_ai_form_extractions_created_at", "ai_form_extractions", ["created_at"])
    op.create_index("ix_ai_form_extractions_expires_at", "ai_form_extractions", ["expires_at"])
    op.create_index(
        "ix_ai_form_extractions_actor_idempotency",
        "ai_form_extractions",
        ["actor_user_id", "idempotency_key"],
        unique=True,
    )

    op.create_table(
        "ai_form_media",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("extraction_id", sa.Integer(), sa.ForeignKey("ai_form_extractions.id"), nullable=False),
        sa.Column("storage_key", sa.String(length=120), nullable=False),
        sa.Column("sha256", sa.String(length=64), server_default=""),
        sa.Column("mime_type", sa.String(length=80), server_default=""),
        sa.Column("byte_size", sa.Integer(), server_default="0"),
        sa.Column("original_filename", sa.String(length=200), server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ai_form_media_extraction_id", "ai_form_media", ["extraction_id"])

    op.create_table(
        "ai_form_suggestions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("extraction_id", sa.Integer(), sa.ForeignKey("ai_form_extractions.id"), nullable=False),
        sa.Column("field_name", sa.String(length=80), nullable=False),
        sa.Column("raw_value_json", sa.Text(), server_default=""),
        sa.Column("normalized_value_json", sa.Text(), server_default=""),
        sa.Column("confidence", sa.Float(), server_default="0"),
        sa.Column("action", sa.String(length=20), server_default="review"),
        sa.Column("reasons_json", sa.Text(), server_default=""),
        sa.Column("source_type", sa.String(length=20), server_default="text"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ai_form_suggestions_extraction_id", "ai_form_suggestions", ["extraction_id"])
    op.create_index("ix_ai_form_suggestions_field_name", "ai_form_suggestions", ["field_name"])

    op.create_table(
        "ai_form_review_decisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("extraction_id", sa.Integer(), sa.ForeignKey("ai_form_extractions.id"), nullable=False),
        sa.Column("suggestion_id", sa.Integer(), nullable=True),
        sa.Column("field_name", sa.String(length=80), server_default=""),
        sa.Column("decision", sa.String(length=20), server_default="pending"),
        sa.Column("edited_value_json", sa.Text(), server_default=""),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_ai_form_review_decisions_extraction_id", "ai_form_review_decisions", ["extraction_id"]
    )


def downgrade():
    op.drop_table("ai_form_review_decisions")
    op.drop_table("ai_form_suggestions")
    op.drop_table("ai_form_media")
    op.drop_table("ai_form_extractions")

"""Add voice history storage for audio metadata and transcriptions.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "voice_history" in inspect(op.get_bind()).get_table_names():
        return

    op.create_table(
        "voice_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("audio_filename", sa.String(length=255), nullable=False),
        sa.Column("audio_file_size", sa.Integer(), nullable=True),
        sa.Column("audio_duration_seconds", sa.Float(), nullable=True),
        sa.Column("transcription", sa.Text(), nullable=True),
        sa.Column("transcription_confidence", sa.Float(), nullable=True),
        sa.Column("language_detected", sa.String(length=10), nullable=True),
        sa.Column("ai_model_used", sa.String(length=50), nullable=False, server_default="gemini-pro"),
        sa.Column("processing_status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_voice_history_is_deleted", "voice_history", ["is_deleted"])


def downgrade() -> None:
    if "voice_history" not in inspect(op.get_bind()).get_table_names():
        return
    op.drop_index("ix_voice_history_is_deleted", table_name="voice_history")
    op.drop_table("voice_history")

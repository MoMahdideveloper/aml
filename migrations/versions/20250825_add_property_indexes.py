"""add useful indexes to properties

Revision ID: 20250825_add_indexes
Revises: 
Create Date: 2025-08-25
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250825_add_indexes'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index('ix_properties_price', 'properties', ['price'], unique=False)
    op.create_index('ix_properties_status', 'properties', ['status'], unique=False)
    op.create_index('ix_properties_property_type', 'properties', ['property_type'], unique=False)
    op.create_index('ix_properties_neighborhood', 'properties', ['neighborhood'], unique=False)
    op.create_index('ix_properties_bedrooms', 'properties', ['bedrooms'], unique=False)
    op.create_index('ix_properties_bathrooms', 'properties', ['bathrooms'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_properties_bathrooms', table_name='properties')
    op.drop_index('ix_properties_bedrooms', table_name='properties')
    op.drop_index('ix_properties_neighborhood', table_name='properties')
    op.drop_index('ix_properties_property_type', table_name='properties')
    op.drop_index('ix_properties_status', table_name='properties')
    op.drop_index('ix_properties_price', table_name='properties')


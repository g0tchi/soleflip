"""Add external_ids to inventory_item

Revision ID: 1d7ca9ca7284
Revises: 7689c86d1945
Create Date: 2025-08-14 17:48:00.781552

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '1d7ca9ca7284'
down_revision = '7689c86d1945'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('inventory', sa.Column('external_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade():
    op.drop_column('inventory', 'external_ids')

"""remove redundant sale_overview from inventory

Revision ID: 22679e4c7a0b
Revises: 84bc4d8b03ef
Create Date: 2025-10-01 08:16:58.121633

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '22679e4c7a0b'
down_revision = '84bc4d8b03ef'
branch_labels = None
depends_on = None


def upgrade():
    # Remove redundant sale_overview column from inventory
    # This field contained legacy text like "In stock for X days - SOLD"
    # Now superseded by:
    # - orders.shelf_life_days (structured data)
    # - orders.status (sale status)
    op.drop_column('inventory', 'sale_overview', schema='products')


def downgrade():
    # Restore sale_overview column (data will be lost)
    op.add_column(
        'inventory',
        sa.Column('sale_overview', sa.Text(), nullable=True),
        schema='products'
    )

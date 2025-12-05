"""Add EAN fields to Product and InventoryItem

Revision ID: 0a4cb50d4a04
Revises: 1c9879bad9c0
Create Date: 2025-12-04 07:23:39.610258

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '0a4cb50d4a04'
down_revision = '1c9879bad9c0'
branch_labels = None
depends_on = None


def upgrade():
    # Add EAN field to Product table
    op.add_column(
        'product',
        sa.Column('ean', sa.String(length=13), nullable=True, comment='EAN/GTIN product identifier (size-independent)'),
        schema='catalog'
    )
    op.create_index(
        'ix_catalog_product_ean',
        'product',
        ['ean'],
        schema='catalog'
    )

    # Add EAN field to InventoryItem (stock) table
    op.add_column(
        'stock',
        sa.Column('ean', sa.String(length=13), nullable=True, comment='Size-specific EAN/GTIN identifier'),
        schema='inventory'
    )
    op.create_index(
        'ix_inventory_stock_ean',
        'stock',
        ['ean'],
        schema='inventory'
    )


def downgrade():
    # Remove EAN field and index from InventoryItem (stock) table
    op.drop_index('ix_inventory_stock_ean', table_name='stock', schema='inventory')
    op.drop_column('stock', 'ean', schema='inventory')

    # Remove EAN field and index from Product table
    op.drop_index('ix_catalog_product_ean', table_name='product', schema='catalog')
    op.drop_column('product', 'ean', schema='catalog')

"""remove_redundant_style_code_column

Gibson AI schema cleanup: Remove redundant style_code column.

Analysis showed that style_code is always identical to sku:
- sku = style_code = enrichment_data->>'sku' = enrichment_data->'product_details'->>'styleId'

This creates 4x data redundancy with no benefit. Per Gibson's hybrid schema principles,
we keep the frequently-queried 'sku' column and remove the redundant 'style_code'.

Impact:
- Eliminates unnecessary data duplication
- Reduces sync complexity
- Maintains all functionality (sku serves same purpose)

Revision ID: 9a81f76b2638
Revises: 9e2361a7c480
Create Date: 2025-11-19 18:24:39.382025

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9a81f76b2638'
down_revision = '9e2361a7c480'
branch_labels = None
depends_on = None


def upgrade():
    # Drop redundant style_code column
    # Note: sku column contains the same data and is used for queries
    op.drop_column('product', 'style_code', schema='catalog')


def downgrade():
    # Restore style_code column and copy data from sku
    op.add_column(
        'product',
        sa.Column('style_code', sa.String(length=100), nullable=True, comment='Product style code (e.g., SKU)'),
        schema='catalog'
    )

    # Copy sku data back to style_code for rollback
    op.execute("""
        UPDATE catalog.product
        SET style_code = sku
        WHERE sku IS NOT NULL
    """)

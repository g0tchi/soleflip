"""add_product_enrichment_fields

Revision ID: 7e0919aaa601
Revises: 391b4113b939
Create Date: 2025-10-22 11:39:11.439100

Add StockX enrichment fields to catalog.product table:
- stockx_product_id: StockX product UUID
- style_code: Product style code (SKU)
- enrichment_data: Complete StockX product data (JSONB)
- lowest_ask: Current lowest ask price
- highest_bid: Current highest bid price
- recommended_sell_faster: Recommended price for faster sale
- recommended_earn_more: Recommended price for maximum earnings
- last_enriched_at: Last enrichment timestamp

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '7e0919aaa601'
down_revision = '391b4113b939'
branch_labels = None
depends_on = None


def upgrade():
    # Add StockX enrichment fields to catalog.product
    op.add_column('product', sa.Column('stockx_product_id', sa.String(length=255), nullable=True, comment='StockX product UUID'), schema='catalog')
    op.add_column('product', sa.Column('style_code', sa.String(length=100), nullable=True, comment='Product style code (e.g., SKU)'), schema='catalog')
    op.add_column('product', sa.Column('enrichment_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Complete StockX product data'), schema='catalog')
    op.add_column('product', sa.Column('lowest_ask', sa.Numeric(precision=10, scale=2), nullable=True, comment='Current lowest ask price'), schema='catalog')
    op.add_column('product', sa.Column('highest_bid', sa.Numeric(precision=10, scale=2), nullable=True, comment='Current highest bid price'), schema='catalog')
    op.add_column('product', sa.Column('recommended_sell_faster', sa.Numeric(precision=10, scale=2), nullable=True, comment='Recommended price for faster sale'), schema='catalog')
    op.add_column('product', sa.Column('recommended_earn_more', sa.Numeric(precision=10, scale=2), nullable=True, comment='Recommended price for maximum earnings'), schema='catalog')
    op.add_column('product', sa.Column('last_enriched_at', sa.DateTime(timezone=True), nullable=True, comment='Last enrichment timestamp'), schema='catalog')

    # Create index on stockx_product_id for faster lookups
    op.create_index('idx_product_stockx_id', 'product', ['stockx_product_id'], unique=False, schema='catalog')

    # Create GIN index on enrichment_data JSONB column for faster JSONB queries
    op.create_index('idx_product_enrichment_data', 'product', ['enrichment_data'], unique=False, schema='catalog', postgresql_using='gin')


def downgrade():
    # Drop indexes
    op.drop_index('idx_product_enrichment_data', table_name='product', schema='catalog')
    op.drop_index('idx_product_stockx_id', table_name='product', schema='catalog')

    # Drop columns
    op.drop_column('product', 'last_enriched_at', schema='catalog')
    op.drop_column('product', 'recommended_earn_more', schema='catalog')
    op.drop_column('product', 'recommended_sell_faster', schema='catalog')
    op.drop_column('product', 'highest_bid', schema='catalog')
    op.drop_column('product', 'lowest_ask', schema='catalog')
    op.drop_column('product', 'enrichment_data', schema='catalog')
    op.drop_column('product', 'style_code', schema='catalog')
    op.drop_column('product', 'stockx_product_id', schema='catalog')

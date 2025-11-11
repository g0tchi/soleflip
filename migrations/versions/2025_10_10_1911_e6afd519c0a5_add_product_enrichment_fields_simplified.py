"""Add product enrichment fields (simplified)

Adds StockX catalog enrichment fields to products table:
- stockx_product_id: StockX product identifier
- style_code: Nike/Adidas style code
- enrichment_data: Full StockX catalog data (JSONB)
- lowest_ask: Current lowest ask price
- highest_bid: Current highest bid price
- recommended_sell_faster: StockX pricing recommendation (faster sale)
- recommended_earn_more: StockX pricing recommendation (max earnings)
- last_enriched_at: Timestamp of last enrichment

Revision ID: e6afd519c0a5
Revises: 22679e4c7a0b
Create Date: 2025-10-10 19:11:54.640204

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e6afd519c0a5'
down_revision = '22679e4c7a0b'
branch_labels = None
depends_on = None


def upgrade():
    # Add enrichment fields to products table
    op.add_column(
        'products',
        sa.Column('stockx_product_id', sa.String(length=100), nullable=True,
                  comment='StockX product identifier from catalog API'),
        schema='products'
    )

    op.add_column(
        'products',
        sa.Column('style_code', sa.String(length=50), nullable=True,
                  comment='Manufacturer style code (e.g., Nike style code)'),
        schema='products'
    )

    op.add_column(
        'products',
        sa.Column('enrichment_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Complete StockX catalog data (product details, variants, etc.)'),
        schema='products'
    )

    op.add_column(
        'products',
        sa.Column('lowest_ask', sa.Numeric(precision=10, scale=2), nullable=True,
                  comment='Current lowest ask price on StockX'),
        schema='products'
    )

    op.add_column(
        'products',
        sa.Column('highest_bid', sa.Numeric(precision=10, scale=2), nullable=True,
                  comment='Current highest bid price on StockX'),
        schema='products'
    )

    op.add_column(
        'products',
        sa.Column('recommended_sell_faster', sa.Numeric(precision=10, scale=2), nullable=True,
                  comment='StockX recommended price for faster sale'),
        schema='products'
    )

    op.add_column(
        'products',
        sa.Column('recommended_earn_more', sa.Numeric(precision=10, scale=2), nullable=True,
                  comment='StockX recommended price for maximum earnings'),
        schema='products'
    )

    op.add_column(
        'products',
        sa.Column('last_enriched_at', sa.DateTime(timezone=True), nullable=True,
                  comment='Timestamp of last enrichment from StockX catalog'),
        schema='products'
    )

    # Create index on stockx_product_id for faster lookups
    op.create_index(
        'ix_products_stockx_product_id',
        'products',
        ['stockx_product_id'],
        unique=False,
        schema='products'
    )

    # Create index on last_enriched_at to identify stale data
    op.create_index(
        'ix_products_last_enriched_at',
        'products',
        ['last_enriched_at'],
        unique=False,
        schema='products'
    )


def downgrade():
    # Drop indexes
    op.drop_index('ix_products_last_enriched_at', table_name='products', schema='products')
    op.drop_index('ix_products_stockx_product_id', table_name='products', schema='products')

    # Drop columns
    op.drop_column('products', 'last_enriched_at', schema='products')
    op.drop_column('products', 'recommended_earn_more', schema='products')
    op.drop_column('products', 'recommended_sell_faster', schema='products')
    op.drop_column('products', 'highest_bid', schema='products')
    op.drop_column('products', 'lowest_ask', schema='products')
    op.drop_column('products', 'enrichment_data', schema='products')
    op.drop_column('products', 'style_code', schema='products')
    op.drop_column('products', 'stockx_product_id', schema='products')

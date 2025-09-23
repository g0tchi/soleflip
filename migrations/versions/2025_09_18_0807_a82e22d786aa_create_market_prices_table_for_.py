"""create_market_prices_table_for_quickflip_detection

Revision ID: a82e22d786aa
Revises: 260ad1392824
Create Date: 2025-09-18 08:07:10.340266

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a82e22d786aa'
down_revision = '260ad1392824'
branch_labels = None
depends_on = None


def upgrade():
    """Create market_prices table for QuickFlip detection"""
    print("Creating market_prices table for external price tracking...")

    # Create integration schema if it doesn't exist
    op.execute('CREATE SCHEMA IF NOT EXISTS integration')

    # Create market_prices table
    op.create_table(
        'market_prices',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('product_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('products.products.id'), nullable=False),
        sa.Column('source', sa.String(100), nullable=False, comment='Data source: awin, webgains, scraping, etc.'),
        sa.Column('supplier_name', sa.String(100), nullable=False, comment='Retailer/supplier name'),
        sa.Column('external_id', sa.String(255), nullable=True, comment='External product ID from source'),
        sa.Column('buy_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='EUR'),
        sa.Column('availability', sa.String(50), nullable=True),
        sa.Column('stock_qty', sa.Integer, nullable=True),
        sa.Column('product_url', sa.Text, nullable=True),
        sa.Column('last_updated', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('raw_data', sa.dialects.postgresql.JSONB, nullable=True, comment='Complete source data'),
        schema='integration'
    )

    # Add indexes for performance
    op.create_index('idx_market_prices_product_id', 'market_prices', ['product_id'], schema='integration')
    op.create_index('idx_market_prices_source', 'market_prices', ['source'], schema='integration')
    op.create_index('idx_market_prices_supplier', 'market_prices', ['supplier_name'], schema='integration')
    op.create_index('idx_market_prices_price', 'market_prices', ['buy_price'], schema='integration')
    op.create_index('idx_market_prices_updated', 'market_prices', ['last_updated'], schema='integration')

    # Composite index for QuickFlip queries
    op.create_index('idx_market_prices_quickflip', 'market_prices', ['product_id', 'buy_price', 'last_updated'], schema='integration')

    print("[OK] Created integration.market_prices table with performance indexes")
    print("Market prices table ready for QuickFlip detection!")


def downgrade():
    """Drop market_prices table"""
    print("Removing market_prices table...")

    # Drop indexes first
    op.drop_index('idx_market_prices_quickflip', table_name='market_prices', schema='integration')
    op.drop_index('idx_market_prices_updated', table_name='market_prices', schema='integration')
    op.drop_index('idx_market_prices_price', table_name='market_prices', schema='integration')
    op.drop_index('idx_market_prices_supplier', table_name='market_prices', schema='integration')
    op.drop_index('idx_market_prices_source', table_name='market_prices', schema='integration')
    op.drop_index('idx_market_prices_product_id', table_name='market_prices', schema='integration')

    # Drop table
    op.drop_table('market_prices', schema='integration')

    print("Market prices table removed successfully!")

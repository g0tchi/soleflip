"""Create selling schema and tables for StockX integration

Revision ID: a1b2c3d4e5f6
Revises: 2025_09_18_0807_a82e22d786aa_create_market_prices_table_for_
Create Date: 2025-09-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = 'a1b2c3d4e5f6'
down_revision = 'a82e22d786aa'
branch_labels = None
depends_on = None


def upgrade():
    # Create selling schema
    op.execute("CREATE SCHEMA IF NOT EXISTS selling")

    # Create stockx_listings table
    op.create_table(
        'stockx_listings',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('product_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('products.products.id'), nullable=False),
        sa.Column('stockx_listing_id', sa.String(100), nullable=False, unique=True),
        sa.Column('stockx_product_id', sa.String(100), nullable=False),
        sa.Column('variant_id', sa.String(100), nullable=True),

        # Listing Details
        sa.Column('ask_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('original_ask_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('buy_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('expected_profit', sa.Numeric(10, 2), nullable=True),
        sa.Column('expected_margin', sa.Numeric(5, 2), nullable=True),

        # Status Management
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=True),

        # Market Data
        sa.Column('current_lowest_ask', sa.Numeric(10, 2), nullable=True),
        sa.Column('current_highest_bid', sa.Numeric(10, 2), nullable=True),
        sa.Column('last_price_update', sa.TIMESTAMP(timezone=True), nullable=True),

        # Source Tracking
        sa.Column('source_opportunity_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_from', sa.String(50), nullable=True, server_default='manual'),

        # Timestamps
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('listed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('delisted_at', sa.TIMESTAMP(timezone=True), nullable=True),

        schema='selling'
    )

    # Create stockx_orders table
    op.create_table(
        'stockx_orders',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('listing_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('selling.stockx_listings.id'), nullable=False),
        sa.Column('stockx_order_number', sa.String(100), nullable=False, unique=True),

        # Sale Details
        sa.Column('sale_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('buyer_premium', sa.Numeric(10, 2), nullable=True),
        sa.Column('seller_fee', sa.Numeric(10, 2), nullable=True),
        sa.Column('processing_fee', sa.Numeric(10, 2), nullable=True),
        sa.Column('net_proceeds', sa.Numeric(10, 2), nullable=True),

        # Profit Calculation
        sa.Column('original_buy_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('gross_profit', sa.Numeric(10, 2), nullable=True),
        sa.Column('net_profit', sa.Numeric(10, 2), nullable=True),
        sa.Column('actual_margin', sa.Numeric(5, 2), nullable=True),
        sa.Column('roi', sa.Numeric(5, 2), nullable=True),

        # Status & Tracking
        sa.Column('order_status', sa.String(20), nullable=True),
        sa.Column('shipping_status', sa.String(20), nullable=True),
        sa.Column('tracking_number', sa.String(100), nullable=True),

        # Timeline
        sa.Column('sold_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('shipped_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),

        schema='selling'
    )

    # Create pricing_history table
    op.create_table(
        'pricing_history',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('listing_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('selling.stockx_listings.id'), nullable=False),

        sa.Column('old_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('new_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('change_reason', sa.String(100), nullable=True),
        sa.Column('market_lowest_ask', sa.Numeric(10, 2), nullable=True),
        sa.Column('market_highest_bid', sa.Numeric(10, 2), nullable=True),

        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),

        schema='selling'
    )

    # Create indexes for performance
    op.create_index('idx_stockx_listings_status', 'stockx_listings', ['status'], schema='selling')
    op.create_index('idx_stockx_listings_active', 'stockx_listings', ['is_active'], schema='selling')
    op.create_index('idx_stockx_listings_product', 'stockx_listings', ['product_id'], schema='selling')
    op.create_index('idx_stockx_listings_stockx_id', 'stockx_listings', ['stockx_listing_id'], schema='selling')

    op.create_index('idx_stockx_orders_status', 'stockx_orders', ['order_status'], schema='selling')
    op.create_index('idx_stockx_orders_listing', 'stockx_orders', ['listing_id'], schema='selling')
    op.create_index('idx_stockx_orders_sold_at', 'stockx_orders', ['sold_at'], schema='selling')

    op.create_index('idx_pricing_history_listing', 'pricing_history', ['listing_id'], schema='selling')
    op.create_index('idx_pricing_history_created', 'pricing_history', ['created_at'], schema='selling')

    # Create constraints
    op.create_check_constraint(
        'ck_listing_status',
        'stockx_listings',
        "status IN ('active', 'inactive', 'sold', 'expired', 'cancelled')",
        schema='selling'
    )

    op.create_check_constraint(
        'ck_order_status',
        'stockx_orders',
        "order_status IN ('pending', 'authenticated', 'shipped', 'completed', 'cancelled')",
        schema='selling'
    )


def downgrade():
    # Drop indexes
    op.drop_index('idx_pricing_history_created', table_name='pricing_history', schema='selling')
    op.drop_index('idx_pricing_history_listing', table_name='pricing_history', schema='selling')
    op.drop_index('idx_stockx_orders_sold_at', table_name='stockx_orders', schema='selling')
    op.drop_index('idx_stockx_orders_listing', table_name='stockx_orders', schema='selling')
    op.drop_index('idx_stockx_orders_status', table_name='stockx_orders', schema='selling')
    op.drop_index('idx_stockx_listings_stockx_id', table_name='stockx_listings', schema='selling')
    op.drop_index('idx_stockx_listings_product', table_name='stockx_listings', schema='selling')
    op.drop_index('idx_stockx_listings_active', table_name='stockx_listings', schema='selling')
    op.drop_index('idx_stockx_listings_status', table_name='stockx_listings', schema='selling')

    # Drop tables
    op.drop_table('pricing_history', schema='selling')
    op.drop_table('stockx_orders', schema='selling')
    op.drop_table('stockx_listings', schema='selling')

    # Drop schema
    op.execute("DROP SCHEMA IF EXISTS selling CASCADE")
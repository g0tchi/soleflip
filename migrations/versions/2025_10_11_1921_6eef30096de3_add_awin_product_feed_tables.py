"""add_awin_product_feed_tables

Revision ID: 6eef30096de3
Revises: 3ef19f94d0a5
Create Date: 2025-10-11 19:21:18.492643

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '6eef30096de3'
down_revision = '3ef19f94d0a5'
branch_labels = None
depends_on = None


def upgrade():
    # Create integration schema if not exists
    op.execute("CREATE SCHEMA IF NOT EXISTS integration")

    # Create awin_products table
    op.create_table(
        'awin_products',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),

        # Awin IDs
        sa.Column('awin_product_id', sa.String(50), nullable=False),
        sa.Column('merchant_product_id', sa.String(100), nullable=True),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('merchant_name', sa.String(200), nullable=True),
        sa.Column('data_feed_id', sa.Integer(), nullable=True),

        # Product Info
        sa.Column('product_name', sa.String(500), nullable=False),
        sa.Column('brand_name', sa.String(200), nullable=True),
        sa.Column('brand_id', sa.Integer(), nullable=True),
        sa.Column('ean', sa.String(20), nullable=True),
        sa.Column('product_gtin', sa.String(20), nullable=True),
        sa.Column('mpn', sa.String(100), nullable=True),
        sa.Column('product_model', sa.String(200), nullable=True),

        # Pricing (in cents)
        sa.Column('retail_price_cents', sa.Integer(), nullable=True),
        sa.Column('store_price_cents', sa.Integer(), nullable=True),
        sa.Column('rrp_price_cents', sa.Integer(), nullable=True),
        sa.Column('currency', sa.String(3), server_default='EUR'),

        # Product Details
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('short_description', sa.Text(), nullable=True),
        sa.Column('colour', sa.String(100), nullable=True),
        sa.Column('size', sa.String(20), nullable=True),
        sa.Column('material', sa.String(200), nullable=True),

        # Stock
        sa.Column('in_stock', sa.Boolean(), server_default='false'),
        sa.Column('stock_quantity', sa.Integer(), server_default='0'),
        sa.Column('delivery_time', sa.String(100), nullable=True),

        # Images (JSONB for flexibility)
        sa.Column('image_url', sa.String(1000), nullable=True),
        sa.Column('thumbnail_url', sa.String(1000), nullable=True),
        sa.Column('alternate_images', sa.JSON(), nullable=True),

        # Links
        sa.Column('affiliate_link', sa.String(2000), nullable=True),
        sa.Column('merchant_link', sa.String(2000), nullable=True),

        # Matching to our products
        sa.Column('matched_product_id', sa.UUID(), nullable=True),
        sa.Column('match_confidence', sa.Numeric(3, 2), nullable=True),
        sa.Column('match_method', sa.String(50), nullable=True),

        # Metadata
        sa.Column('last_updated', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('feed_import_date', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),

        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('awin_product_id'),

        schema='integration'
    )

    # Create indexes for performance
    op.create_index('idx_awin_ean', 'awin_products', ['ean'], schema='integration')
    op.create_index('idx_awin_merchant', 'awin_products', ['merchant_id'], schema='integration')
    op.create_index('idx_awin_brand', 'awin_products', ['brand_name'], schema='integration')
    op.create_index('idx_awin_matched_product', 'awin_products', ['matched_product_id'], schema='integration')
    op.create_index('idx_awin_in_stock', 'awin_products', ['in_stock'], schema='integration')
    op.create_index('idx_awin_last_updated', 'awin_products', ['last_updated'], schema='integration')

    # Create price history table
    op.create_table(
        'awin_price_history',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('awin_product_id', sa.String(50), nullable=False),
        sa.Column('price_cents', sa.Integer(), nullable=False),
        sa.Column('in_stock', sa.Boolean(), nullable=True),
        sa.Column('recorded_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['awin_product_id'],
            ['integration.awin_products.awin_product_id'],
            ondelete='CASCADE'
        ),

        schema='integration'
    )

    op.create_index('idx_awin_price_history_product', 'awin_price_history', ['awin_product_id'], schema='integration')
    op.create_index('idx_awin_price_history_date', 'awin_price_history', ['recorded_at'], schema='integration')

    # Create trigger function for price change tracking
    op.execute("""
        CREATE OR REPLACE FUNCTION integration.track_awin_price_changes()
        RETURNS TRIGGER AS $$
        BEGIN
            IF OLD.retail_price_cents IS DISTINCT FROM NEW.retail_price_cents THEN
                INSERT INTO integration.awin_price_history
                    (awin_product_id, price_cents, in_stock, recorded_at)
                VALUES
                    (NEW.awin_product_id, NEW.retail_price_cents, NEW.in_stock, NOW());
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create trigger
    op.execute("""
        CREATE TRIGGER awin_price_change_trigger
        AFTER UPDATE ON integration.awin_products
        FOR EACH ROW
        EXECUTE FUNCTION integration.track_awin_price_changes();
    """)


def downgrade():
    # Drop trigger and function
    op.execute("DROP TRIGGER IF EXISTS awin_price_change_trigger ON integration.awin_products")
    op.execute("DROP FUNCTION IF EXISTS integration.track_awin_price_changes()")

    # Drop tables
    op.drop_table('awin_price_history', schema='integration')
    op.drop_table('awin_products', schema='integration')

"""add_notion_sale_fields

Add missing fields to support complete Notion sale data sync.

This migration adds purchase and sale tracking fields that exist in Notion
but were missing from PostgreSQL schema:

Inventory (products.inventory):
- delivery_date: When supplier delivered the item
- gross_purchase_price: Purchase price including VAT
- vat_amount: VAT amount paid
- vat_rate: VAT rate percentage (default 19% for Germany)

Orders (transactions.orders):
- sold_at: Sale completion date
- gross_sale: Sale price before fees/taxes
- net_proceeds: Net proceeds after platform fees
- gross_profit: Gross profit (sale - purchase)
- net_profit: Net profit after all costs
- roi: Return on investment percentage
- payout_received: Whether payout was received
- payout_date: Date payout was received
- shelf_life_days: Days between purchase and sale

Revision ID: 1fc1f0c9b64d
Revises: 887763befe74
Create Date: 2025-09-30 13:28:13.762205

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '1fc1f0c9b64d'
down_revision = '887763befe74'
branch_labels = None
depends_on = None


def upgrade():
    # Add inventory purchase tracking fields
    op.add_column(
        'inventory',
        sa.Column('delivery_date', sa.DateTime(timezone=True), nullable=True),
        schema='products'
    )
    op.add_column(
        'inventory',
        sa.Column('gross_purchase_price', sa.Numeric(precision=10, scale=2), nullable=True),
        schema='products'
    )
    op.add_column(
        'inventory',
        sa.Column('vat_amount', sa.Numeric(precision=10, scale=2), nullable=True),
        schema='products'
    )
    op.add_column(
        'inventory',
        sa.Column('vat_rate', sa.Numeric(precision=5, scale=2), server_default='19.00', nullable=True),
        schema='products'
    )

    # Add order financial tracking fields
    op.add_column(
        'orders',
        sa.Column('sold_at', sa.DateTime(timezone=True), nullable=True),
        schema='transactions'
    )
    op.add_column(
        'orders',
        sa.Column('gross_sale', sa.Numeric(precision=10, scale=2), nullable=True),
        schema='transactions'
    )
    op.add_column(
        'orders',
        sa.Column('net_proceeds', sa.Numeric(precision=10, scale=2), nullable=True),
        schema='transactions'
    )
    op.add_column(
        'orders',
        sa.Column('gross_profit', sa.Numeric(precision=10, scale=2), nullable=True),
        schema='transactions'
    )
    op.add_column(
        'orders',
        sa.Column('net_profit', sa.Numeric(precision=10, scale=2), nullable=True),
        schema='transactions'
    )
    op.add_column(
        'orders',
        sa.Column('roi', sa.Numeric(precision=5, scale=2), nullable=True),
        schema='transactions'
    )
    op.add_column(
        'orders',
        sa.Column('payout_received', sa.Boolean(), server_default='false', nullable=True),
        schema='transactions'
    )
    op.add_column(
        'orders',
        sa.Column('payout_date', sa.DateTime(timezone=True), nullable=True),
        schema='transactions'
    )
    op.add_column(
        'orders',
        sa.Column('shelf_life_days', sa.Integer(), nullable=True),
        schema='transactions'
    )

    # Add comments for documentation
    op.execute("COMMENT ON COLUMN products.inventory.delivery_date IS 'Delivery date from supplier'")
    op.execute("COMMENT ON COLUMN products.inventory.gross_purchase_price IS 'Purchase price including VAT'")
    op.execute("COMMENT ON COLUMN products.inventory.vat_amount IS 'VAT amount paid on purchase'")
    op.execute("COMMENT ON COLUMN products.inventory.vat_rate IS 'VAT rate percentage (e.g., 19.00 for Germany)'")

    op.execute("COMMENT ON COLUMN transactions.orders.sold_at IS 'Sale completion date'")
    op.execute("COMMENT ON COLUMN transactions.orders.gross_sale IS 'Gross sale amount before fees'")
    op.execute("COMMENT ON COLUMN transactions.orders.net_proceeds IS 'Net proceeds after platform fees'")
    op.execute("COMMENT ON COLUMN transactions.orders.gross_profit IS 'Sale price - Purchase price'")
    op.execute("COMMENT ON COLUMN transactions.orders.net_profit IS 'Net profit after all costs'")
    op.execute("COMMENT ON COLUMN transactions.orders.roi IS 'Return on investment percentage'")
    op.execute("COMMENT ON COLUMN transactions.orders.payout_received IS 'Whether payout was received'")
    op.execute("COMMENT ON COLUMN transactions.orders.payout_date IS 'Date payout was received'")
    op.execute("COMMENT ON COLUMN transactions.orders.shelf_life_days IS 'Days between purchase and sale'")

    # Add indexes for common queries
    op.create_index('idx_orders_sold_at', 'orders', ['sold_at'], schema='transactions')
    op.create_index('idx_orders_payout_received', 'orders', ['payout_received'], schema='transactions')
    op.create_index('idx_inventory_delivery_date', 'inventory', ['delivery_date'], schema='products')


def downgrade():
    # Drop indexes
    op.drop_index('idx_inventory_delivery_date', table_name='inventory', schema='products')
    op.drop_index('idx_orders_payout_received', table_name='orders', schema='transactions')
    op.drop_index('idx_orders_sold_at', table_name='orders', schema='transactions')

    # Drop order fields
    op.drop_column('orders', 'shelf_life_days', schema='transactions')
    op.drop_column('orders', 'payout_date', schema='transactions')
    op.drop_column('orders', 'payout_received', schema='transactions')
    op.drop_column('orders', 'roi', schema='transactions')
    op.drop_column('orders', 'net_profit', schema='transactions')
    op.drop_column('orders', 'gross_profit', schema='transactions')
    op.drop_column('orders', 'net_proceeds', schema='transactions')
    op.drop_column('orders', 'gross_sale', schema='transactions')
    op.drop_column('orders', 'sold_at', schema='transactions')

    # Drop inventory fields
    op.drop_column('inventory', 'vat_rate', schema='products')
    op.drop_column('inventory', 'vat_amount', schema='products')
    op.drop_column('inventory', 'gross_purchase_price', schema='products')
    op.drop_column('inventory', 'delivery_date', schema='products')

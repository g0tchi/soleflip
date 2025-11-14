"""make orders table multi platform compatible

Revision ID: 84bc4d8b03ef
Revises: 1fc1f0c9b64d
Create Date: 2025-10-01 07:30:38.730850

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '84bc4d8b03ef'
down_revision = '1fc1f0c9b64d'
branch_labels = None
depends_on = None


def upgrade():
    # Add platform_id to orders table to make it multi-platform compatible
    op.add_column('orders', sa.Column('platform_id', sa.UUID(), nullable=True), schema='transactions')

    # Add foreign key to platforms table
    op.create_foreign_key(
        'fk_orders_platform',
        'orders', 'platforms',
        ['platform_id'], ['id'],
        source_schema='transactions',
        referent_schema='core'
    )

    # Make stockx_order_number nullable (not all platforms have this format)
    op.alter_column('orders', 'stockx_order_number',
                    existing_type=sa.String(100),
                    nullable=True,
                    schema='transactions')

    # Add generic external_id field for other platforms
    op.add_column('orders', sa.Column('external_id', sa.String(200), nullable=True), schema='transactions')
    op.create_index('ix_orders_external_id', 'orders', ['external_id'], unique=False, schema='transactions')

    # Add platform-specific fee fields from transactions table
    op.add_column('orders', sa.Column('platform_fee', sa.Numeric(10, 2), nullable=True), schema='transactions')
    op.add_column('orders', sa.Column('shipping_cost', sa.Numeric(10, 2), nullable=True), schema='transactions')

    # Add buyer destination fields
    op.add_column('orders', sa.Column('buyer_destination_country', sa.String(100), nullable=True), schema='transactions')
    op.add_column('orders', sa.Column('buyer_destination_city', sa.String(200), nullable=True), schema='transactions')

    # Add notes field for flexible additional info
    op.add_column('orders', sa.Column('notes', sa.Text(), nullable=True), schema='transactions')

    # Set default platform to StockX for existing records
    # Get StockX platform ID first
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT id FROM core.platforms WHERE slug = 'stockx'"))
    stockx_platform = result.fetchone()

    if stockx_platform:
        stockx_id = stockx_platform[0]
        op.execute(
            sa.text(f"UPDATE transactions.orders SET platform_id = '{stockx_id}' WHERE platform_id IS NULL")
        )

    # Now make platform_id NOT NULL
    op.alter_column('orders', 'platform_id',
                    existing_type=sa.UUID(),
                    nullable=False,
                    schema='transactions')


def downgrade():
    # Remove new columns
    op.drop_column('orders', 'notes', schema='transactions')
    op.drop_column('orders', 'buyer_destination_city', schema='transactions')
    op.drop_column('orders', 'buyer_destination_country', schema='transactions')
    op.drop_column('orders', 'shipping_cost', schema='transactions')
    op.drop_column('orders', 'platform_fee', schema='transactions')

    op.drop_index('ix_orders_external_id', table_name='orders', schema='transactions')
    op.drop_column('orders', 'external_id', schema='transactions')

    # Restore stockx_order_number to NOT NULL
    op.alter_column('orders', 'stockx_order_number',
                    existing_type=sa.String(100),
                    nullable=False,
                    schema='transactions')

    # Remove foreign key and platform_id
    op.drop_constraint('fk_orders_platform', 'orders', schema='transactions', type_='foreignkey')
    op.drop_column('orders', 'platform_id', schema='transactions')

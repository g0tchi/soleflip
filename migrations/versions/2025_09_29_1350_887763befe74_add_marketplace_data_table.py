"""add_marketplace_data_table

Revision ID: 887763befe74
Revises: 319a23ef9c05
Create Date: 2025-09-29 13:50:55.598883

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '887763befe74'
down_revision = '319a23ef9c05'
branch_labels = None
depends_on = None


def upgrade():
    # Create marketplace_data table in analytics schema
    op.create_table('marketplace_data',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('inventory_item_id', sa.UUID(), nullable=False),
        sa.Column('platform_id', sa.UUID(), nullable=False),
        sa.Column('marketplace_listing_id', sa.String(length=255), nullable=True, comment='External listing identifier'),
        sa.Column('ask_price', sa.Numeric(precision=10, scale=2), nullable=True, comment='Current ask price'),
        sa.Column('bid_price', sa.Numeric(precision=10, scale=2), nullable=True, comment='Current bid price'),
        sa.Column('market_lowest_ask', sa.Numeric(precision=10, scale=2), nullable=True, comment='Lowest ask on the market'),
        sa.Column('market_highest_bid', sa.Numeric(precision=10, scale=2), nullable=True, comment='Highest bid on the market'),
        sa.Column('last_sale_price', sa.Numeric(precision=10, scale=2), nullable=True, comment='Most recent sale price'),
        sa.Column('sales_frequency', sa.Integer(), nullable=True, comment='Number of sales in last 30 days'),
        sa.Column('volatility', sa.Numeric(precision=5, scale=4), nullable=True, comment='Price volatility (0.0-1.0)'),
        sa.Column('fees_percentage', sa.Numeric(precision=5, scale=4), nullable=True, comment='Platform fees (0.08 = 8%)'),
        sa.Column('platform_specific', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Platform-specific metadata'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('volatility >= 0 AND volatility <= 1'),
        sa.CheckConstraint('fees_percentage >= 0 AND fees_percentage <= 1'),
        sa.ForeignKeyConstraint(['inventory_item_id'], ['products.inventory.id'], ),
        sa.ForeignKeyConstraint(['platform_id'], ['core.platforms.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('inventory_item_id', 'platform_id'),
        schema='analytics'
    )

    # Create indexes
    op.create_index('idx_marketplace_data_platform', 'marketplace_data', ['platform_id'], unique=False, schema='analytics')
    op.create_index('idx_marketplace_data_item', 'marketplace_data', ['inventory_item_id'], unique=False, schema='analytics')
    op.create_index('idx_marketplace_data_updated', 'marketplace_data', ['updated_at'], unique=False, schema='analytics')
    op.create_index('idx_marketplace_data_ask_price', 'marketplace_data', ['ask_price'], unique=False, schema='analytics', postgresql_where=sa.text('ask_price IS NOT NULL'))


def downgrade():
    # Drop indexes
    op.drop_index('idx_marketplace_data_ask_price', table_name='marketplace_data', schema='analytics')
    op.drop_index('idx_marketplace_data_updated', table_name='marketplace_data', schema='analytics')
    op.drop_index('idx_marketplace_data_item', table_name='marketplace_data', schema='analytics')
    op.drop_index('idx_marketplace_data_platform', table_name='marketplace_data', schema='analytics')

    # Drop table
    op.drop_table('marketplace_data', schema='analytics')

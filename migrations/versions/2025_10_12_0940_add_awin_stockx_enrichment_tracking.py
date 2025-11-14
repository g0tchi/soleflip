"""add_awin_stockx_enrichment_tracking

Revision ID: a7b8c9d0e1f2
Revises: 6eef30096de3
Create Date: 2025-10-12 09:40:00.000000

Adds enrichment job tracking and StockX matching data for Awin products
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'a7b8c9d0e1f2'
down_revision = '6eef30096de3'
branch_labels = None
depends_on = None


def upgrade():
    # Create enrichment jobs tracking table
    op.create_table(
        'awin_enrichment_jobs',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('job_type', sa.String(50), nullable=False),  # 'stockx_match', 'price_update', etc.
        sa.Column('status', sa.String(20), nullable=False),  # 'pending', 'running', 'completed', 'failed'

        # Progress tracking
        sa.Column('total_products', sa.Integer(), nullable=True),
        sa.Column('processed_products', sa.Integer(), server_default='0'),
        sa.Column('matched_products', sa.Integer(), server_default='0'),
        sa.Column('failed_products', sa.Integer(), server_default='0'),

        # Results
        sa.Column('results_summary', sa.JSON(), nullable=True),
        sa.Column('error_log', sa.Text(), nullable=True),

        # Timestamps
        sa.Column('started_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),

        sa.PrimaryKeyConstraint('id'),
        schema='integration'
    )

    # Create index for job status queries
    op.create_index('idx_awin_enrichment_jobs_status', 'awin_enrichment_jobs', ['status'], schema='integration')
    op.create_index('idx_awin_enrichment_jobs_created', 'awin_enrichment_jobs', ['created_at'], schema='integration')

    # Add StockX matching columns to awin_products
    op.add_column('awin_products', sa.Column('stockx_product_id', sa.UUID(), nullable=True), schema='integration')
    op.add_column('awin_products', sa.Column('stockx_url_key', sa.String(200), nullable=True), schema='integration')
    op.add_column('awin_products', sa.Column('stockx_style_id', sa.String(100), nullable=True), schema='integration')
    op.add_column('awin_products', sa.Column('stockx_lowest_ask_cents', sa.Integer(), nullable=True), schema='integration')
    op.add_column('awin_products', sa.Column('stockx_highest_bid_cents', sa.Integer(), nullable=True), schema='integration')
    op.add_column('awin_products', sa.Column('profit_cents', sa.Integer(), nullable=True), schema='integration')
    op.add_column('awin_products', sa.Column('profit_percentage', sa.Numeric(5, 2), nullable=True), schema='integration')
    op.add_column('awin_products', sa.Column('last_enriched_at', sa.TIMESTAMP(timezone=True), nullable=True), schema='integration')
    op.add_column('awin_products', sa.Column('enrichment_status', sa.String(20), server_default='pending'), schema='integration')  # 'pending', 'matched', 'not_found', 'error'

    # Create indexes for performance
    op.create_index('idx_awin_stockx_product_id', 'awin_products', ['stockx_product_id'], schema='integration')
    op.create_index('idx_awin_profit', 'awin_products', ['profit_cents'], schema='integration')
    op.create_index('idx_awin_enrichment_status', 'awin_products', ['enrichment_status'], schema='integration')


def downgrade():
    # Drop indexes
    op.drop_index('idx_awin_enrichment_status', 'awin_products', schema='integration')
    op.drop_index('idx_awin_profit', 'awin_products', schema='integration')
    op.drop_index('idx_awin_stockx_product_id', 'awin_products', schema='integration')
    op.drop_index('idx_awin_enrichment_jobs_created', 'awin_enrichment_jobs', schema='integration')
    op.drop_index('idx_awin_enrichment_jobs_status', 'awin_enrichment_jobs', schema='integration')

    # Drop columns
    op.drop_column('awin_products', 'enrichment_status', schema='integration')
    op.drop_column('awin_products', 'last_enriched_at', schema='integration')
    op.drop_column('awin_products', 'profit_percentage', schema='integration')
    op.drop_column('awin_products', 'profit_cents', schema='integration')
    op.drop_column('awin_products', 'stockx_highest_bid_cents', schema='integration')
    op.drop_column('awin_products', 'stockx_lowest_ask_cents', schema='integration')
    op.drop_column('awin_products', 'stockx_style_id', schema='integration')
    op.drop_column('awin_products', 'stockx_url_key', schema='integration')
    op.drop_column('awin_products', 'stockx_product_id', schema='integration')

    # Drop table
    op.drop_table('awin_enrichment_jobs', schema='integration')

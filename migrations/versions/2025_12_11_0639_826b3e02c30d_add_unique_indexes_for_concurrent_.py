"""Add unique indexes for concurrent materialized view refresh

Patch for Week 2-3 Optimizations

PostgreSQL requires UNIQUE indexes on materialized views for CONCURRENT refresh.
This migration adds the necessary unique indexes to enable lock-free refreshes.

Revision ID: 826b3e02c30d
Revises: 32adf6568b6f
Create Date: 2025-12-11 06:39:27.209890

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '826b3e02c30d'
down_revision = '32adf6568b6f'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add UNIQUE indexes to materialized views for concurrent refresh support.
    """

    # daily_sales_summary - unique on (sale_date, platform_id)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_sales_unique
        ON analytics.daily_sales_summary(sale_date, platform_id);
    """)

    # current_stock_summary - unique on product_id
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_stock_summary_unique
        ON analytics.current_stock_summary(product_id);
    """)

    # platform_performance - unique on platform_id
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_platform_perf_unique
        ON analytics.platform_performance(platform_id);
    """)


def downgrade():
    """
    Remove unique indexes from materialized views.
    """

    op.execute("DROP INDEX IF EXISTS analytics.idx_daily_sales_unique;")
    op.execute("DROP INDEX IF EXISTS analytics.idx_stock_summary_unique;")
    op.execute("DROP INDEX IF EXISTS analytics.idx_platform_perf_unique;")

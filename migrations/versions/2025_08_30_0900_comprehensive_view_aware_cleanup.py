"""Comprehensive view-aware cleanup migration

Revision ID: 2025_08_30_0900
Revises: 9233d7fa1f2a
Create Date: 2025-08-30 09:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '2025_08_30_0900'
down_revision = '9233d7fa1f2a'
branch_labels = None
depends_on = None


def upgrade():
    """
    Comprehensive cleanup that handles view dependencies properly.
    Strategy: Replace views that depend on buyer_id, then cleanup tables.
    """
    print("Starting comprehensive view-aware cleanup...")
    
    # Step 1: Drop views that depend on buyer_id column (2 views)
    print("Dropping views dependent on buyer_id...")
    op.execute('DROP VIEW IF EXISTS analytics.brand_loyalty_analysis CASCADE')
    op.execute('DROP VIEW IF EXISTS analytics.brand_trend_analysis CASCADE')
    
    # Step 2: Now safe to drop buyer_id column from transactions
    print("Dropping buyer_id column from transactions...")
    op.drop_column('transactions', 'buyer_id', schema='sales')
    
    # Step 3: Drop backup tables that may have view dependencies
    print("Dropping backup tables...")
    op.execute('DROP TABLE IF EXISTS products.inventory_backup CASCADE')
    op.execute('DROP TABLE IF EXISTS integration.import_records_backup CASCADE')
    
    # Step 4: Remove unused indexes (safe operations)
    print("Removing unused indexes...")
    try:
        op.drop_index('idx_inventory_supplier', table_name='inventory', schema='products')
    except Exception as e:
        print(f"Index removal skipped: {e}")
    
    # Step 5: Recreate essential views without buyer_id dependencies
    print("Recreating essential analytics views...")
    
    # Simplified brand trend analysis without buyer_id (using brand_id from products table)
    op.execute("""
    CREATE VIEW analytics.brand_trend_analysis AS
    SELECT 
        COALESCE(b.name, 'Unknown Brand') as brand,
        DATE_TRUNC('month', t.transaction_date) as month,
        COUNT(*) as transaction_count,
        SUM(t.sale_price) as total_revenue,
        AVG(t.sale_price) as avg_transaction_value
    FROM sales.transactions t
    JOIN products.inventory i ON t.inventory_id = i.id
    JOIN products.products pr ON i.product_id = pr.id
    LEFT JOIN products.brands b ON pr.brand_id = b.id
    WHERE t.transaction_date >= CURRENT_DATE - INTERVAL '12 months'
    GROUP BY b.name, DATE_TRUNC('month', t.transaction_date)
    ORDER BY month DESC, total_revenue DESC;
    """)
    
    # Simplified brand loyalty analysis without buyer references
    op.execute("""
    CREATE VIEW analytics.brand_loyalty_analysis AS
    SELECT 
        COALESCE(b.name, 'Unknown Brand') as brand,
        COUNT(DISTINCT DATE_TRUNC('month', t.transaction_date)) as active_months,
        COUNT(*) as total_transactions,
        SUM(t.sale_price) as total_spent,
        AVG(t.sale_price) as avg_order_value
    FROM sales.transactions t
    JOIN products.inventory i ON t.inventory_id = i.id
    JOIN products.products pr ON i.product_id = pr.id
    LEFT JOIN products.brands b ON pr.brand_id = b.id
    WHERE t.transaction_date >= CURRENT_DATE - INTERVAL '12 months'
    GROUP BY b.name
    HAVING COUNT(*) > 1
    ORDER BY total_spent DESC;
    """)
    
    print("Comprehensive cleanup completed successfully!")


def downgrade():
    """
    Rollback the comprehensive cleanup.
    Note: Cannot restore dropped tables without original data.
    """
    print("Rolling back comprehensive cleanup...")
    
    # Drop recreated views
    op.execute('DROP VIEW IF EXISTS analytics.brand_trend_analysis CASCADE')
    op.execute('DROP VIEW IF EXISTS analytics.brand_loyalty_analysis CASCADE')
    
    # Note: Cannot restore buyer_id column or backup tables without data
    print("Rollback completed - manual data restoration may be required")
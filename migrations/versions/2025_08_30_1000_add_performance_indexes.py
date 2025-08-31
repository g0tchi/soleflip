"""Add performance indexes for frequently queried columns

Revision ID: 2025_08_30_1000
Revises: 2025_08_30_0915
Create Date: 2025-08-30 10:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '2025_08_30_1000'
down_revision = '2025_08_30_0915'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add critical performance indexes for frequently queried columns.
    Based on codebase analysis identifying N+1 query patterns and filter operations.
    """
    print("Adding performance indexes...")
    
    # Inventory status index - heavily used in status filtering
    op.create_index('idx_inventory_status', 'inventory', ['status'], schema='products')
    print("[OK] Added index on products.inventory.status")
    
    # Transaction date index - used in date range queries and analytics
    op.create_index('idx_transaction_date', 'transactions', ['transaction_date'], schema='sales')
    print("[OK] Added index on sales.transactions.transaction_date")
    
    # Import records status index - used in batch processing
    op.create_index('idx_import_record_status', 'import_records', ['status'], schema='integration')
    print("[OK] Added index on integration.import_records.status")
    
    # Product SKU optimization (already unique, but improve lookup performance)
    op.create_index('idx_products_sku_lookup', 'products', ['sku'], schema='products')
    print("[OK] Added optimized index on products.products.sku")
    
    # Brand ID for product lookups (used in analytics joins)
    op.create_index('idx_products_brand_id', 'products', ['brand_id'], schema='products')
    print("[OK] Added index on products.products.brand_id")
    
    # Category ID for product filtering
    op.create_index('idx_products_category_id', 'products', ['category_id'], schema='products')
    print("[OK] Added index on products.products.category_id")
    
    # Inventory product_id for efficient joins
    op.create_index('idx_inventory_product_id', 'inventory', ['product_id'], schema='products')
    print("[OK] Added index on products.inventory.product_id")
    
    # Transaction inventory_id for sales tracking
    op.create_index('idx_transaction_inventory_id', 'transactions', ['inventory_id'], schema='sales')
    print("[OK] Added index on sales.transactions.inventory_id")
    
    # Composite index for transaction date + status (common query pattern)
    op.create_index('idx_transaction_date_status', 'transactions', ['transaction_date', 'status'], schema='sales')
    print("[OK] Added composite index on sales.transactions (transaction_date, status)")
    
    print("Performance indexes added successfully!")


def downgrade():
    """Remove the performance indexes"""
    print("Removing performance indexes...")
    
    # Remove all indexes in reverse order
    op.drop_index('idx_transaction_date_status', table_name='transactions', schema='sales')
    op.drop_index('idx_transaction_inventory_id', table_name='transactions', schema='sales')
    op.drop_index('idx_inventory_product_id', table_name='inventory', schema='products')
    op.drop_index('idx_products_category_id', table_name='products', schema='products')
    op.drop_index('idx_products_brand_id', table_name='products', schema='products')
    op.drop_index('idx_products_sku_lookup', table_name='products', schema='products')
    op.drop_index('idx_import_record_status', table_name='import_records', schema='integration')
    op.drop_index('idx_transaction_date', table_name='transactions', schema='sales')
    op.drop_index('idx_inventory_status', table_name='inventory', schema='products')
    
    print("Performance indexes removed successfully!")
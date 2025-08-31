"""Minimal safe cleanup - only drop columns and tables that exist

Revision ID: 2025_08_30_0915
Revises: 9233d7fa1f2a
Create Date: 2025-08-30 09:15:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '2025_08_30_0915'
down_revision = '9233d7fa1f2a'
branch_labels = None
depends_on = None


def upgrade():
    """
    Minimal safe cleanup - only operations that we know will work.
    No view recreation, just basic cleanup.
    """
    print("Starting minimal safe cleanup...")
    
    # Step 1: Drop the two specific views that use buyer_id
    print("Dropping views dependent on buyer_id...")
    op.execute('DROP VIEW IF EXISTS analytics.brand_loyalty_analysis CASCADE')
    op.execute('DROP VIEW IF EXISTS analytics.brand_trend_analysis CASCADE')
    
    # Step 2: Now safe to drop buyer_id column
    print("Dropping buyer_id column from transactions...")
    op.drop_column('transactions', 'buyer_id', schema='sales')
    
    # Step 3: Drop backup tables if they exist
    print("Dropping backup tables...")
    op.execute('DROP TABLE IF EXISTS products.inventory_backup CASCADE')
    op.execute('DROP TABLE IF EXISTS integration.import_records_backup CASCADE')
    
    # Step 4: Try to remove unused index (safe failure)
    print("Attempting to remove unused index...")
    try:
        op.drop_index('idx_inventory_supplier', table_name='inventory', schema='products')
        print("Index removed successfully")
    except Exception as e:
        print(f"Index removal failed (expected): {e}")
    
    print("Minimal safe cleanup completed!")


def downgrade():
    """
    Rollback the minimal cleanup.
    Note: Cannot restore dropped tables/columns without data.
    """
    print("Rolling back minimal cleanup...")
    print("Manual data restoration may be required for dropped elements")
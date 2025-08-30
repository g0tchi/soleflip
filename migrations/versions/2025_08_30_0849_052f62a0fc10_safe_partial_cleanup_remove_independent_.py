"""Safe partial cleanup - remove independent unused tables only

Revision ID: 052f62a0fc10
Revises: 9233d7fa1f2a
Create Date: 2025-08-30 08:49:11.878007

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '052f62a0fc10'
down_revision = '9233d7fa1f2a'
branch_labels = None
depends_on = None


def upgrade():
    """
    Safe partial cleanup - removing only tables/columns that have no dependencies
    Skipping: brand_financials, brand_history, brand_collaborations, brand_attributes, buyers
    (These have view dependencies)
    """
    # Safe to remove - no view dependencies found
    op.drop_table('inventory_backup', schema='products')
    op.drop_table('import_records_backup', schema='integration')
    
    # Remove unused indexes from inventory table (safe)
    op.drop_index('idx_inventory_supplier', table_name='inventory', schema='products')
    
    # Remove unused columns from transactions table (safe)
    op.drop_column('transactions', 'buyer_id', schema='sales')
    
    print("✅ Safe partial cleanup completed - removed independent tables only")


def downgrade():
    """Rollback the safe cleanup changes"""
    # Note: Cannot recreate dropped tables without data
    # This is primarily for reference
    pass

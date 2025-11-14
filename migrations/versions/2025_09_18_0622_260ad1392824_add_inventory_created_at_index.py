"""add_inventory_created_at_index

Revision ID: 260ad1392824
Revises: 930405202c44
Create Date: 2025-09-18 06:22:45.177661

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '260ad1392824'
down_revision = '930405202c44'
branch_labels = None
depends_on = None


def upgrade():
    """Add index on inventory.created_at for pagination ordering"""
    print("Adding inventory created_at index for pagination performance...")

    # Add index for created_at ordering used in pagination
    op.create_index('idx_inventory_created_at', 'inventory', ['created_at'], schema='products')
    print("[OK] Added index on products.inventory.created_at")

    # Composite index for status + created_at (common filter + order pattern)
    op.create_index('idx_inventory_status_created_at', 'inventory', ['status', 'created_at'], schema='products')
    print("[OK] Added composite index on products.inventory (status, created_at)")

    print("Inventory pagination indexes added successfully!")


def downgrade():
    """Remove the inventory pagination indexes"""
    print("Removing inventory pagination indexes...")

    op.drop_index('idx_inventory_status_created_at', table_name='inventory', schema='products')
    op.drop_index('idx_inventory_created_at', table_name='inventory', schema='products')

    print("Inventory pagination indexes removed successfully!")

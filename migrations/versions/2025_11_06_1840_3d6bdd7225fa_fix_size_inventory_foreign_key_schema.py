"""fix_size_inventory_foreign_key_schema

Revision ID: 3d6bdd7225fa
Revises: b8cf8f271d37
Create Date: 2025-11-06 18:40:40.019172

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '3d6bdd7225fa'
down_revision = 'b8cf8f271d37'
branch_labels = None
depends_on = None


def upgrade():
    # Add missing foreign key constraint from inventory.stock.size_id to catalog.sizes.id
    # Using NOT VALID to allow existing invalid data (will be cleaned up later)
    op.execute("""
        ALTER TABLE inventory.stock
        ADD CONSTRAINT stock_size_id_fkey
        FOREIGN KEY (size_id)
        REFERENCES catalog.sizes(id)
        NOT VALID
    """)
    # Note: Run VALIDATE CONSTRAINT later after data cleanup


def downgrade():
    # Remove the foreign key constraint
    op.drop_constraint(
        'stock_size_id_fkey',
        'stock',
        schema='inventory',
        type_='foreignkey'
    )

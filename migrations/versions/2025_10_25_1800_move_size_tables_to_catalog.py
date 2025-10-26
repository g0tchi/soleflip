"""move_size_tables_to_catalog

Revision ID: move_size_tables_to_catalog
Revises: add_gibson_size_system
Create Date: 2025-10-25 18:00:00.000000

Reorganizes size tables from core to catalog schema following Gibson AI recommendations:
- Moves core.size_master → catalog.size_master
- Moves core.size_conversion → catalog.size_conversion
- Updates all foreign key references
- Maintains data integrity and referential constraints

Domain-Driven Design rationale:
- Size data is product catalog metadata, not core system infrastructure
- Size conversions support product presentation and merchandising
- Aligns with catalog domain responsibilities

Foreign key updates:
1. catalog.product_variant.size_master_id → catalog.size_master
2. core.size_validation_log.size_master_id → catalog.size_master

Note: core.sizes (legacy) and core.size_validation_log remain in core schema.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'move_size_tables_to_catalog'
down_revision = 'add_gibson_size_system'
branch_labels = None
depends_on = None


def upgrade():
    """Move size_master and size_conversion from core to catalog schema."""

    # Step 1: Drop existing foreign key constraints that reference core.size_master
    print("Dropping foreign key constraints...")
    op.drop_constraint('product_variant_size_master_id_fkey', 'product_variant', schema='catalog', type_='foreignkey')
    op.drop_constraint('size_validation_log_size_master_id_fkey', 'size_validation_log', schema='core', type_='foreignkey')

    # Step 2: Move size_master table to catalog schema
    print("Moving core.size_master to catalog.size_master...")
    op.execute('ALTER TABLE core.size_master SET SCHEMA catalog')

    # Step 3: Move size_conversion table to catalog schema
    print("Moving core.size_conversion to catalog.size_conversion...")
    op.execute('ALTER TABLE core.size_conversion SET SCHEMA catalog')

    # Step 4: Recreate foreign key constraints pointing to catalog.size_master
    print("Recreating foreign key constraints...")
    op.create_foreign_key(
        'product_variant_size_master_id_fkey',
        'product_variant', 'size_master',
        ['size_master_id'], ['id'],
        source_schema='catalog', referent_schema='catalog'
    )

    op.create_foreign_key(
        'size_validation_log_size_master_id_fkey',
        'size_validation_log', 'size_master',
        ['size_master_id'], ['id'],
        source_schema='core', referent_schema='catalog',
        ondelete='CASCADE'
    )

    print("✅ Size tables successfully moved to catalog schema")


def downgrade():
    """Revert size_master and size_conversion back to core schema."""

    # Step 1: Drop foreign key constraints
    print("Dropping foreign key constraints...")
    op.drop_constraint('product_variant_size_master_id_fkey', 'product_variant', schema='catalog', type_='foreignkey')
    op.drop_constraint('size_validation_log_size_master_id_fkey', 'size_validation_log', schema='core', type_='foreignkey')

    # Step 2: Move tables back to core schema
    print("Moving catalog.size_master back to core.size_master...")
    op.execute('ALTER TABLE catalog.size_master SET SCHEMA core')

    print("Moving catalog.size_conversion back to core.size_conversion...")
    op.execute('ALTER TABLE catalog.size_conversion SET SCHEMA core')

    # Step 3: Recreate original foreign key constraints
    print("Recreating original foreign key constraints...")
    op.create_foreign_key(
        'product_variant_size_master_id_fkey',
        'product_variant', 'size_master',
        ['size_master_id'], ['id'],
        source_schema='catalog', referent_schema='core'
    )

    op.create_foreign_key(
        'size_validation_log_size_master_id_fkey',
        'size_validation_log', 'size_master',
        ['size_master_id'], ['id'],
        source_schema='core', referent_schema='core',
        ondelete='CASCADE'
    )

    print("✅ Size tables successfully reverted to core schema")

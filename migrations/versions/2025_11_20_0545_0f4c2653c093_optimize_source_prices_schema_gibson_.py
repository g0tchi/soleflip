"""optimize_source_prices_schema_gibson_recommendations

Gibson AI recommended optimizations for integration.source_prices table:
- Add UNIQUE constraint on (product_id, source, supplier_name) for efficient upserts
- Add performance indexes for common queries
- Enables efficient profit opportunity calculations

Revision ID: 0f4c2653c093
Revises: 9a81f76b2638
Create Date: 2025-11-20 05:45:08.873143

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '0f4c2653c093'
down_revision = '9a81f76b2638'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add UNIQUE constraint for upserts
    # First, remove any duplicate entries (keep most recent)
    op.execute("""
        DELETE FROM integration.source_prices sp1
        USING integration.source_prices sp2
        WHERE sp1.id < sp2.id
          AND sp1.product_id = sp2.product_id
          AND sp1.source = sp2.source
          AND sp1.supplier_name = sp2.supplier_name;
    """)

    # Now add the UNIQUE constraint
    op.create_unique_constraint(
        'uq_source_prices_product_source_supplier',
        'source_prices',
        ['product_id', 'source', 'supplier_name'],
        schema='integration'
    )

    # 2. Add performance indexes
    # Fast product price lookups
    op.create_index(
        'idx_source_prices_product_id',
        'source_prices',
        ['product_id'],
        schema='integration'
    )

    # Filter by source
    op.create_index(
        'idx_source_prices_source',
        'source_prices',
        ['source'],
        schema='integration'
    )

    # Filter by availability (for in-stock queries)
    op.create_index(
        'idx_source_prices_availability',
        'source_prices',
        ['availability'],
        schema='integration'
    )

    # Composite index for profit opportunity queries
    op.create_index(
        'idx_source_prices_product_availability',
        'source_prices',
        ['product_id', 'availability'],
        schema='integration'
    )

    # Index on last_updated for freshness queries
    op.create_index(
        'idx_source_prices_last_updated',
        'source_prices',
        ['last_updated'],
        schema='integration'
    )


def downgrade():
    # Drop indexes
    op.drop_index('idx_source_prices_last_updated', table_name='source_prices', schema='integration')
    op.drop_index('idx_source_prices_product_availability', table_name='source_prices', schema='integration')
    op.drop_index('idx_source_prices_availability', table_name='source_prices', schema='integration')
    op.drop_index('idx_source_prices_source', table_name='source_prices', schema='integration')
    op.drop_index('idx_source_prices_product_id', table_name='source_prices', schema='integration')

    # Drop UNIQUE constraint
    op.drop_constraint('uq_source_prices_product_source_supplier', 'source_prices', schema='integration')

"""add_gibson_enrichment_optimizations

Gibson AI recommended optimizations for StockX enrichment schema:
- Add enrichment_version for API versioning
- Add UNIQUE constraint on stockx_product_id
- Add composite index on (lowest_ask, highest_bid) for price queries

Revision ID: 9e2361a7c480
Revises: 3d6bdd7225fa
Create Date: 2025-11-19 06:08:35.712004

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '9e2361a7c480'
down_revision = '3d6bdd7225fa'
branch_labels = None
depends_on = None


def upgrade():
    # Add enrichment_version column for API versioning
    op.add_column(
        'product',
        sa.Column(
            'enrichment_version',
            sa.Integer,
            nullable=True,
            server_default='1',
            comment='StockX API version used for enrichment'
        ),
        schema='catalog'
    )

    # Add UNIQUE constraint on stockx_product_id (currently only indexed)
    # First, check if there are duplicates and handle them
    op.execute("""
        -- Remove duplicate stockx_product_ids, keeping the most recently enriched
        DELETE FROM catalog.product p1
        USING catalog.product p2
        WHERE p1.id < p2.id
          AND p1.stockx_product_id = p2.stockx_product_id
          AND p1.stockx_product_id IS NOT NULL
          AND p2.stockx_product_id IS NOT NULL;
    """)

    # Now add the UNIQUE constraint
    op.create_unique_constraint(
        'uq_product_stockx_id',
        'product',
        ['stockx_product_id'],
        schema='catalog'
    )

    # Add composite index on pricing columns for performance
    op.create_index(
        'idx_product_pricing',
        'product',
        ['lowest_ask', 'highest_bid'],
        schema='catalog'
    )


def downgrade():
    # Drop composite index
    op.drop_index('idx_product_pricing', table_name='product', schema='catalog')

    # Drop UNIQUE constraint
    op.drop_constraint('uq_product_stockx_id', 'product', schema='catalog')

    # Drop enrichment_version column
    op.drop_column('product', 'enrichment_version', schema='catalog')

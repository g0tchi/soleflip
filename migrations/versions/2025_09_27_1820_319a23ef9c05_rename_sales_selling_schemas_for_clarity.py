"""rename_sales_selling_schemas_for_clarity

Revision ID: 319a23ef9c05
Revises: business_intelligence_fields
Create Date: 2025-09-27 18:20:38.188734

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '319a23ef9c05'
down_revision = 'business_intelligence_fields'
branch_labels = None
depends_on = None


def upgrade():
    """
    Rename schemas for better clarity:
    - 'sales' → 'transactions' (general transaction processing)
    - 'selling' → 'platforms' (platform-specific integrations)

    This resolves the confusing naming between sales/selling schemas
    and provides clearer semantic meaning.
    """
    # Rename sales schema to transactions
    op.execute('ALTER SCHEMA sales RENAME TO transactions')

    # Rename selling schema to platforms
    op.execute('ALTER SCHEMA selling RENAME TO platforms')


def downgrade():
    """
    Revert schema renames back to original names
    """
    # Revert transactions schema back to sales
    op.execute('ALTER SCHEMA transactions RENAME TO sales')

    # Revert platforms schema back to selling
    op.execute('ALTER SCHEMA platforms RENAME TO selling')

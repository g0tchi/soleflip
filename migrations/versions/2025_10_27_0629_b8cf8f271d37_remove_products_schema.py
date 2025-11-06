"""remove_products_schema

Revision ID: b8cf8f271d37
Revises: 315da5b21535
Create Date: 2025-10-27 06:29:08.383547

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'b8cf8f271d37'
down_revision = '315da5b21535'
branch_labels = None
depends_on = None


def upgrade():
    # Remove obsolete products schema
    # All product-related tables now in catalog schema per Gibson best practices
    op.execute("DROP SCHEMA IF EXISTS products CASCADE")


def downgrade():
    # Cannot restore - products schema replaced by catalog schema
    pass

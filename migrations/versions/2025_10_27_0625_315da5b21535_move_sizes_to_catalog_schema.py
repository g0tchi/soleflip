"""move_sizes_to_catalog_schema

Revision ID: 315da5b21535
Revises: 811f510987fb
Create Date: 2025-10-27 06:25:29.297432

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '315da5b21535'
down_revision = '811f510987fb'
branch_labels = None
depends_on = None


def upgrade():
    # Remove sizes table from inventory schema
    # catalog.sizes already exists (Gibson best practice location)
    # According to Gibson: sizes are reference data and belong in catalog schema
    op.execute("DROP TABLE IF EXISTS inventory.sizes CASCADE")


def downgrade():
    # Cannot restore - sizes belong in catalog schema per Gibson best practices
    pass

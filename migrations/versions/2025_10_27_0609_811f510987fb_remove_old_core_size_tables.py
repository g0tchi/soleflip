"""remove_old_core_size_tables

Revision ID: 811f510987fb
Revises: cleanup_obsolete_schemas
Create Date: 2025-10-27 06:09:09.279132

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '811f510987fb'
down_revision = 'cleanup_obsolete_schemas'
branch_labels = None
depends_on = None


def upgrade():
    # Drop old size tables from core schema (moved to inventory schema in Gibson v2.4)
    op.execute("DROP TABLE IF EXISTS core.size_validation_log CASCADE")
    op.execute("DROP TABLE IF EXISTS core.sizes CASCADE")


def downgrade():
    # Cannot restore old tables - data already migrated to inventory schema
    pass

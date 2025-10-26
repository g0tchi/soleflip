"""Cleanup obsolete schemas

Revision ID: cleanup_obsolete_schemas
Revises: add_gibson_features
Create Date: 2025-10-25 21:00:00.000000

Description:
    Removes 6 empty schemas that were created by the consolidated_fresh_start migration
    but became obsolete after the DDD restructuring (v2.3.4).

    Deleted schemas:
    - forecasting (never used, 0 tables)
    - orders (superseded by sales schema, 0 tables)
    - platforms (duplicate of platform, 0 tables)
    - product (duplicate of catalog, 0 tables)
    - products (duplicate of catalog, 0 tables)
    - transaction (duplicate of financial, 0 tables)

    Current schema structure (post-cleanup):
    - catalog (product management)
    - inventory (stock management)
    - sales (order management)
    - supplier (supplier management)
    - integration (import processing)
    - pricing (pricing engine)
    - analytics (business intelligence)
    - compliance (business rules & RBAC)
    - operations (operational data)
    - core (system configuration)
    - auth (authentication)
    - platform (marketplace configs)
    - financial (financial transactions)
    - logging (event & audit logs)
    - realtime (live events)
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'cleanup_obsolete_schemas'
down_revision = 'add_gibson_features'
branch_labels = None
depends_on = None


def upgrade():
    """Remove obsolete empty schemas"""
    # These schemas are completely empty and not referenced anywhere in the codebase
    op.execute('DROP SCHEMA IF EXISTS forecasting CASCADE')
    op.execute('DROP SCHEMA IF EXISTS orders CASCADE')
    op.execute('DROP SCHEMA IF EXISTS platforms CASCADE')
    op.execute('DROP SCHEMA IF EXISTS product CASCADE')
    op.execute('DROP SCHEMA IF EXISTS products CASCADE')
    op.execute('DROP SCHEMA IF EXISTS transaction CASCADE')


def downgrade():
    """Recreate the schemas (empty, for rollback only)"""
    op.execute('CREATE SCHEMA IF NOT EXISTS forecasting')
    op.execute('CREATE SCHEMA IF NOT EXISTS orders')
    op.execute('CREATE SCHEMA IF NOT EXISTS platforms')
    op.execute('CREATE SCHEMA IF NOT EXISTS product')
    op.execute('CREATE SCHEMA IF NOT EXISTS products')
    op.execute('CREATE SCHEMA IF NOT EXISTS transaction')

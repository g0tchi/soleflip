"""add_gibson_features

Revision ID: add_gibson_features
Revises: add_brand_supplier_history
Create Date: 2025-10-25 20:00:00.000000

Adds missing Gibson features to PostgreSQL schema:
1. Compliance module - Business rules, data retention, permissions
2. Operations module - Listing history, order fulfillment, supplier platform integration
3. Realtime event log - Real-time notification tracking
4. Analytics materialized views - Performance dashboards
5. Product inventory split - Detailed inventory tracking (financial, lifecycle, reservation)

Keeps PostgreSQL-specific features:
- auth schema (local authentication)
- brand_history, supplier_history (timeline tracking)
- brand_patterns (brand intelligence)
- forecast_accuracy (ML metrics)
- sizes, size_validation_log (legacy/validation)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_gibson_features'
down_revision = 'add_brand_supplier_history'
branch_labels = None
depends_on = None


def upgrade():
    """Add missing Gibson features to PostgreSQL."""

    # ================================================
    # 1. CREATE COMPLIANCE SCHEMA & TABLES
    # ================================================
    print("Creating compliance schema...")
    op.execute('CREATE SCHEMA IF NOT EXISTS compliance')

    # compliance.business_rules
    op.create_table(
        'business_rules',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('rule_name', sa.String(255), nullable=False, unique=True),
        sa.Column('description', sa.Text()),
        sa.Column('conditions', postgresql.JSONB()),
        sa.Column('actions', postgresql.JSONB()),
        sa.Column('active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        schema='compliance'
    )
    op.create_index('idx_business_rules_active', 'business_rules', ['active'], schema='compliance')

    # compliance.data_retention_policies
    op.create_table(
        'data_retention_policies',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('entity_name', sa.String(255), nullable=False, unique=True),
        sa.Column('retention_period_days', sa.Integer(), nullable=False),
        sa.Column('effective_date', sa.Date(), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        schema='compliance'
    )

    # compliance.user_permissions
    op.create_table(
        'user_permissions',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('permission_key', sa.String(255), nullable=False),
        sa.Column('granted_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('granted_by', sa.String(100)),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'permission_key', name='unique_user_permission'),
        sa.ForeignKeyConstraint(['user_id'], ['auth.users.id'], ondelete='CASCADE'),
        schema='compliance'
    )
    op.create_index('idx_user_permissions_user', 'user_permissions', ['user_id'], schema='compliance')
    op.create_index('idx_user_permissions_active', 'user_permissions', ['user_id', 'expires_at'],
                    schema='compliance',
                    postgresql_where=sa.text("expires_at IS NULL OR expires_at > now()"))

    # ================================================
    # 2. CREATE OPERATIONS SCHEMA & TABLES
    # ================================================
    print("Creating operations schema...")
    op.execute('CREATE SCHEMA IF NOT EXISTS operations')

    # operations.listing_history
    op.create_table(
        'listing_history',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('listing_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('previous_status', sa.String(20)),
        sa.Column('change_reason', sa.String(255)),
        sa.Column('changed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('changed_by', sa.String(100)),
        sa.Column('metadata', postgresql.JSONB()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['listing_id'], ['sales.listing.id'], ondelete='CASCADE'),
        schema='operations'
    )
    op.create_index('idx_listing_history_listing', 'listing_history', ['listing_id'], schema='operations')
    op.create_index('idx_listing_history_changed_at', 'listing_history', ['changed_at'], schema='operations')

    # operations.order_fulfillment
    op.create_table(
        'order_fulfillment',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('order_id', sa.UUID(), nullable=False),
        sa.Column('shipping_provider', sa.String(100)),
        sa.Column('tracking_number', sa.String(255)),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('shipped_at', sa.DateTime(timezone=True)),
        sa.Column('delivered_at', sa.DateTime(timezone=True)),
        sa.Column('estimated_delivery', sa.Date()),
        sa.Column('notes', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['order_id'], ['sales.order.id'], ondelete='CASCADE'),
        schema='operations'
    )
    op.create_index('idx_order_fulfillment_order', 'order_fulfillment', ['order_id'], schema='operations')
    op.create_index('idx_order_fulfillment_status', 'order_fulfillment', ['status'], schema='operations')
    op.create_index('idx_order_fulfillment_tracking', 'order_fulfillment', ['tracking_number'], schema='operations')

    # operations.supplier_platform_integration
    op.create_table(
        'supplier_platform_integration',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('supplier_id', sa.UUID(), nullable=False),
        sa.Column('platform_id', sa.UUID(), nullable=False),
        sa.Column('integration_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('api_credentials', postgresql.JSONB()),
        sa.Column('sync_settings', postgresql.JSONB()),
        sa.Column('last_sync_at', sa.DateTime(timezone=True)),
        sa.Column('sync_status', sa.String(50)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('supplier_id', 'platform_id', name='unique_supplier_platform'),
        sa.ForeignKeyConstraint(['supplier_id'], ['supplier.profile.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['platform_id'], ['platform.marketplace.id'], ondelete='CASCADE'),
        schema='operations'
    )
    op.create_index('idx_supplier_platform_supplier', 'supplier_platform_integration',
                    ['supplier_id'], schema='operations')
    op.create_index('idx_supplier_platform_active', 'supplier_platform_integration',
                    ['supplier_id', 'integration_active'], schema='operations')

    # ================================================
    # 3. CREATE REALTIME SCHEMA & TABLE
    # ================================================
    print("Creating realtime schema...")
    op.execute('CREATE SCHEMA IF NOT EXISTS realtime')

    op.create_table(
        'event_log',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('event_id', sa.String(100), nullable=False, unique=True),
        sa.Column('channel_name', sa.String(255), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('event_payload', postgresql.JSONB(), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('source_table', sa.String(255)),
        sa.Column('source_record_id', sa.UUID()),
        sa.Column('user_id', sa.UUID()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        schema='realtime'
    )
    op.create_index('idx_realtime_event_channel', 'event_log', ['channel_name'], schema='realtime')
    op.create_index('idx_realtime_event_type', 'event_log', ['event_type'], schema='realtime')
    op.create_index('idx_realtime_event_sent_at', 'event_log', ['sent_at'], schema='realtime')

    # ================================================
    # 4. ADD PRODUCT INVENTORY SPLIT TABLES
    # ================================================
    print("Creating product inventory split tables...")

    # Note: We're adding these to the existing inventory schema (not product schema)
    # to match our PostgreSQL structure

    # inventory.stock_financial
    op.create_table(
        'stock_financial',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('stock_id', sa.UUID(), nullable=False),
        sa.Column('purchase_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('gross_purchase_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('vat_amount', sa.Numeric(10, 2), nullable=False, default=0),
        sa.Column('profit_per_shelf_day', sa.Numeric(10, 2)),
        sa.Column('roi', sa.Numeric(5, 2)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['stock_id'], ['inventory.stock.id'], ondelete='CASCADE'),
        schema='inventory'
    )
    op.create_index('idx_stock_financial_stock', 'stock_financial', ['stock_id'], schema='inventory')

    # inventory.stock_lifecycle
    op.create_table(
        'stock_lifecycle',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('stock_id', sa.UUID(), nullable=False),
        sa.Column('shelf_life_days', sa.Integer()),
        sa.Column('listed_on_platforms', postgresql.JSONB(), comment='Array of platform IDs where listed'),
        sa.Column('status_history', postgresql.JSONB(), comment='Timeline of status changes'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['stock_id'], ['inventory.stock.id'], ondelete='CASCADE'),
        schema='inventory'
    )
    op.create_index('idx_stock_lifecycle_stock', 'stock_lifecycle', ['stock_id'], schema='inventory')

    # inventory.stock_reservation
    op.create_table(
        'stock_reservation',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('stock_id', sa.UUID(), nullable=False),
        sa.Column('reserved_quantity', sa.Integer(), nullable=False),
        sa.Column('reserved_until', sa.DateTime(timezone=True)),
        sa.Column('reservation_reason', sa.Text()),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('reserved_by', sa.String(100)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['stock_id'], ['inventory.stock.id'], ondelete='CASCADE'),
        schema='inventory'
    )
    op.create_index('idx_stock_reservation_stock', 'stock_reservation', ['stock_id'], schema='inventory')
    op.create_index('idx_stock_reservation_active', 'stock_reservation', ['stock_id', 'status'],
                    schema='inventory',
                    postgresql_where=sa.text("status = 'active' AND (reserved_until IS NULL OR reserved_until > now())"))

    # inventory.stock_metrics (new - aggregates the above)
    op.create_table(
        'stock_metrics',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('stock_id', sa.UUID(), nullable=False),
        sa.Column('available_quantity', sa.Integer(), nullable=False, comment='Total - Reserved'),
        sa.Column('reserved_quantity', sa.Integer(), nullable=False, default=0),
        sa.Column('total_cost', sa.Numeric(12, 2)),
        sa.Column('expected_profit', sa.Numeric(15, 2)),
        sa.Column('last_calculated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['stock_id'], ['inventory.stock.id'], ondelete='CASCADE'),
        schema='inventory'
    )
    op.create_index('idx_stock_metrics_stock', 'stock_metrics', ['stock_id'], schema='inventory', unique=True)

    # ================================================
    # 5. CREATE ANALYTICS MATERIALIZED VIEWS
    # ================================================
    print("Creating analytics materialized views...")

    # Note: These are simplified versions - you can enhance them later
    # They are created as regular tables that can be refreshed via queries/jobs

    # analytics.inventory_status_summary
    op.execute("""
        CREATE MATERIALIZED VIEW analytics.inventory_status_summary AS
        SELECT
            s.product_id,
            COUNT(DISTINCT s.id) as total_items,
            SUM(s.quantity) as total_quantity,
            SUM(CASE WHEN s.quantity > 0 THEN s.quantity ELSE 0 END) as available_quantity,
            COUNT(DISTINCT s.supplier_id) as supplier_count,
            AVG(sf.purchase_price) as avg_purchase_price,
            SUM(sf.gross_purchase_price) as total_investment,
            now() as refreshed_at
        FROM inventory.stock s
        LEFT JOIN inventory.stock_financial sf ON s.id = sf.stock_id
        GROUP BY s.product_id
    """)
    op.create_index('idx_inventory_status_product', 'inventory_status_summary',
                    ['product_id'], schema='analytics', unique=True)

    # analytics.sales_summary_daily
    op.execute("""
        CREATE MATERIALIZED VIEW analytics.sales_summary_daily AS
        SELECT
            DATE(o.created_at) as summary_date,
            l.platform_id,
            COUNT(o.id) as total_orders,
            SUM(o.amount) as total_revenue,
            AVG(o.amount) as avg_order_value,
            now() as refreshed_at
        FROM sales.order o
        JOIN sales.listing l ON o.listing_id = l.id
        GROUP BY DATE(o.created_at), l.platform_id
    """)
    op.create_index('idx_sales_summary_date_platform', 'sales_summary_daily',
                    ['summary_date', 'platform_id'], schema='analytics')

    # analytics.supplier_performance_summary
    op.execute("""
        CREATE MATERIALIZED VIEW analytics.supplier_performance_summary AS
        SELECT
            s.supplier_id,
            COUNT(DISTINCT s.id) as total_stock_items,
            SUM(s.quantity) as total_quantity,
            AVG(sf.purchase_price) as avg_purchase_price,
            SUM(sf.gross_purchase_price) as total_spent,
            AVG(sf.roi) as avg_roi,
            COUNT(DISTINCT sh.id) FILTER (WHERE sh.event_type = 'quality_issue' AND sh.resolved = false) as open_issues,
            now() as refreshed_at
        FROM inventory.stock s
        LEFT JOIN inventory.stock_financial sf ON s.id = sf.stock_id
        LEFT JOIN supplier.supplier_history sh ON s.supplier_id = sh.supplier_id
        GROUP BY s.supplier_id
    """)
    op.create_index('idx_supplier_performance_supplier', 'supplier_performance_summary',
                    ['supplier_id'], schema='analytics', unique=True)

    print("✅ Gibson features added successfully")


def downgrade():
    """Remove Gibson features."""

    print("Dropping analytics materialized views...")
    op.execute('DROP MATERIALIZED VIEW IF EXISTS analytics.supplier_performance_summary')
    op.execute('DROP MATERIALIZED VIEW IF EXISTS analytics.sales_summary_daily')
    op.execute('DROP MATERIALIZED VIEW IF EXISTS analytics.inventory_status_summary')

    print("Dropping inventory split tables...")
    op.drop_table('stock_metrics', schema='inventory')
    op.drop_table('stock_reservation', schema='inventory')
    op.drop_table('stock_lifecycle', schema='inventory')
    op.drop_table('stock_financial', schema='inventory')

    print("Dropping realtime schema...")
    op.drop_table('event_log', schema='realtime')
    op.execute('DROP SCHEMA IF EXISTS realtime CASCADE')

    print("Dropping operations schema...")
    op.drop_table('supplier_platform_integration', schema='operations')
    op.drop_table('order_fulfillment', schema='operations')
    op.drop_table('listing_history', schema='operations')
    op.execute('DROP SCHEMA IF EXISTS operations CASCADE')

    print("Dropping compliance schema...")
    op.drop_table('user_permissions', schema='compliance')
    op.drop_table('data_retention_policies', schema='compliance')
    op.drop_table('business_rules', schema='compliance')
    op.execute('DROP SCHEMA IF EXISTS compliance CASCADE')

    print("✅ Gibson features removed successfully")

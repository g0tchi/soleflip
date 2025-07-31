"""Initial schema migration

Revision ID: 001
Revises: 
Create Date: 2024-07-29 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Create initial database schema"""
    
    # Create extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS ltree")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto") 
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    
    # Create schemas
    op.execute("CREATE SCHEMA IF NOT EXISTS core")
    op.execute("CREATE SCHEMA IF NOT EXISTS products")
    op.execute("CREATE SCHEMA IF NOT EXISTS sales")
    op.execute("CREATE SCHEMA IF NOT EXISTS integration")
    op.execute("CREATE SCHEMA IF NOT EXISTS analytics")
    op.execute("CREATE SCHEMA IF NOT EXISTS logging")
    
    # Core schema tables
    op.create_table('brands',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('slug'),
        schema='core'
    )
    
    op.create_table('categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('path', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['parent_id'], ['core.categories.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
        schema='core'
    )
    
    op.create_table('sizes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('value', sa.String(length=20), nullable=False),
        sa.Column('standardized_value', sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column('region', sa.String(length=10), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['core.categories.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='core'
    )
    
    # Products schema tables
    op.create_table('products',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sku', sa.String(length=100), nullable=False),
        sa.Column('brand_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('retail_price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('release_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['brand_id'], ['core.brands.id'], ),
        sa.ForeignKeyConstraint(['category_id'], ['core.categories.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sku'),
        schema='products'
    )
    
    op.create_table('inventory',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('size_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('purchase_price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('purchase_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('supplier', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.products.id'], ),
        sa.ForeignKeyConstraint(['size_id'], ['core.sizes.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='products'
    )
    
    # Sales schema tables
    op.create_table('platforms',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('fee_percentage', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('slug'),
        schema='sales'
    )
    
    op.create_table('transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('inventory_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('platform_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('transaction_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('sale_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('platform_fee', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('shipping_cost', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('net_profit', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('external_id', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['inventory_id'], ['products.inventory.id'], ),
        sa.ForeignKeyConstraint(['platform_id'], ['sales.platforms.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='sales'
    )
    
    # Integration schema tables
    op.create_table('import_batches',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('source_file', sa.String(length=255), nullable=True),
        sa.Column('total_records', sa.Integer(), nullable=True),
        sa.Column('processed_records', sa.Integer(), nullable=True),
        sa.Column('error_records', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema='integration'
    )
    
    op.create_table('import_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('batch_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('raw_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('normalized_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('validation_errors', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('processed', sa.Boolean(), nullable=True),
        sa.Column('processing_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processing_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['batch_id'], ['integration.import_batches.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='integration'
    )
    
    # Logging schema tables
    op.create_table('system_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('level', sa.String(length=20), nullable=False),
        sa.Column('component', sa.String(length=50), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('source_table', sa.String(length=100), nullable=True),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema='logging'
    )
    
    # Create indexes
    op.create_index('idx_brands_slug', 'brands', ['slug'], unique=False, schema='core')
    op.create_index('idx_categories_slug', 'categories', ['slug'], unique=False, schema='core')
    op.create_index('idx_categories_parent', 'categories', ['parent_id'], unique=False, schema='core')
    op.create_index('idx_sizes_category', 'sizes', ['category_id'], unique=False, schema='core')
    
    op.create_index('idx_products_sku', 'products', ['sku'], unique=False, schema='products')
    op.create_index('idx_products_brand', 'products', ['brand_id'], unique=False, schema='products')
    op.create_index('idx_products_category', 'products', ['category_id'], unique=False, schema='products')
    
    op.create_index('idx_inventory_product', 'inventory', ['product_id'], unique=False, schema='products')
    op.create_index('idx_inventory_status', 'inventory', ['status'], unique=False, schema='products')
    
    op.create_index('idx_platforms_slug', 'platforms', ['slug'], unique=False, schema='sales')
    
    op.create_index('idx_transactions_inventory', 'transactions', ['inventory_id'], unique=False, schema='sales')
    op.create_index('idx_transactions_platform', 'transactions', ['platform_id'], unique=False, schema='sales')
    op.create_index('idx_transactions_date', 'transactions', ['transaction_date'], unique=False, schema='sales')
    
    op.create_index('idx_import_batches_source', 'import_batches', ['source_type'], unique=False, schema='integration')
    op.create_index('idx_import_batches_status', 'import_batches', ['status'], unique=False, schema='integration')
    
    op.create_index('idx_import_records_batch', 'import_records', ['batch_id'], unique=False, schema='integration')
    op.create_index('idx_import_records_processed', 'import_records', ['processed'], unique=False, schema='integration')
    
    op.create_index('idx_system_logs_level', 'system_logs', ['level'], unique=False, schema='logging')
    op.create_index('idx_system_logs_component', 'system_logs', ['component'], unique=False, schema='logging')
    op.create_index('idx_system_logs_created', 'system_logs', ['created_at'], unique=False, schema='logging')

def downgrade() -> None:
    """Drop all schema objects"""
    
    # Drop indexes first
    op.drop_index('idx_system_logs_created', table_name='system_logs', schema='logging')
    op.drop_index('idx_system_logs_component', table_name='system_logs', schema='logging')
    op.drop_index('idx_system_logs_level', table_name='system_logs', schema='logging')
    
    op.drop_index('idx_import_records_processed', table_name='import_records', schema='integration')
    op.drop_index('idx_import_records_batch', table_name='import_records', schema='integration')
    
    op.drop_index('idx_import_batches_status', table_name='import_batches', schema='integration')
    op.drop_index('idx_import_batches_source', table_name='import_batches', schema='integration')
    
    op.drop_index('idx_transactions_date', table_name='transactions', schema='sales')
    op.drop_index('idx_transactions_platform', table_name='transactions', schema='sales')
    op.drop_index('idx_transactions_inventory', table_name='transactions', schema='sales')
    
    op.drop_index('idx_platforms_slug', table_name='platforms', schema='sales')
    
    op.drop_index('idx_inventory_status', table_name='inventory', schema='products')
    op.drop_index('idx_inventory_product', table_name='inventory', schema='products')
    
    op.drop_index('idx_products_category', table_name='products', schema='products')
    op.drop_index('idx_products_brand', table_name='products', schema='products')
    op.drop_index('idx_products_sku', table_name='products', schema='products')
    
    op.drop_index('idx_sizes_category', table_name='sizes', schema='core')
    op.drop_index('idx_categories_parent', table_name='categories', schema='core')
    op.drop_index('idx_categories_slug', table_name='categories', schema='core')
    op.drop_index('idx_brands_slug', table_name='brands', schema='core')
    
    # Drop tables
    op.drop_table('system_logs', schema='logging')
    op.drop_table('import_records', schema='integration')
    op.drop_table('import_batches', schema='integration')
    op.drop_table('transactions', schema='sales')
    op.drop_table('platforms', schema='sales')
    op.drop_table('inventory', schema='products')
    op.drop_table('products', schema='products')
    op.drop_table('sizes', schema='core')
    op.drop_table('categories', schema='core')
    op.drop_table('brands', schema='core')
    
    # Drop schemas
    op.execute("DROP SCHEMA IF EXISTS logging CASCADE")
    op.execute("DROP SCHEMA IF EXISTS analytics CASCADE")
    op.execute("DROP SCHEMA IF EXISTS integration CASCADE")
    op.execute("DROP SCHEMA IF EXISTS sales CASCADE")
    op.execute("DROP SCHEMA IF EXISTS products CASCADE")
    op.execute("DROP SCHEMA IF EXISTS core CASCADE")
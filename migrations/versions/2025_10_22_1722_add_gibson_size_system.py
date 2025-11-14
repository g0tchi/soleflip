"""add_gibson_size_system

Revision ID: add_gibson_size_system
Revises: 7e0919aaa601
Create Date: 2025-10-22 17:22:00.000000

Implements Gibson's superior size system for sneaker sizes:
- core.size_master: Single row per size with ALL conversions (US/EU/UK/CM/KR/JP)
- core.size_conversion: Brand-specific size overrides
- catalog.product_variant: Product variants linked to sizes
- core.size_validation_log: Audit trail for StockX validation

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_gibson_size_system'
down_revision = '7e0919aaa601'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create core.size_master table (Gibson pattern)
    op.create_table(
        'size_master',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()'), comment='Primary key'),
        sa.Column('gender', sa.String(length=20), nullable=False, comment='Gender category: men, women, kids, unisex'),

        # All size standards in ONE row (Gibson pattern)
        sa.Column('us_size', sa.Numeric(precision=4, scale=1), nullable=False, comment='US size (e.g., 9.0, 9.5)'),
        sa.Column('eu_size', sa.Numeric(precision=4, scale=1), nullable=True, comment='EU size (e.g., 42.0, 42.5)'),
        sa.Column('uk_size', sa.Numeric(precision=4, scale=1), nullable=True, comment='UK size (e.g., 8.0, 8.5)'),
        sa.Column('cm_size', sa.Numeric(precision=4, scale=1), nullable=True, comment='CM size (e.g., 27.0)'),
        sa.Column('jp_size', sa.Numeric(precision=4, scale=1), nullable=True, comment='JP size (e.g., 27.0)'),
        sa.Column('kr_size', sa.Numeric(precision=5, scale=1), nullable=True, comment='KR size in mm (e.g., 260.0)'),

        sa.Column('category_id', sa.UUID(), nullable=True, comment='Optional category for category-specific sizing'),

        # Validation tracking
        sa.Column('validation_source', sa.String(length=20), nullable=True, comment='Last validation source: stockx, ebay, manual'),
        sa.Column('last_validated_at', sa.DateTime(timezone=True), nullable=True, comment='Last validation timestamp'),

        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'), comment='Creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'), comment='Last update timestamp'),

        sa.PrimaryKeyConstraint('id', name='size_master_pkey'),
        sa.ForeignKeyConstraint(['category_id'], ['catalog.category.id'], name='size_master_category_id_fkey'),
        sa.UniqueConstraint('us_size', 'gender', 'category_id', name='unique_size_gender_category'),
        schema='core'
    )

    # Indexes for size_master
    op.create_index('idx_size_master_lookup', 'size_master', ['us_size', 'gender'], unique=False, schema='core')
    op.create_index('idx_size_master_category', 'size_master', ['category_id'], unique=False, schema='core')
    op.create_index('idx_size_master_validation', 'size_master', ['last_validated_at'], unique=False, schema='core')

    # 2. Create core.size_conversion table (Brand-specific overrides)
    op.create_table(
        'size_conversion',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()'), comment='Primary key'),
        sa.Column('from_standard', sa.String(length=10), nullable=False, comment='Source size standard: US, EU, UK, CM, JP, KR'),
        sa.Column('to_standard', sa.String(length=10), nullable=False, comment='Target size standard: US, EU, UK, CM, JP, KR'),
        sa.Column('gender', sa.String(length=20), nullable=True, comment='Gender category: men, women, kids, unisex'),
        sa.Column('from_value', sa.Numeric(precision=5, scale=1), nullable=False, comment='Source size value'),
        sa.Column('to_value', sa.Numeric(precision=5, scale=1), nullable=False, comment='Target size value'),

        # Optional brand-specific override
        sa.Column('brand_id', sa.UUID(), nullable=True, comment='Brand-specific conversion override (NULL = default)'),
        sa.Column('category_id', sa.UUID(), nullable=True, comment='Category-specific conversion'),

        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'), comment='Creation timestamp'),

        sa.PrimaryKeyConstraint('id', name='size_conversion_pkey'),
        sa.ForeignKeyConstraint(['brand_id'], ['catalog.brand.id'], name='size_conversion_brand_id_fkey'),
        sa.ForeignKeyConstraint(['category_id'], ['catalog.category.id'], name='size_conversion_category_id_fkey'),
        sa.UniqueConstraint('from_standard', 'to_standard', 'gender', 'from_value', 'brand_id', 'category_id',
                          name='unique_conversion'),
        schema='core'
    )

    # Indexes for size_conversion
    op.create_index('idx_size_conversion_lookup', 'size_conversion',
                   ['from_standard', 'to_standard', 'gender', 'from_value'],
                   unique=False, schema='core')
    op.create_index('idx_size_conversion_brand', 'size_conversion', ['brand_id'], unique=False, schema='core')

    # 3. Create catalog.product_variant table
    op.create_table(
        'product_variant',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()'), comment='Primary key'),
        sa.Column('product_id', sa.UUID(), nullable=False, comment='Link to product'),
        sa.Column('size_master_id', sa.UUID(), nullable=True, comment='Link to size_master'),

        # StockX-specific identifiers
        sa.Column('stockx_variant_id', sa.String(length=255), nullable=True, comment='StockX variant UUID'),
        sa.Column('stockx_variant_name', sa.String(length=255), nullable=True, comment='StockX variant name'),

        # Variant attributes
        sa.Column('color', sa.String(length=100), nullable=True, comment='Variant color'),
        sa.Column('condition', sa.String(length=20), nullable=False, server_default='new', comment='Product condition: new, used, refurbished'),

        # StockX variant data (full JSON)
        sa.Column('variant_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Complete StockX variant JSON'),

        # StockX flags
        sa.Column('is_flex_eligible', sa.Boolean(), nullable=False, server_default='false', comment='StockX Flex eligible'),
        sa.Column('is_direct_eligible', sa.Boolean(), nullable=False, server_default='false', comment='StockX Direct eligible'),

        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'), comment='Creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'), comment='Last update timestamp'),

        sa.PrimaryKeyConstraint('id', name='product_variant_pkey'),
        sa.ForeignKeyConstraint(['product_id'], ['catalog.product.id'], name='product_variant_product_id_fkey', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['size_master_id'], ['core.size_master.id'], name='product_variant_size_master_id_fkey'),
        sa.UniqueConstraint('stockx_variant_id', name='product_variant_stockx_variant_id_key'),
        schema='catalog'
    )

    # Indexes for product_variant
    op.create_index('idx_variant_product', 'product_variant', ['product_id'], unique=False, schema='catalog')
    op.create_index('idx_variant_size', 'product_variant', ['size_master_id'], unique=False, schema='catalog')
    op.create_index('idx_variant_stockx', 'product_variant', ['stockx_variant_id'], unique=False, schema='catalog')
    op.create_index('idx_variant_condition', 'product_variant', ['condition'], unique=False, schema='catalog')

    # Create GIN index on variant_data JSONB column
    op.create_index('idx_variant_data', 'product_variant', ['variant_data'],
                   unique=False, schema='catalog', postgresql_using='gin')

    # 4. Create core.size_validation_log table (Audit trail)
    op.create_table(
        'size_validation_log',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()'), comment='Primary key'),
        sa.Column('size_master_id', sa.UUID(), nullable=False, comment='Link to size_master'),

        sa.Column('validation_source', sa.String(length=20), nullable=False, comment='Validation source: stockx, ebay, goat, manual'),
        sa.Column('validation_status', sa.String(length=20), nullable=False, comment='Status: valid, conflict, updated, created'),

        # StockX reference
        sa.Column('stockx_product_id', sa.String(length=255), nullable=True, comment='StockX product UUID'),
        sa.Column('stockx_variant_id', sa.String(length=255), nullable=True, comment='StockX variant UUID'),

        # Validation results
        sa.Column('conflicts_found', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Array of conflict objects'),
        sa.Column('action_taken', sa.String(length=50), nullable=False, comment='Action: created, updated, no_change'),

        # Data snapshots
        sa.Column('before_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Size data before update'),
        sa.Column('after_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='Size data after update'),

        sa.Column('validated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'), comment='Validation timestamp'),

        sa.PrimaryKeyConstraint('id', name='size_validation_log_pkey'),
        sa.ForeignKeyConstraint(['size_master_id'], ['core.size_master.id'], name='size_validation_log_size_master_id_fkey', ondelete='CASCADE'),
        schema='core'
    )

    # Indexes for size_validation_log
    op.create_index('idx_size_validation_master', 'size_validation_log', ['size_master_id'], unique=False, schema='core')
    op.create_index('idx_size_validation_source', 'size_validation_log', ['validation_source'], unique=False, schema='core')
    op.create_index('idx_size_validation_status', 'size_validation_log', ['validation_status'], unique=False, schema='core')
    op.create_index('idx_size_validation_time', 'size_validation_log', ['validated_at'], unique=False, schema='core')

    # Create GIN indexes on JSONB columns
    op.create_index('idx_size_validation_conflicts', 'size_validation_log', ['conflicts_found'],
                   unique=False, schema='core', postgresql_using='gin')


def downgrade():
    # Drop tables in reverse order (handle foreign keys)
    op.drop_table('size_validation_log', schema='core')
    op.drop_table('product_variant', schema='catalog')
    op.drop_table('size_conversion', schema='core')
    op.drop_table('size_master', schema='core')

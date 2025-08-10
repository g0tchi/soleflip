"""Add comprehensive suppliers system

Revision ID: 003_add_suppliers
Revises: 002_move_platforms_to_core  
Create Date: 2025-08-04 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_add_suppliers'
down_revision = '002_move_platforms_to_core'
branch_labels = None
depends_on = None

def upgrade():
    """Create comprehensive suppliers system with brand relationships"""
    
    # Create core.suppliers table
    op.create_table(
        'suppliers',
        
        # Primary Key
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        
        # Basic Information
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False, unique=True),
        sa.Column('display_name', sa.String(150), nullable=True),
        
        # Business Classification
        sa.Column('supplier_type', sa.String(50), nullable=False),
        sa.Column('business_size', sa.String(30), nullable=True),
        
        # Contact Information
        sa.Column('contact_person', sa.String(100), nullable=True),
        sa.Column('email', sa.String(100), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('website', sa.String(200), nullable=True),
        
        # Address Information
        sa.Column('address_line1', sa.String(200), nullable=True),
        sa.Column('address_line2', sa.String(200), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state_province', sa.String(100), nullable=True),
        sa.Column('postal_code', sa.String(20), nullable=True),
        sa.Column('country', sa.String(50), nullable=True, server_default='Germany'),
        
        # Business Details
        sa.Column('tax_id', sa.String(50), nullable=True),
        sa.Column('vat_number', sa.String(50), nullable=True),
        sa.Column('business_registration', sa.String(100), nullable=True),
        
        # Return Policy & Terms
        sa.Column('return_policy_days', sa.Integer, nullable=True),
        sa.Column('return_policy_text', sa.Text, nullable=True),
        sa.Column('return_conditions', sa.String(500), nullable=True),
        sa.Column('accepts_exchanges', sa.Boolean, nullable=True, server_default='true'),
        sa.Column('restocking_fee_percent', sa.Numeric(5, 2), nullable=True),
        
        # Payment & Trading Terms
        sa.Column('payment_terms', sa.String(100), nullable=True),
        sa.Column('credit_limit', sa.Numeric(12, 2), nullable=True),
        sa.Column('discount_percent', sa.Numeric(5, 2), nullable=True),
        sa.Column('minimum_order_amount', sa.Numeric(10, 2), nullable=True),
        
        # Performance & Status
        sa.Column('rating', sa.Numeric(3, 2), nullable=True),
        sa.Column('reliability_score', sa.Integer, nullable=True),
        sa.Column('quality_score', sa.Integer, nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('preferred', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('verified', sa.Boolean, nullable=False, server_default='false'),
        
        # Operational Information
        sa.Column('average_processing_days', sa.Integer, nullable=True),
        sa.Column('ships_internationally', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('accepts_returns_by_mail', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('provides_authenticity_guarantee', sa.Boolean, nullable=False, server_default='false'),
        
        # Integration & Technical
        sa.Column('has_api', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('api_endpoint', sa.String(200), nullable=True),
        sa.Column('api_key_encrypted', sa.Text, nullable=True),
        
        # Financial Tracking
        sa.Column('total_orders_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('total_order_value', sa.Numeric(12, 2), nullable=False, server_default='0.00'),
        sa.Column('average_order_value', sa.Numeric(10, 2), nullable=True),
        sa.Column('last_order_date', sa.DateTime(timezone=True), nullable=True),
        
        # Metadata
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('internal_notes', sa.Text, nullable=True),
        sa.Column('tags', postgresql.JSONB, nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        
        schema='core'
    )
    
    
    # Add constraints
    op.create_check_constraint(
        'chk_suppliers_rating',
        'suppliers',
        'rating >= 1.0 AND rating <= 5.0',
        schema='core'
    )
    
    op.create_check_constraint(
        'chk_suppliers_reliability_score', 
        'suppliers',
        'reliability_score >= 1 AND reliability_score <= 10',
        schema='core'
    )
    
    op.create_check_constraint(
        'chk_suppliers_quality_score',
        'suppliers', 
        'quality_score >= 1 AND quality_score <= 10',
        schema='core'
    )
    
    op.create_check_constraint(
        'chk_suppliers_return_days',
        'suppliers',
        'return_policy_days >= 0 AND return_policy_days <= 365',
        schema='core'
    )
    
    
    # Create indexes for suppliers
    op.create_index('idx_suppliers_name', 'suppliers', ['name'], unique=False, schema='core')
    op.create_index('idx_suppliers_slug', 'suppliers', ['slug'], unique=True, schema='core') 
    op.create_index('idx_suppliers_type', 'suppliers', ['supplier_type'], unique=False, schema='core')
    op.create_index('idx_suppliers_status', 'suppliers', ['status'], unique=False, schema='core')
    op.create_index('idx_suppliers_country', 'suppliers', ['country'], unique=False, schema='core')
    op.create_index('idx_suppliers_preferred', 'suppliers', ['preferred'], unique=False, schema='core')
    op.create_index('idx_suppliers_rating', 'suppliers', ['rating'], unique=False, schema='core')
    op.create_index('idx_suppliers_tags', 'suppliers', ['tags'], unique=False, schema='core', postgresql_using='gin')
    
    
    # Add supplier_id column to inventory table
    op.add_column(
        'inventory',
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('core.suppliers.id'), nullable=True),
        schema='products'
    )
    
    # Create index for inventory supplier_id
    op.create_index('idx_inventory_supplier', 'inventory', ['supplier_id'], unique=False, schema='products')


def downgrade():
    """Remove suppliers system"""
    
    # Drop indexes first
    op.drop_index('idx_inventory_supplier', table_name='inventory', schema='products')
    op.drop_index('idx_suppliers_tags', table_name='suppliers', schema='core')
    op.drop_index('idx_suppliers_rating', table_name='suppliers', schema='core')
    op.drop_index('idx_suppliers_preferred', table_name='suppliers', schema='core')
    op.drop_index('idx_suppliers_country', table_name='suppliers', schema='core')
    op.drop_index('idx_suppliers_status', table_name='suppliers', schema='core')
    op.drop_index('idx_suppliers_type', table_name='suppliers', schema='core')
    op.drop_index('idx_suppliers_slug', table_name='suppliers', schema='core')
    op.drop_index('idx_suppliers_name', table_name='suppliers', schema='core')
    
    # Drop column from inventory
    op.drop_column('inventory', 'supplier_id', schema='products')
    
    # Drop tables
    op.drop_table('suppliers', schema='core')
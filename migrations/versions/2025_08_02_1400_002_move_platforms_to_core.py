"""Move platforms table from sales schema to core schema

Revision ID: 002_move_platforms_to_core
Revises: 2024_07_29_1200_001_initial_schema
Create Date: 2025-08-02 14:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers
revision = '002_move_platforms_to_core'
down_revision = '2024_07_29_1200_001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Move platforms table from sales to core schema"""
    
    # 1. Create platforms table in core schema with enhanced columns
    op.create_table('platforms',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('fee_percentage', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('supports_fees', sa.Boolean(), nullable=True, default=True),
        sa.Column('active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('slug'),
        schema='core'
    )
    
    # 2. Copy existing data from sales.platforms to core.platforms (if exists)
    op.execute("""
        INSERT INTO core.platforms (id, name, slug, fee_percentage, active, created_at, updated_at)
        SELECT id, name, slug, fee_percentage, active, created_at, updated_at
        FROM sales.platforms
        WHERE EXISTS (SELECT 1 FROM information_schema.tables 
                     WHERE table_schema = 'sales' AND table_name = 'platforms')
    """)
    
    # 3. Update foreign key constraint in transactions table
    # First drop the old constraint if it exists
    op.execute("""
        ALTER TABLE sales.transactions 
        DROP CONSTRAINT IF EXISTS transactions_platform_id_fkey
    """)
    
    # Add new foreign key constraint pointing to core.platforms
    op.create_foreign_key(
        'fk_transactions_platform_id', 
        'transactions', 
        'platforms',
        ['platform_id'], 
        ['id'],
        source_schema='sales',
        referent_schema='core'
    )
    
    # 4. Drop old platforms table from sales schema (if exists)
    op.execute("""
        DROP TABLE IF EXISTS sales.platforms CASCADE
    """)
    
    # 5. Insert default platform data for common platforms
    op.execute("""
        INSERT INTO core.platforms (id, name, slug, fee_percentage, supports_fees, active)
        VALUES 
            (gen_random_uuid(), 'StockX', 'stockx', 9.5, true, true),
            (gen_random_uuid(), 'Alias', 'alias', 0.0, false, true),
            (gen_random_uuid(), 'GOAT', 'goat', 9.5, true, true),
            (gen_random_uuid(), 'eBay', 'ebay', 10.0, true, true),
            (gen_random_uuid(), 'Manual Sale', 'manual', 0.0, false, true)
        ON CONFLICT (slug) DO NOTHING
    """)


def downgrade() -> None:
    """Move platforms table back from core to sales schema"""
    
    # 1. Create platforms table in sales schema (restore old structure)
    op.create_table('platforms',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('fee_percentage', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('slug'),
        schema='sales'
    )
    
    # 2. Copy data back from core.platforms to sales.platforms
    op.execute("""
        INSERT INTO sales.platforms (id, name, slug, fee_percentage, active, created_at, updated_at)
        SELECT id, name, slug, fee_percentage, active, created_at, updated_at
        FROM core.platforms
    """)
    
    # 3. Update foreign key constraint back to sales schema
    op.drop_constraint('fk_transactions_platform_id', 'transactions', schema='sales')
    
    op.create_foreign_key(
        'transactions_platform_id_fkey',
        'transactions',
        'platforms', 
        ['platform_id'],
        ['id'],
        source_schema='sales',
        referent_schema='sales'
    )
    
    # 4. Drop platforms table from core schema
    op.drop_table('platforms', schema='core')
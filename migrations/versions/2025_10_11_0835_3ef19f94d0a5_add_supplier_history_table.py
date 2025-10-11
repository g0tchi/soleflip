"""add_supplier_history_table

Revision ID: 3ef19f94d0a5
Revises: 1eecf0cb7df3
Create Date: 2025-10-11 08:35:08.187114

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '3ef19f94d0a5'
down_revision = '1eecf0cb7df3'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Extend suppliers table with additional history-related fields
    op.add_column('suppliers', sa.Column('founded_year', sa.Integer(), nullable=True), schema='core')
    op.add_column('suppliers', sa.Column('founder_name', sa.String(length=200), nullable=True), schema='core')
    op.add_column('suppliers', sa.Column('instagram_handle', sa.String(length=100), nullable=True), schema='core')
    op.add_column('suppliers', sa.Column('instagram_url', sa.String(length=300), nullable=True), schema='core')
    op.add_column('suppliers', sa.Column('facebook_url', sa.String(length=300), nullable=True), schema='core')
    op.add_column('suppliers', sa.Column('twitter_handle', sa.String(length=100), nullable=True), schema='core')
    op.add_column('suppliers', sa.Column('logo_url', sa.String(length=500), nullable=True), schema='core')
    op.add_column('suppliers', sa.Column('supplier_story', sa.Text(), nullable=True), schema='core')
    op.add_column('suppliers', sa.Column('closure_date', sa.Date(), nullable=True), schema='core')
    op.add_column('suppliers', sa.Column('closure_reason', sa.Text(), nullable=True), schema='core')

    # 2. Create supplier_history table (similar to brand_history)
    op.create_table('supplier_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_date', sa.Date(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False,
                  comment='founded, opened_store, closed_store, expansion, rebranding, controversy, milestone, closure'),
        sa.Column('event_title', sa.String(length=200), nullable=False),
        sa.Column('event_description', sa.Text(), nullable=True),
        sa.Column('impact_level', sa.String(length=20), server_default='medium', nullable=True,
                  comment='low, medium, high, critical'),
        sa.Column('source_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['supplier_id'], ['core.suppliers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='core'
    )

    # 3. Create indexes for performance
    op.create_index('idx_supplier_history_supplier_date', 'supplier_history', ['supplier_id', 'event_date'], schema='core')
    op.create_index('idx_supplier_history_event_type', 'supplier_history', ['event_type'], schema='core')
    op.create_index('idx_suppliers_instagram', 'suppliers', ['instagram_handle'], schema='core')
    op.create_index('idx_suppliers_founded_year', 'suppliers', ['founded_year'], schema='core')


def downgrade():
    # Drop indexes
    op.drop_index('idx_suppliers_founded_year', table_name='suppliers', schema='core')
    op.drop_index('idx_suppliers_instagram', table_name='suppliers', schema='core')
    op.drop_index('idx_supplier_history_event_type', table_name='supplier_history', schema='core')
    op.drop_index('idx_supplier_history_supplier_date', table_name='supplier_history', schema='core')

    # Drop table
    op.drop_table('supplier_history', schema='core')

    # Remove columns from suppliers table
    op.drop_column('suppliers', 'closure_reason', schema='core')
    op.drop_column('suppliers', 'closure_date', schema='core')
    op.drop_column('suppliers', 'supplier_story', schema='core')
    op.drop_column('suppliers', 'logo_url', schema='core')
    op.drop_column('suppliers', 'twitter_handle', schema='core')
    op.drop_column('suppliers', 'facebook_url', schema='core')
    op.drop_column('suppliers', 'instagram_url', schema='core')
    op.drop_column('suppliers', 'instagram_handle', schema='core')
    op.drop_column('suppliers', 'founder_name', schema='core')
    op.drop_column('suppliers', 'founded_year', schema='core')

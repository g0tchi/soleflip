"""Create supplier accounts management

Revision ID: 2025_09_19_1300_create_supplier_accounts
Revises: 2025_09_19_1200_create_selling_schema
Create Date: 2025-09-19 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2025_09_19_1300_create_supplier_accounts'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # Create supplier_accounts table in core schema (where suppliers already exists)
    op.create_table('supplier_accounts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('supplier_id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(length=150), nullable=False),
        sa.Column('password_hash', sa.Text(), nullable=True),
        sa.Column('proxy_config', sa.Text(), nullable=True),
        sa.Column('first_name', sa.String(length=100), nullable=True),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('address_line_1', sa.String(length=200), nullable=True),
        sa.Column('address_line_2', sa.String(length=200), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('country_code', sa.String(length=5), nullable=True),
        sa.Column('zip_code', sa.String(length=20), nullable=True),
        sa.Column('state_code', sa.String(length=10), nullable=True),
        sa.Column('phone_number', sa.String(length=50), nullable=True),
        sa.Column('cc_number_encrypted', sa.Text(), nullable=True),
        sa.Column('expiry_month', sa.Integer(), nullable=True),
        sa.Column('expiry_year', sa.Integer(), nullable=True),
        sa.Column('cvv_encrypted', sa.Text(), nullable=True),
        sa.Column('browser_preference', sa.String(length=50), nullable=True),
        sa.Column('list_name', sa.String(length=100), nullable=True),
        sa.Column('account_status', sa.String(length=30), nullable=False, server_default='active'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('total_purchases', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_spent', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00'),
        sa.Column('success_rate', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0.00'),
        sa.Column('average_order_value', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.00'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['supplier_id'], ['core.suppliers.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('supplier_id', 'email', name='uq_supplier_account_email'),
        schema='core'
    )

    # Create purchase_history table for tracking account usage
    op.create_table('account_purchase_history',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('account_id', sa.UUID(), nullable=False),
        sa.Column('supplier_id', sa.UUID(), nullable=False),
        sa.Column('product_id', sa.UUID(), nullable=True),
        sa.Column('order_reference', sa.String(length=100), nullable=True),
        sa.Column('purchase_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('purchase_date', sa.DateTime(), nullable=False),
        sa.Column('purchase_status', sa.String(length=30), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['account_id'], ['core.supplier_accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['supplier_id'], ['core.suppliers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.products.id'], ondelete='SET NULL'),
        schema='core'
    )

    # Create indexes for performance
    op.create_index('idx_supplier_accounts_supplier_id', 'supplier_accounts', ['supplier_id'], schema='core')
    op.create_index('idx_supplier_accounts_email', 'supplier_accounts', ['email'], schema='core')
    op.create_index('idx_supplier_accounts_status', 'supplier_accounts', ['account_status'], schema='core')
    op.create_index('idx_supplier_accounts_last_used', 'supplier_accounts', ['last_used_at'], schema='core')

    op.create_index('idx_purchase_history_account_id', 'account_purchase_history', ['account_id'], schema='core')
    op.create_index('idx_purchase_history_supplier_id', 'account_purchase_history', ['supplier_id'], schema='core')
    op.create_index('idx_purchase_history_date', 'account_purchase_history', ['purchase_date'], schema='core')
    op.create_index('idx_purchase_history_status', 'account_purchase_history', ['purchase_status'], schema='core')


def downgrade():
    # Drop indexes
    op.drop_index('idx_purchase_history_status', table_name='account_purchase_history', schema='core')
    op.drop_index('idx_purchase_history_date', table_name='account_purchase_history', schema='core')
    op.drop_index('idx_purchase_history_supplier_id', table_name='account_purchase_history', schema='core')
    op.drop_index('idx_purchase_history_account_id', table_name='account_purchase_history', schema='core')

    op.drop_index('idx_supplier_accounts_last_used', table_name='supplier_accounts', schema='core')
    op.drop_index('idx_supplier_accounts_status', table_name='supplier_accounts', schema='core')
    op.drop_index('idx_supplier_accounts_email', table_name='supplier_accounts', schema='core')
    op.drop_index('idx_supplier_accounts_supplier_id', table_name='supplier_accounts', schema='core')

    # Drop tables
    op.drop_table('account_purchase_history', schema='core')
    op.drop_table('supplier_accounts', schema='core')
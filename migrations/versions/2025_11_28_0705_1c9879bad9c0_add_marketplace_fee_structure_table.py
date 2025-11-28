"""add_marketplace_fee_structure_table

Revision ID: 1c9879bad9c0
Revises: fa6f61561a34
Create Date: 2025-11-28 07:05:40.760739

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1c9879bad9c0'
down_revision = 'fa6f61561a34'
branch_labels = None
depends_on = None


def upgrade():
    # Create ENUM types for fee_type and fee_calculation_type
    fee_type_enum = sa.Enum(
        'transaction',
        'payment_processing',
        'shipping',
        'custom',
        name='marketplace_fee_type',
        schema='platform'
    )

    fee_calculation_type_enum = sa.Enum(
        'percentage',
        'fixed',
        'tiered',
        name='marketplace_fee_calculation_type',
        schema='platform'
    )

    # Create the enum types
    fee_type_enum.create(op.get_bind(), checkfirst=True)
    fee_calculation_type_enum.create(op.get_bind(), checkfirst=True)

    # Create the marketplace_fee_structure table
    op.create_table(
        'marketplace_fee_structure',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('marketplace_id', sa.UUID(), nullable=False),
        sa.Column('fee_type', fee_type_enum, nullable=False),
        sa.Column('fee_calculation_type', fee_calculation_type_enum, nullable=False),
        sa.Column('fee_value', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('effective_from', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('effective_until', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['marketplace_id'], ['platform.marketplace.id'], ondelete='CASCADE'),
        sa.CheckConstraint('fee_value >= 0', name='marketplace_fee_structure_fee_value_check'),
        schema='platform'
    )

    # Create indexes
    op.create_index(
        'idx_marketplace_fee_active',
        'marketplace_fee_structure',
        ['marketplace_id', 'active'],
        schema='platform'
    )

    op.create_index(
        'idx_marketplace_fee_effective',
        'marketplace_fee_structure',
        ['marketplace_id', 'effective_from', 'effective_until'],
        schema='platform'
    )

    # Create trigger for auto-updating updated_at timestamp
    op.execute("""
        CREATE OR REPLACE FUNCTION platform.update_marketplace_fee_structure_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER marketplace_fee_structure_updated_at_trigger
        BEFORE UPDATE ON platform.marketplace_fee_structure
        FOR EACH ROW
        EXECUTE FUNCTION platform.update_marketplace_fee_structure_updated_at();
    """)


def downgrade():
    # Drop trigger and function
    op.execute("""
        DROP TRIGGER IF EXISTS marketplace_fee_structure_updated_at_trigger ON platform.marketplace_fee_structure;
        DROP FUNCTION IF EXISTS platform.update_marketplace_fee_structure_updated_at();
    """)

    # Drop indexes
    op.drop_index('idx_marketplace_fee_effective', table_name='marketplace_fee_structure', schema='platform')
    op.drop_index('idx_marketplace_fee_active', table_name='marketplace_fee_structure', schema='platform')

    # Drop table
    op.drop_table('marketplace_fee_structure', schema='platform')

    # Drop enum types
    sa.Enum(name='marketplace_fee_calculation_type', schema='platform').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='marketplace_fee_type', schema='platform').drop(op.get_bind(), checkfirst=True)

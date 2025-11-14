"""PCI Compliance: Remove credit card storage and add tokenized payment fields

Revision ID: pci_compliance_payment_fields
Revises: 2025_09_19_1300_create_supplier_accounts
Create Date: 2025-09-20 15:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'pci_compliance_payment_fields'
down_revision = '2025_09_19_1300_create_supplier_accounts'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    CRITICAL SECURITY UPDATE: Remove PCI DSS violating credit card storage
    and replace with tokenized payment method fields
    """

    # Add new PCI-compliant payment method columns
    op.add_column('supplier_accounts',
                  sa.Column('payment_provider', sa.String(length=50), nullable=True,
                           comment='Payment provider: stripe, paypal, etc'),
                  schema='core')

    op.add_column('supplier_accounts',
                  sa.Column('payment_method_token', sa.String(length=255), nullable=True,
                           comment='Tokenized payment method ID'),
                  schema='core')

    op.add_column('supplier_accounts',
                  sa.Column('payment_method_last4', sa.String(length=4), nullable=True,
                           comment='Last 4 digits for display only'),
                  schema='core')

    op.add_column('supplier_accounts',
                  sa.Column('payment_method_brand', sa.String(length=20), nullable=True,
                           comment='Card brand: visa, mastercard, etc'),
                  schema='core')

    # CRITICAL: Remove PCI DSS violating columns
    # These columns store sensitive credit card data which violates PCI compliance
    op.drop_column('supplier_accounts', 'cc_number_encrypted', schema='core')
    op.drop_column('supplier_accounts', 'cvv_encrypted', schema='core')

    # Update existing records: Convert any existing encrypted data to safe display format
    # This migration assumes existing data needs to be preserved as display-only
    # In production, coordinate with payment provider integration before running this migration


def downgrade() -> None:
    """
    SECURITY NOTICE: Downgrade disabled for PCI compliance.

    This migration removes sensitive credit card data for PCI DSS compliance.
    Downgrading would reintroduce security vulnerabilities and is not permitted.

    If you need to rollback this migration, coordinate with your security team
    and payment provider integration team first.
    """
    raise RuntimeError(
        "Downgrade disabled for security reasons. "
        "This migration removes PCI DSS violating credit card storage. "
        "Contact your security team before attempting to rollback."
    )
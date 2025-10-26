"""add_brand_supplier_history

Revision ID: add_brand_supplier_history
Revises: move_size_tables_to_catalog
Create Date: 2025-10-25 19:00:00.000000

Adds timeline/history tracking for brands and suppliers:

## catalog.brand_history
Tracks brand milestones, closures, and collaborations:
- Brand founding, acquisitions, closures, rebranding
- Collaborations with other brands (Nike x Off-White, etc.)
- Immutable event log for brand timeline
- Supports year-only or full date precision

## supplier.supplier_history
Tracks supplier relationship milestones and issues:
- Partnership milestones, status changes
- Quality issues, closures, warnings
- Immutable event log for supplier timeline
- Supports year-only or full date precision

Design decisions:
- Separate tables for domain-specific event types
- Immutable events (no soft deletes - audit trail)
- Optional related_brand_id for collaborations
- Optimized indexes for timeline queries
- JSON metadata for flexible event details
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_brand_supplier_history'
down_revision = 'move_size_tables_to_catalog'
branch_labels = None
depends_on = None


def upgrade():
    """Add brand_history and supplier_history tables."""

    # ================================================
    # 1. Create catalog.brand_history
    # ================================================
    print("Creating catalog.brand_history table...")

    op.execute("""
        CREATE TYPE catalog.brand_event_type AS ENUM (
            'founded',
            'milestone',
            'acquisition',
            'closure',
            'rebranding',
            'collaboration',
            'expansion',
            'contraction',
            'other'
        )
    """)

    op.create_table(
        'brand_history',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()'),
                 comment='Primary key'),
        sa.Column('brand_id', sa.UUID(), nullable=False,
                 comment='Brand this event relates to'),
        sa.Column('event_type', postgresql.ENUM(name='brand_event_type', schema='catalog'), nullable=False,
                 comment='Type of event: founded, milestone, acquisition, closure, rebranding, collaboration'),
        sa.Column('event_date', sa.Date(), nullable=True,
                 comment='Full date of event (if known)'),
        sa.Column('event_year', sa.Integer(), nullable=True,
                 comment='Year of event (for year-only precision)'),
        sa.Column('title', sa.String(length=200), nullable=False,
                 comment='Event title (e.g., "Founded in Germany", "Acquired by Nike")'),
        sa.Column('description', sa.Text(), nullable=True,
                 comment='Detailed description of the event'),
        sa.Column('related_brand_id', sa.UUID(), nullable=True,
                 comment='Related brand for collaborations (e.g., Nike x Off-White -> Off-White ID)'),
        sa.Column('collaboration_start_date', sa.Date(), nullable=True,
                 comment='Collaboration start date (for collab events)'),
        sa.Column('collaboration_end_date', sa.Date(), nullable=True,
                 comment='Collaboration end date (if applicable)'),
        sa.Column('metadata', postgresql.JSONB(), nullable=True,
                 comment='Additional event metadata (flexible JSON)'),
        sa.Column('source', sa.String(length=100), nullable=True,
                 comment='Information source (e.g., "Wikipedia", "Official announcement")'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                 server_default=sa.text('now()'), comment='Record creation timestamp'),
        sa.Column('created_by', sa.String(length=100), nullable=True,
                 comment='User who created this event'),

        sa.PrimaryKeyConstraint('id', name='brand_history_pkey'),
        sa.ForeignKeyConstraint(['brand_id'], ['catalog.brand.id'],
                               name='brand_history_brand_id_fkey', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['related_brand_id'], ['catalog.brand.id'],
                               name='brand_history_related_brand_id_fkey', ondelete='SET NULL'),

        schema='catalog',
        comment='Brand timeline events: milestones, closures, collaborations'
    )

    # Indexes for brand_history
    op.create_index('idx_brand_history_brand_id', 'brand_history', ['brand_id'], schema='catalog')
    op.create_index('idx_brand_history_event_type', 'brand_history', ['event_type'], schema='catalog')
    op.create_index('idx_brand_history_event_date', 'brand_history', ['event_date'], schema='catalog')
    op.create_index('idx_brand_history_event_year', 'brand_history', ['event_year'], schema='catalog')
    op.create_index('idx_brand_history_collaboration', 'brand_history',
                    ['brand_id', 'related_brand_id'], schema='catalog',
                    postgresql_where=sa.text("event_type = 'collaboration'"))

    # ================================================
    # 2. Create supplier.supplier_history
    # ================================================
    print("Creating supplier.supplier_history table...")

    op.execute("""
        CREATE TYPE supplier.supplier_event_type AS ENUM (
            'partnership_started',
            'partnership_ended',
            'status_change',
            'milestone',
            'quality_issue',
            'closure',
            'warning',
            'preferred_status_gained',
            'preferred_status_lost',
            'contract_signed',
            'contract_renewed',
            'contract_terminated',
            'other'
        )
    """)

    op.create_table(
        'supplier_history',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()'),
                 comment='Primary key'),
        sa.Column('supplier_id', sa.UUID(), nullable=False,
                 comment='Supplier this event relates to'),
        sa.Column('event_type', postgresql.ENUM(name='supplier_event_type', schema='supplier'), nullable=False,
                 comment='Type of event: partnership_started, quality_issue, closure, etc.'),
        sa.Column('event_date', sa.Date(), nullable=True,
                 comment='Full date of event (if known)'),
        sa.Column('event_year', sa.Integer(), nullable=True,
                 comment='Year of event (for year-only precision)'),
        sa.Column('title', sa.String(length=200), nullable=False,
                 comment='Event title (e.g., "Partnership started", "Quality issues detected")'),
        sa.Column('description', sa.Text(), nullable=True,
                 comment='Detailed description of the event'),
        sa.Column('severity', sa.String(length=20), nullable=True,
                 comment='Severity level for issues: low, medium, high, critical'),
        sa.Column('resolved', sa.Boolean(), nullable=True, default=False,
                 comment='Whether issue has been resolved (for quality_issue/warning events)'),
        sa.Column('resolved_date', sa.Date(), nullable=True,
                 comment='Date when issue was resolved'),
        sa.Column('metadata', postgresql.JSONB(), nullable=True,
                 comment='Additional event metadata (flexible JSON)'),
        sa.Column('source', sa.String(length=100), nullable=True,
                 comment='Information source'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                 server_default=sa.text('now()'), comment='Record creation timestamp'),
        sa.Column('created_by', sa.String(length=100), nullable=True,
                 comment='User who created this event'),

        sa.PrimaryKeyConstraint('id', name='supplier_history_pkey'),
        sa.ForeignKeyConstraint(['supplier_id'], ['supplier.profile.id'],
                               name='supplier_history_supplier_id_fkey', ondelete='CASCADE'),

        schema='supplier',
        comment='Supplier timeline events: milestones, issues, status changes'
    )

    # Indexes for supplier_history
    op.create_index('idx_supplier_history_supplier_id', 'supplier_history', ['supplier_id'], schema='supplier')
    op.create_index('idx_supplier_history_event_type', 'supplier_history', ['event_type'], schema='supplier')
    op.create_index('idx_supplier_history_event_date', 'supplier_history', ['event_date'], schema='supplier')
    op.create_index('idx_supplier_history_event_year', 'supplier_history', ['event_year'], schema='supplier')
    op.create_index('idx_supplier_history_unresolved_issues', 'supplier_history',
                    ['supplier_id', 'resolved'], schema='supplier',
                    postgresql_where=sa.text("event_type IN ('quality_issue', 'warning') AND resolved = false"))

    print("✅ Brand and supplier history tables created successfully")


def downgrade():
    """Remove brand_history and supplier_history tables."""

    print("Dropping supplier.supplier_history table...")
    op.drop_index('idx_supplier_history_unresolved_issues', table_name='supplier_history', schema='supplier')
    op.drop_index('idx_supplier_history_event_year', table_name='supplier_history', schema='supplier')
    op.drop_index('idx_supplier_history_event_date', table_name='supplier_history', schema='supplier')
    op.drop_index('idx_supplier_history_event_type', table_name='supplier_history', schema='supplier')
    op.drop_index('idx_supplier_history_supplier_id', table_name='supplier_history', schema='supplier')
    op.drop_table('supplier_history', schema='supplier')
    op.execute('DROP TYPE supplier.supplier_event_type')

    print("Dropping catalog.brand_history table...")
    op.drop_index('idx_brand_history_collaboration', table_name='brand_history', schema='catalog')
    op.drop_index('idx_brand_history_event_year', table_name='brand_history', schema='catalog')
    op.drop_index('idx_brand_history_event_date', table_name='brand_history', schema='catalog')
    op.drop_index('idx_brand_history_event_type', table_name='brand_history', schema='catalog')
    op.drop_index('idx_brand_history_brand_id', table_name='brand_history', schema='catalog')
    op.drop_table('brand_history', schema='catalog')
    op.execute('DROP TYPE catalog.brand_event_type')

    print("✅ Brand and supplier history tables removed successfully")

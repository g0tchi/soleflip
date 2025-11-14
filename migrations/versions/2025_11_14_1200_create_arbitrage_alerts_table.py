"""create_arbitrage_alerts_table

Revision ID: a9f8c7b6d5e4
Revises: 3d6bdd7225fa
Create Date: 2025-11-14 12:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a9f8c7b6d5e4'
down_revision = '3d6bdd7225fa'
branch_labels = None
depends_on = None


def upgrade():
    # Create arbitrage schema if it doesn't exist
    op.execute("CREATE SCHEMA IF NOT EXISTS arbitrage")

    # Create RiskLevelFilter enum type
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE arbitrage.risk_level_filter AS ENUM ('LOW', 'MEDIUM', 'HIGH');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create arbitrage_alerts table
    op.create_table(
        'arbitrage_alerts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('alert_name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),

        # Filter criteria
        sa.Column('min_profit_margin', sa.Numeric(precision=5, scale=2),
                  nullable=False, server_default='10.0',
                  comment='Minimum profit margin %'),
        sa.Column('min_gross_profit', sa.Numeric(precision=8, scale=2),
                  nullable=False, server_default='20.0',
                  comment='Minimum gross profit €'),
        sa.Column('max_buy_price', sa.Numeric(precision=8, scale=2),
                  nullable=True,
                  comment='Maximum buy price €'),
        sa.Column('min_feasibility_score', sa.Integer(),
                  nullable=False, server_default='60',
                  comment='Minimum feasibility score (0-100)'),
        sa.Column('max_risk_level',
                  postgresql.ENUM('LOW', 'MEDIUM', 'HIGH',
                                  name='risk_level_filter',
                                  schema='arbitrage',
                                  create_type=False),
                  nullable=False, server_default='MEDIUM',
                  comment='Maximum acceptable risk level'),
        sa.Column('source_filter', sa.String(length=50), nullable=True,
                  comment='Filter by source (awin, webgains, etc.)'),
        sa.Column('additional_filters', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=True,
                  comment='Additional filters (brand, category, supplier, etc.)'),

        # Notification settings
        sa.Column('n8n_webhook_url', sa.String(length=500), nullable=False,
                  comment='n8n webhook endpoint for notifications'),
        sa.Column('notification_config', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=True,
                  comment='Notification preferences: {discord: true, email: false, telegram: false}'),
        sa.Column('include_demand_breakdown', sa.Boolean(),
                  nullable=False, server_default='true'),
        sa.Column('include_risk_details', sa.Boolean(),
                  nullable=False, server_default='true'),
        sa.Column('max_opportunities_per_alert', sa.Integer(),
                  nullable=False, server_default='10'),

        # Schedule settings
        sa.Column('alert_frequency_minutes', sa.Integer(),
                  nullable=False, server_default='15',
                  comment='Minutes between alert checks'),
        sa.Column('active_hours_start', sa.Time(), nullable=True,
                  comment='Start of active hours (e.g., 09:00)'),
        sa.Column('active_hours_end', sa.Time(), nullable=True,
                  comment='End of active hours (e.g., 22:00)'),
        sa.Column('active_days', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=True,
                  comment="Active days: ['monday', 'tuesday', ...] or null for all"),
        sa.Column('timezone', sa.String(length=50),
                  nullable=False, server_default='Europe/Berlin'),

        # Alert tracking
        sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_scanned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_alerts_sent', sa.Integer(),
                  nullable=False, server_default='0'),
        sa.Column('total_opportunities_sent', sa.Integer(),
                  nullable=False, server_default='0',
                  comment='Total opportunities sent across all alerts'),
        sa.Column('last_error', sa.String(length=1000), nullable=True),
        sa.Column('last_error_at', sa.DateTime(timezone=True), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),

        # Constraints
        sa.ForeignKeyConstraint(['user_id'], ['auth.users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('min_profit_margin >= 0 AND min_profit_margin <= 100',
                           name='check_profit_margin_range'),
        sa.CheckConstraint('min_feasibility_score >= 0 AND min_feasibility_score <= 100',
                           name='check_feasibility_score_range'),
        sa.CheckConstraint('alert_frequency_minutes > 0',
                           name='check_alert_frequency_positive'),
        sa.CheckConstraint('max_opportunities_per_alert > 0',
                           name='check_max_opportunities_positive'),

        schema='arbitrage'
    )

    # Create indexes for better query performance
    op.create_index(
        'idx_arbitrage_alerts_user_id',
        'arbitrage_alerts',
        ['user_id'],
        unique=False,
        schema='arbitrage'
    )
    op.create_index(
        'idx_arbitrage_alerts_active',
        'arbitrage_alerts',
        ['active'],
        unique=False,
        schema='arbitrage'
    )
    op.create_index(
        'idx_arbitrage_alerts_last_scanned',
        'arbitrage_alerts',
        ['last_scanned_at'],
        unique=False,
        schema='arbitrage',
        postgresql_where=sa.text('active = true')
    )
    op.create_index(
        'idx_arbitrage_alerts_next_scan',
        'arbitrage_alerts',
        ['last_scanned_at', 'alert_frequency_minutes'],
        unique=False,
        schema='arbitrage',
        postgresql_where=sa.text('active = true')
    )

    # Create trigger for updated_at
    op.execute("""
        CREATE OR REPLACE FUNCTION arbitrage.update_arbitrage_alerts_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trigger_update_arbitrage_alerts_updated_at
        BEFORE UPDATE ON arbitrage.arbitrage_alerts
        FOR EACH ROW
        EXECUTE FUNCTION arbitrage.update_arbitrage_alerts_updated_at();
    """)


def downgrade():
    # Drop trigger and function
    op.execute("""
        DROP TRIGGER IF EXISTS trigger_update_arbitrage_alerts_updated_at
        ON arbitrage.arbitrage_alerts;

        DROP FUNCTION IF EXISTS arbitrage.update_arbitrage_alerts_updated_at();
    """)

    # Drop indexes
    op.drop_index('idx_arbitrage_alerts_next_scan',
                  table_name='arbitrage_alerts', schema='arbitrage')
    op.drop_index('idx_arbitrage_alerts_last_scanned',
                  table_name='arbitrage_alerts', schema='arbitrage')
    op.drop_index('idx_arbitrage_alerts_active',
                  table_name='arbitrage_alerts', schema='arbitrage')
    op.drop_index('idx_arbitrage_alerts_user_id',
                  table_name='arbitrage_alerts', schema='arbitrage')

    # Drop table
    op.drop_table('arbitrage_alerts', schema='arbitrage')

    # Drop enum type
    op.execute("DROP TYPE IF EXISTS arbitrage.risk_level_filter")

    # Note: We don't drop the schema in case other tables are added to it
    # op.execute("DROP SCHEMA IF EXISTS arbitrage CASCADE")

"""Create pricing and analytics schemas for forecasting system

Revision ID: 9233d7fa1f2a
Revises: 1d7ca9ca7284
Create Date: 2025-08-27 13:53:04.789915

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '9233d7fa1f2a'
down_revision = '1d7ca9ca7284'
branch_labels = None
depends_on = None


def upgrade():
    # Create pricing schema
    op.execute("CREATE SCHEMA IF NOT EXISTS pricing")
    op.execute("CREATE SCHEMA IF NOT EXISTS analytics")
    
    # =====================================================
    # PRICING SCHEMA TABLES
    # =====================================================
    
    # Price Rules - Core pricing logic configurations
    op.create_table('price_rules',
        sa.Column('id', sa.UUID(), default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('rule_type', sa.String(50), nullable=False),  # 'cost_plus', 'market_based', 'competitive'
        sa.Column('priority', sa.Integer(), nullable=False, default=100),
        sa.Column('active', sa.Boolean(), nullable=False, default=True),
        sa.Column('brand_id', sa.UUID(), nullable=True),
        sa.Column('category_id', sa.UUID(), nullable=True),
        sa.Column('platform_id', sa.UUID(), nullable=True),
        sa.Column('base_markup_percent', sa.Numeric(5, 2), nullable=True),
        sa.Column('minimum_margin_percent', sa.Numeric(5, 2), nullable=True),
        sa.Column('maximum_discount_percent', sa.Numeric(5, 2), nullable=True),
        sa.Column('condition_multipliers', sa.JSON(), nullable=True),
        sa.Column('seasonal_adjustments', sa.JSON(), nullable=True),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=False),
        sa.Column('effective_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['brand_id'], ['core.brands.id'], ),
        sa.ForeignKeyConstraint(['category_id'], ['core.categories.id'], ),
        sa.ForeignKeyConstraint(['platform_id'], ['core.platforms.id'], ),
        schema='pricing'
    )
    
    # Brand Multipliers - Brand-specific pricing adjustments
    op.create_table('brand_multipliers',
        sa.Column('id', sa.UUID(), default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('brand_id', sa.UUID(), nullable=False),
        sa.Column('multiplier_type', sa.String(50), nullable=False),  # 'premium', 'discount', 'seasonal'
        sa.Column('multiplier_value', sa.Numeric(4, 3), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, default=True),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_until', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['brand_id'], ['core.brands.id'], ),
        schema='pricing'
    )
    
    # Price History - Historical price tracking
    op.create_table('price_history',
        sa.Column('id', sa.UUID(), default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('product_id', sa.UUID(), nullable=False),
        sa.Column('inventory_item_id', sa.UUID(), nullable=True),
        sa.Column('platform_id', sa.UUID(), nullable=True),
        sa.Column('price_date', sa.Date(), nullable=False),
        sa.Column('price_type', sa.String(30), nullable=False),  # 'listing', 'sale', 'market', 'competitor'
        sa.Column('price_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, default='EUR'),
        sa.Column('source', sa.String(50), nullable=False),  # 'internal', 'stockx', 'goat', 'manual'
        sa.Column('confidence_score', sa.Numeric(3, 2), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['product_id'], ['products.products.id'], ),
        sa.ForeignKeyConstraint(['inventory_item_id'], ['inventory.inventory_items.id'], ),
        sa.ForeignKeyConstraint(['platform_id'], ['core.platforms.id'], ),
        schema='pricing'
    )
    
    # Market Prices - External market price data
    op.create_table('market_prices',
        sa.Column('id', sa.UUID(), default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('product_id', sa.UUID(), nullable=False),
        sa.Column('platform_name', sa.String(50), nullable=False),
        sa.Column('size_value', sa.String(20), nullable=True),
        sa.Column('condition', sa.String(20), nullable=False),
        sa.Column('price_date', sa.Date(), nullable=False),
        sa.Column('lowest_ask', sa.Numeric(10, 2), nullable=True),
        sa.Column('highest_bid', sa.Numeric(10, 2), nullable=True),
        sa.Column('last_sale', sa.Numeric(10, 2), nullable=True),
        sa.Column('average_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('sales_volume', sa.Integer(), nullable=True),
        sa.Column('premium_percentage', sa.Numeric(5, 2), nullable=True),
        sa.Column('data_quality_score', sa.Numeric(3, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['product_id'], ['products.products.id'], ),
        schema='pricing'
    )
    
    # =====================================================
    # ANALYTICS SCHEMA TABLES  
    # =====================================================
    
    # Sales Forecasts - Predictive sales data
    op.create_table('sales_forecasts',
        sa.Column('id', sa.UUID(), default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('forecast_run_id', sa.UUID(), nullable=False),
        sa.Column('product_id', sa.UUID(), nullable=True),
        sa.Column('brand_id', sa.UUID(), nullable=True),
        sa.Column('category_id', sa.UUID(), nullable=True),
        sa.Column('platform_id', sa.UUID(), nullable=True),
        sa.Column('forecast_level', sa.String(20), nullable=False),  # 'product', 'brand', 'category', 'platform'
        sa.Column('forecast_date', sa.Date(), nullable=False),
        sa.Column('forecast_horizon', sa.String(20), nullable=False),  # 'daily', 'weekly', 'monthly'
        sa.Column('forecasted_units', sa.Numeric(10, 2), nullable=False),
        sa.Column('forecasted_revenue', sa.Numeric(12, 2), nullable=False),
        sa.Column('confidence_lower', sa.Numeric(10, 2), nullable=True),
        sa.Column('confidence_upper', sa.Numeric(10, 2), nullable=True),
        sa.Column('model_name', sa.String(50), nullable=False),
        sa.Column('model_version', sa.String(20), nullable=False),
        sa.Column('feature_importance', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['product_id'], ['products.products.id'], ),
        sa.ForeignKeyConstraint(['brand_id'], ['core.brands.id'], ),
        sa.ForeignKeyConstraint(['category_id'], ['core.categories.id'], ),
        sa.ForeignKeyConstraint(['platform_id'], ['core.platforms.id'], ),
        schema='analytics'
    )
    
    # Forecast Accuracy - Track prediction performance
    op.create_table('forecast_accuracy',
        sa.Column('id', sa.UUID(), default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('forecast_run_id', sa.UUID(), nullable=False),
        sa.Column('model_name', sa.String(50), nullable=False),
        sa.Column('forecast_level', sa.String(20), nullable=False),
        sa.Column('forecast_horizon', sa.String(20), nullable=False),
        sa.Column('accuracy_date', sa.Date(), nullable=False),
        sa.Column('mape_score', sa.Numeric(5, 2), nullable=True),  # Mean Absolute Percentage Error
        sa.Column('rmse_score', sa.Numeric(10, 2), nullable=True),  # Root Mean Square Error
        sa.Column('mae_score', sa.Numeric(10, 2), nullable=True),   # Mean Absolute Error
        sa.Column('r2_score', sa.Numeric(5, 4), nullable=True),    # R-squared
        sa.Column('bias_score', sa.Numeric(8, 2), nullable=True),
        sa.Column('records_evaluated', sa.Integer(), nullable=False),
        sa.Column('evaluation_period_days', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema='analytics'
    )
    
    # Demand Patterns - Historical demand analysis
    op.create_table('demand_patterns',
        sa.Column('id', sa.UUID(), default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('product_id', sa.UUID(), nullable=True),
        sa.Column('brand_id', sa.UUID(), nullable=True),
        sa.Column('category_id', sa.UUID(), nullable=True),
        sa.Column('analysis_level', sa.String(20), nullable=False),
        sa.Column('pattern_date', sa.Date(), nullable=False),
        sa.Column('period_type', sa.String(20), nullable=False),  # 'daily', 'weekly', 'monthly', 'seasonal'
        sa.Column('demand_score', sa.Numeric(8, 4), nullable=False),
        sa.Column('velocity_rank', sa.Integer(), nullable=True),
        sa.Column('seasonality_factor', sa.Numeric(4, 3), nullable=True),
        sa.Column('trend_direction', sa.String(20), nullable=True),  # 'increasing', 'decreasing', 'stable'
        sa.Column('volatility_score', sa.Numeric(5, 4), nullable=True),
        sa.Column('pattern_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['product_id'], ['products.products.id'], ),
        sa.ForeignKeyConstraint(['brand_id'], ['core.brands.id'], ),
        sa.ForeignKeyConstraint(['category_id'], ['core.categories.id'], ),
        schema='analytics'
    )
    
    # Pricing KPIs - Key performance indicators
    op.create_table('pricing_kpis',
        sa.Column('id', sa.UUID(), default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('kpi_date', sa.Date(), nullable=False),
        sa.Column('product_id', sa.UUID(), nullable=True),
        sa.Column('brand_id', sa.UUID(), nullable=True),
        sa.Column('category_id', sa.UUID(), nullable=True),
        sa.Column('platform_id', sa.UUID(), nullable=True),
        sa.Column('aggregation_level', sa.String(20), nullable=False),
        sa.Column('average_margin_percent', sa.Numeric(5, 2), nullable=True),
        sa.Column('average_markup_percent', sa.Numeric(5, 2), nullable=True),
        sa.Column('price_realization_percent', sa.Numeric(5, 2), nullable=True),
        sa.Column('competitive_index', sa.Numeric(5, 2), nullable=True),
        sa.Column('conversion_rate_percent', sa.Numeric(5, 2), nullable=True),
        sa.Column('revenue_impact_eur', sa.Numeric(12, 2), nullable=True),
        sa.Column('units_sold', sa.Integer(), nullable=True),
        sa.Column('average_selling_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('price_elasticity', sa.Numeric(6, 4), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['product_id'], ['products.products.id'], ),
        sa.ForeignKeyConstraint(['brand_id'], ['core.brands.id'], ),
        sa.ForeignKeyConstraint(['category_id'], ['core.categories.id'], ),
        sa.ForeignKeyConstraint(['platform_id'], ['core.platforms.id'], ),
        schema='analytics'
    )
    
    # =====================================================
    # INDEXES FOR PERFORMANCE
    # =====================================================
    
    # Pricing schema indexes
    op.create_index('idx_price_rules_brand_active', 'price_rules', ['brand_id', 'active'], schema='pricing')
    op.create_index('idx_price_rules_effective_dates', 'price_rules', ['effective_from', 'effective_until'], schema='pricing')
    op.create_index('idx_price_history_product_date', 'price_history', ['product_id', 'price_date'], schema='pricing')
    op.create_index('idx_price_history_date_type', 'price_history', ['price_date', 'price_type'], schema='pricing')
    op.create_index('idx_market_prices_product_platform', 'market_prices', ['product_id', 'platform_name'], schema='pricing')
    op.create_index('idx_market_prices_date', 'market_prices', ['price_date'], schema='pricing')
    
    # Analytics schema indexes  
    op.create_index('idx_sales_forecasts_run_date', 'sales_forecasts', ['forecast_run_id', 'forecast_date'], schema='analytics')
    op.create_index('idx_sales_forecasts_product_date', 'sales_forecasts', ['product_id', 'forecast_date'], schema='analytics')
    op.create_index('idx_sales_forecasts_brand_level', 'sales_forecasts', ['brand_id', 'forecast_level'], schema='analytics')
    op.create_index('idx_forecast_accuracy_model_date', 'forecast_accuracy', ['model_name', 'accuracy_date'], schema='analytics')
    op.create_index('idx_demand_patterns_product_date', 'demand_patterns', ['product_id', 'pattern_date'], schema='analytics')
    op.create_index('idx_demand_patterns_brand_period', 'demand_patterns', ['brand_id', 'period_type'], schema='analytics')
    op.create_index('idx_pricing_kpis_date_level', 'pricing_kpis', ['kpi_date', 'aggregation_level'], schema='analytics')
    op.create_index('idx_pricing_kpis_brand_date', 'pricing_kpis', ['brand_id', 'kpi_date'], schema='analytics')


def downgrade():
    # Drop indexes first
    op.drop_index('idx_pricing_kpis_brand_date', table_name='pricing_kpis', schema='analytics')
    op.drop_index('idx_pricing_kpis_date_level', table_name='pricing_kpis', schema='analytics')
    op.drop_index('idx_demand_patterns_brand_period', table_name='demand_patterns', schema='analytics')
    op.drop_index('idx_demand_patterns_product_date', table_name='demand_patterns', schema='analytics')
    op.drop_index('idx_forecast_accuracy_model_date', table_name='forecast_accuracy', schema='analytics')
    op.drop_index('idx_sales_forecasts_brand_level', table_name='sales_forecasts', schema='analytics')
    op.drop_index('idx_sales_forecasts_product_date', table_name='sales_forecasts', schema='analytics')
    op.drop_index('idx_sales_forecasts_run_date', table_name='sales_forecasts', schema='analytics')
    op.drop_index('idx_market_prices_date', table_name='market_prices', schema='pricing')
    op.drop_index('idx_market_prices_product_platform', table_name='market_prices', schema='pricing')
    op.drop_index('idx_price_history_date_type', table_name='price_history', schema='pricing')
    op.drop_index('idx_price_history_product_date', table_name='price_history', schema='pricing')
    op.drop_index('idx_price_rules_effective_dates', table_name='price_rules', schema='pricing')
    op.drop_index('idx_price_rules_brand_active', table_name='price_rules', schema='pricing')
    
    # Drop tables
    op.drop_table('pricing_kpis', schema='analytics')
    op.drop_table('demand_patterns', schema='analytics')
    op.drop_table('forecast_accuracy', schema='analytics')
    op.drop_table('sales_forecasts', schema='analytics')
    op.drop_table('market_prices', schema='pricing')
    op.drop_table('price_history', schema='pricing')
    op.drop_table('brand_multipliers', schema='pricing')
    op.drop_table('price_rules', schema='pricing')
    
    # Drop schemas
    op.execute("DROP SCHEMA IF EXISTS analytics CASCADE")
    op.execute("DROP SCHEMA IF EXISTS pricing CASCADE")

-- ============================================================================
-- Soleflip Database Schema - PostgreSQL Version (PHASE 2)
-- Converted from Gibson AI MySQL Schema
-- Remaining: 31 Tables (analytics, financial, logging, pricing, realtime, supplier, transaction)
-- ============================================================================

-- Note: Run schema-tables.sql (Phase 1) first!
-- This script assumes Phase 1 tables and ENUMs already exist

-- ============================================================================
-- ADDITIONAL ENUM TYPES FOR PHASE 2
-- ============================================================================

CREATE TYPE IF NOT EXISTS listing_status_type AS ENUM ('active', 'cancelled', 'expired', 'sold');
CREATE TYPE IF NOT EXISTS order_status_type AS ENUM ('cancelled', 'completed', 'pending', 'shipped');
CREATE TYPE IF NOT EXISTS fulfillment_status_type AS ENUM ('cancelled', 'completed', 'pending', 'processing', 'shipped');
CREATE TYPE IF NOT EXISTS integration_source_type AS ENUM ('api', 'csv', 'manual');

-- ============================================================================
-- ANALYTICS MODULE (9 tables - Materialized Views)
-- ============================================================================

-- Note: Gibson has these as tables, but they're actually materialized views in production
-- We'll create them as regular tables for now, can be converted to MVs later

CREATE TABLE IF NOT EXISTS analytics.current_inventory_status_mv (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    product_id BIGINT,
    total_units INT,
    available_units INT,
    reserved_units INT,
    sold_units INT,
    avg_days_in_stock DECIMAL(10, 2),
    last_updated TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
COMMENT ON TABLE analytics.current_inventory_status_mv IS 'Current inventory status analytics';

CREATE TABLE IF NOT EXISTS analytics.daily_sales_summary_mv (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    sale_date DATE NOT NULL,
    total_sales DECIMAL(12, 2),
    total_units_sold INT,
    avg_sale_price DECIMAL(10, 2),
    platform_id BIGINT,
    last_updated TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
COMMENT ON TABLE analytics.daily_sales_summary_mv IS 'Daily sales summary analytics';

CREATE TABLE IF NOT EXISTS analytics.marketplace_data (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    product_id BIGINT NOT NULL,
    platform_id BIGINT NOT NULL,
    market_price DECIMAL(10, 2),
    volume_30d INT,
    last_sale_price DECIMAL(10, 2),
    last_sale_date DATE,
    trend_indicator VARCHAR(20),
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_analytics_marketplace_data_product ON analytics.marketplace_data(product_id);
CREATE INDEX idx_analytics_marketplace_data_platform ON analytics.marketplace_data(platform_id);
COMMENT ON TABLE analytics.marketplace_data IS 'Marketplace pricing and volume data';

CREATE TABLE IF NOT EXISTS analytics.marketplace_summary (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    platform_id BIGINT NOT NULL,
    total_listings INT,
    avg_price DECIMAL(10, 2),
    median_price DECIMAL(10, 2),
    volume_24h INT,
    summary_date DATE NOT NULL,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_analytics_marketplace_summary_platform ON analytics.marketplace_summary(platform_id);
COMMENT ON TABLE analytics.marketplace_summary IS 'Platform-level marketplace summary';

CREATE TABLE IF NOT EXISTS analytics.monthly_pl_summary_mv (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    month_year VARCHAR(7) NOT NULL,
    total_revenue DECIMAL(12, 2),
    total_cogs DECIMAL(12, 2),
    total_fees DECIMAL(12, 2),
    gross_profit DECIMAL(12, 2),
    net_profit DECIMAL(12, 2),
    profit_margin DECIMAL(5, 2),
    last_updated TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
COMMENT ON TABLE analytics.monthly_pl_summary_mv IS 'Monthly profit & loss summary';

CREATE TABLE IF NOT EXISTS analytics.platform_performance_comparison_mv (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    platform_id BIGINT,
    total_sales DECIMAL(12, 2),
    total_units_sold INT,
    avg_sale_price DECIMAL(10, 2),
    total_fees DECIMAL(12, 2),
    avg_days_to_sell DECIMAL(10, 2),
    last_updated TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
COMMENT ON TABLE analytics.platform_performance_comparison_mv IS 'Platform performance comparison';

CREATE TABLE IF NOT EXISTS analytics.product_profitability_analysis_mv (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    product_id BIGINT,
    total_revenue DECIMAL(12, 2),
    total_cogs DECIMAL(12, 2),
    total_fees DECIMAL(12, 2),
    net_profit DECIMAL(12, 2),
    profit_margin DECIMAL(5, 2),
    units_sold INT,
    avg_days_to_sell DECIMAL(10, 2),
    last_updated TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
COMMENT ON TABLE analytics.product_profitability_analysis_mv IS 'Product-level profitability analysis';

CREATE TABLE IF NOT EXISTS analytics.supplier_performance (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    supplier_id BIGINT NOT NULL,
    total_orders INT,
    on_time_deliveries INT,
    quality_score DECIMAL(3, 2),
    avg_lead_time_days DECIMAL(5, 1),
    return_rate DECIMAL(5, 2),
    evaluation_period_start DATE NOT NULL,
    evaluation_period_end DATE NOT NULL,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_analytics_supplier_performance_supplier ON analytics.supplier_performance(supplier_id);
COMMENT ON TABLE analytics.supplier_performance IS 'Supplier performance metrics';

CREATE TABLE IF NOT EXISTS analytics.supplier_performance_dashboard_mv (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    supplier_id BIGINT,
    total_purchases DECIMAL(12, 2),
    total_units_purchased INT,
    avg_purchase_price DECIMAL(10, 2),
    quality_score DECIMAL(3, 2),
    on_time_delivery_rate DECIMAL(5, 2),
    last_updated TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
COMMENT ON TABLE analytics.supplier_performance_dashboard_mv IS 'Supplier performance dashboard';

-- ============================================================================
-- FINANCIAL MODULE (3 tables)
-- ============================================================================

CREATE TABLE IF NOT EXISTS financial.product_price_snapshot (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    product_id BIGINT NOT NULL,
    snapshot_date DATE NOT NULL,
    retail_price DECIMAL(10, 2),
    market_price DECIMAL(10, 2),
    lowest_ask DECIMAL(10, 2),
    highest_bid DECIMAL(10, 2),
    last_sale_price DECIMAL(10, 2),
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_financial_price_snapshot_product ON financial.product_price_snapshot(product_id);
CREATE INDEX idx_financial_price_snapshot_date ON financial.product_price_snapshot(snapshot_date);
COMMENT ON TABLE financial.product_price_snapshot IS 'Daily price snapshots for products';

CREATE TABLE IF NOT EXISTS financial.supplier_contract (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    supplier_id BIGINT NOT NULL,
    contract_number VARCHAR(100) NOT NULL UNIQUE,
    start_date DATE NOT NULL,
    end_date DATE,
    payment_terms TEXT,
    discount_rate DECIMAL(5, 2),
    min_order_quantity INT,
    notes TEXT,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_financial_supplier_contract_supplier ON financial.supplier_contract(supplier_id);
COMMENT ON TABLE financial.supplier_contract IS 'Supplier contracts and terms';

CREATE TABLE IF NOT EXISTS financial.supplier_rating_history (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    supplier_id BIGINT NOT NULL,
    rating DECIMAL(3, 2) NOT NULL,
    rating_date DATE NOT NULL,
    evaluator VARCHAR(100),
    notes TEXT,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_financial_supplier_rating_supplier ON financial.supplier_rating_history(supplier_id);
COMMENT ON TABLE financial.supplier_rating_history IS 'Historical supplier ratings';

-- ============================================================================
-- LOGGING MODULE (3 tables)
-- ============================================================================

CREATE TABLE IF NOT EXISTS logging.audit_trail (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    user_identifier UUID NOT NULL,
    action VARCHAR(255) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id BIGINT,
    old_values JSONB,
    new_values JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    action_timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_logging_audit_trail_user ON logging.audit_trail(user_identifier);
CREATE INDEX idx_logging_audit_trail_entity ON logging.audit_trail(entity_type, entity_id);
CREATE INDEX idx_logging_audit_trail_timestamp ON logging.audit_trail(action_timestamp);
COMMENT ON TABLE logging.audit_trail IS 'Audit log for all system changes';

CREATE TABLE IF NOT EXISTS logging.stockx_presale_marking (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    listing_id BIGINT NOT NULL,
    marked_presale BOOLEAN NOT NULL DEFAULT false,
    presale_date DATE,
    marked_by VARCHAR(100),
    marked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    notes TEXT,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_logging_stockx_presale_listing ON logging.stockx_presale_marking(listing_id);
COMMENT ON TABLE logging.stockx_presale_marking IS 'StockX presale marking log';

CREATE TABLE IF NOT EXISTS logging.system_log (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    log_level VARCHAR(20) NOT NULL,
    log_source VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    stack_trace TEXT,
    additional_data JSONB,
    log_timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_logging_system_log_level ON logging.system_log(log_level);
CREATE INDEX idx_logging_system_log_source ON logging.system_log(log_source);
CREATE INDEX idx_logging_system_log_timestamp ON logging.system_log(log_timestamp);
COMMENT ON TABLE logging.system_log IS 'System error and event logs';

-- ============================================================================
-- PRICING MODULE (7 tables)
-- ============================================================================

CREATE TABLE IF NOT EXISTS pricing.brand_multiplier (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    brand_id BIGINT NOT NULL,
    multiplier DECIMAL(5, 2) NOT NULL DEFAULT 1.00,
    effective_from DATE NOT NULL,
    effective_to DATE,
    notes TEXT,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_pricing_brand_multiplier_brand ON pricing.brand_multiplier(brand_id);
COMMENT ON TABLE pricing.brand_multiplier IS 'Brand-specific pricing multipliers';

CREATE TABLE IF NOT EXISTS pricing.demand_pattern (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    product_id BIGINT NOT NULL,
    pattern_type VARCHAR(50) NOT NULL,
    seasonality_index DECIMAL(5, 2),
    trend_direction VARCHAR(20),
    volatility_score DECIMAL(5, 2),
    analysis_date DATE NOT NULL,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_pricing_demand_pattern_product ON pricing.demand_pattern(product_id);
COMMENT ON TABLE pricing.demand_pattern IS 'Product demand pattern analysis';

CREATE TABLE IF NOT EXISTS pricing.kpi (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    kpi_name VARCHAR(100) NOT NULL,
    kpi_value DECIMAL(12, 2) NOT NULL,
    target_value DECIMAL(12, 2),
    measurement_date DATE NOT NULL,
    category VARCHAR(50),
    notes TEXT,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_pricing_kpi_name ON pricing.kpi(kpi_name);
CREATE INDEX idx_pricing_kpi_date ON pricing.kpi(measurement_date);
COMMENT ON TABLE pricing.kpi IS 'Key Performance Indicators tracking';

CREATE TABLE IF NOT EXISTS pricing.market_price (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    product_id BIGINT NOT NULL,
    platform_id BIGINT NOT NULL,
    size_id BIGINT,
    lowest_ask DECIMAL(10, 2),
    highest_bid DECIMAL(10, 2),
    last_sale DECIMAL(10, 2),
    sales_volume_24h INT,
    price_date DATE NOT NULL,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_pricing_market_price_product ON pricing.market_price(product_id);
CREATE INDEX idx_pricing_market_price_platform ON pricing.market_price(platform_id);
COMMENT ON TABLE pricing.market_price IS 'Market prices across platforms';

CREATE TABLE IF NOT EXISTS pricing.price_history (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    product_id BIGINT NOT NULL,
    price_type VARCHAR(50) NOT NULL,
    price_value DECIMAL(10, 2) NOT NULL,
    effective_date DATE NOT NULL,
    source VARCHAR(100),
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_pricing_price_history_product ON pricing.price_history(product_id);
CREATE INDEX idx_pricing_price_history_date ON pricing.price_history(effective_date);
COMMENT ON TABLE pricing.price_history IS 'Historical price tracking';

CREATE TABLE IF NOT EXISTS pricing.price_rule (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    rule_name VARCHAR(100) NOT NULL UNIQUE,
    rule_type VARCHAR(50) NOT NULL,
    priority INT NOT NULL DEFAULT 0,
    conditions JSONB,
    actions JSONB,
    active BOOLEAN NOT NULL DEFAULT true,
    effective_from DATE NOT NULL,
    effective_to DATE,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
COMMENT ON TABLE pricing.price_rule IS 'Dynamic pricing rules';

CREATE TABLE IF NOT EXISTS pricing.sales_forecast (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    product_id BIGINT NOT NULL,
    forecast_date DATE NOT NULL,
    forecasted_units INT,
    forecasted_revenue DECIMAL(12, 2),
    confidence_level DECIMAL(5, 2),
    model_used VARCHAR(100),
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_pricing_sales_forecast_product ON pricing.sales_forecast(product_id);
CREATE INDEX idx_pricing_sales_forecast_date ON pricing.sales_forecast(forecast_date);
COMMENT ON TABLE pricing.sales_forecast IS 'Sales forecasting data';

-- ============================================================================
-- REALTIME MODULE (1 table)
-- ============================================================================

CREATE TABLE IF NOT EXISTS realtime.event_log (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    event_type VARCHAR(100) NOT NULL,
    event_source VARCHAR(100) NOT NULL,
    event_data JSONB,
    correlation_id UUID,
    user_identifier UUID,
    event_timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_realtime_event_log_type ON realtime.event_log(event_type);
CREATE INDEX idx_realtime_event_log_source ON realtime.event_log(event_source);
CREATE INDEX idx_realtime_event_log_timestamp ON realtime.event_log(event_timestamp);
CREATE INDEX idx_realtime_event_log_correlation ON realtime.event_log(correlation_id);
COMMENT ON TABLE realtime.event_log IS 'Real-time event logging';

-- ============================================================================
-- SUPPLIER MODULE (3 tables)
-- ============================================================================

CREATE TABLE IF NOT EXISTS supplier.account (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    supplier_id BIGINT NOT NULL,
    account_number VARCHAR(100) NOT NULL UNIQUE,
    account_type VARCHAR(50) NOT NULL,
    balance DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    credit_limit DECIMAL(12, 2),
    payment_terms_days INT DEFAULT 30,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_supplier_account_supplier ON supplier.account(supplier_id);
COMMENT ON TABLE supplier.account IS 'Supplier account information';

CREATE TABLE IF NOT EXISTS supplier.account_purchase_history (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    account_id BIGINT NOT NULL,
    purchase_date DATE NOT NULL,
    product_id BIGINT NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    total_amount DECIMAL(12, 2) NOT NULL,
    vat_amount DECIMAL(12, 2),
    invoice_number VARCHAR(100),
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_supplier_purchase_history_account ON supplier.account_purchase_history(account_id);
CREATE INDEX idx_supplier_purchase_history_product ON supplier.account_purchase_history(product_id);
COMMENT ON TABLE supplier.account_purchase_history IS 'Supplier purchase history';

CREATE TABLE IF NOT EXISTS supplier.account_setting (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    account_id BIGINT NOT NULL,
    setting_key VARCHAR(100) NOT NULL,
    setting_value TEXT,
    is_encrypted BOOLEAN NOT NULL DEFAULT false,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ,
    UNIQUE (account_id, setting_key)
);
CREATE INDEX idx_supplier_account_setting_account ON supplier.account_setting(account_id);
COMMENT ON TABLE supplier.account_setting IS 'Supplier account settings';

-- ============================================================================
-- TRANSACTION MODULE (4 tables)
-- ============================================================================

CREATE TABLE IF NOT EXISTS transaction.transaction (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    transaction_number VARCHAR(100) NOT NULL UNIQUE,
    product_id BIGINT NOT NULL,
    transaction_type VARCHAR(50) NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    total_amount DECIMAL(12, 2) NOT NULL,
    transaction_date TIMESTAMPTZ NOT NULL,
    platform_id BIGINT,
    status VARCHAR(50) NOT NULL,
    notes TEXT,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_transaction_transaction_product ON transaction.transaction(product_id);
CREATE INDEX idx_transaction_transaction_platform ON transaction.transaction(platform_id);
CREATE INDEX idx_transaction_transaction_date ON transaction.transaction(transaction_date);
COMMENT ON TABLE transaction.transaction IS 'All transaction records';

CREATE TABLE IF NOT EXISTS transaction.pricing_history (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    transaction_id BIGINT NOT NULL,
    price_component VARCHAR(50) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    calculation_method VARCHAR(100),
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_transaction_pricing_history_transaction ON transaction.pricing_history(transaction_id);
COMMENT ON TABLE transaction.pricing_history IS 'Transaction pricing breakdown history';

CREATE TABLE IF NOT EXISTS transaction.stockx_listing (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    product_id BIGINT NOT NULL,
    size_id BIGINT NOT NULL,
    listing_price DECIMAL(10, 2) NOT NULL,
    lowest_ask DECIMAL(10, 2),
    highest_bid DECIMAL(10, 2),
    status listing_status_type NOT NULL DEFAULT 'active',
    listed_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ,
    external_listing_id VARCHAR(255),
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_transaction_stockx_listing_product ON transaction.stockx_listing(product_id);
CREATE INDEX idx_transaction_stockx_listing_size ON transaction.stockx_listing(size_id);
CREATE INDEX idx_transaction_stockx_listing_status ON transaction.stockx_listing(status);
COMMENT ON TABLE transaction.stockx_listing IS 'StockX listings';

CREATE TABLE IF NOT EXISTS transaction.stockx_order (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    listing_id BIGINT NOT NULL,
    order_number VARCHAR(100) NOT NULL UNIQUE,
    buyer_info JSONB,
    sale_price DECIMAL(10, 2) NOT NULL,
    platform_fee DECIMAL(10, 2),
    shipping_fee DECIMAL(10, 2),
    net_proceeds DECIMAL(10, 2),
    status order_status_type NOT NULL DEFAULT 'pending',
    order_date TIMESTAMPTZ NOT NULL,
    shipped_date TIMESTAMPTZ,
    completed_date TIMESTAMPTZ,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_transaction_stockx_order_listing ON transaction.stockx_order(listing_id);
CREATE INDEX idx_transaction_stockx_order_status ON transaction.stockx_order(status);
CREATE INDEX idx_transaction_stockx_order_date ON transaction.stockx_order(order_date);
COMMENT ON TABLE transaction.stockx_order IS 'StockX orders';

-- ============================================================================
-- OPERATIONS MODULE - ADDITIONAL TABLES (2 more tables found)
-- ============================================================================

CREATE TABLE IF NOT EXISTS operations.listing_history (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    product_id BIGINT NOT NULL,
    platform_id BIGINT NOT NULL,
    listing_price DECIMAL(10, 2) NOT NULL,
    listed_at TIMESTAMPTZ NOT NULL,
    delisted_at TIMESTAMPTZ,
    status listing_status_type NOT NULL,
    views_count INT DEFAULT 0,
    notes TEXT,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_operations_listing_history_product ON operations.listing_history(product_id);
CREATE INDEX idx_operations_listing_history_platform ON operations.listing_history(platform_id);
COMMENT ON TABLE operations.listing_history IS 'Product listing history across platforms';

CREATE TABLE IF NOT EXISTS operations.order_fulfillment (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    order_id BIGINT NOT NULL,
    fulfillment_status fulfillment_status_type NOT NULL DEFAULT 'pending',
    tracking_number VARCHAR(100),
    carrier VARCHAR(100),
    shipped_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    notes TEXT,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_operations_order_fulfillment_order ON operations.order_fulfillment(order_id);
CREATE INDEX idx_operations_order_fulfillment_status ON operations.order_fulfillment(fulfillment_status);
COMMENT ON TABLE operations.order_fulfillment IS 'Order fulfillment tracking';

-- ============================================================================
-- PLATFORM MODULE - ADDITIONAL TABLES (3 more tables found)
-- ============================================================================

CREATE TABLE IF NOT EXISTS platform.fee (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    platform_id BIGINT NOT NULL,
    fee_type VARCHAR(50) NOT NULL,
    fee_percentage DECIMAL(5, 2),
    flat_fee DECIMAL(10, 2),
    min_fee DECIMAL(10, 2),
    max_fee DECIMAL(10, 2),
    effective_from DATE NOT NULL,
    effective_to DATE,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_platform_fee_platform ON platform.fee(platform_id);
COMMENT ON TABLE platform.fee IS 'Platform fee structures';

CREATE TABLE IF NOT EXISTS platform.integration (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    platform_id BIGINT NOT NULL,
    integration_type VARCHAR(50) NOT NULL,
    api_endpoint VARCHAR(500),
    api_key_encrypted TEXT,
    config_data JSONB,
    is_active BOOLEAN NOT NULL DEFAULT true,
    last_sync_at TIMESTAMPTZ,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_platform_integration_platform ON platform.integration(platform_id);
COMMENT ON TABLE platform.integration IS 'Platform API integrations';

CREATE TABLE IF NOT EXISTS platform.size_display (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    platform_id BIGINT NOT NULL,
    size_id BIGINT NOT NULL,
    display_format VARCHAR(50) NOT NULL,
    display_value VARCHAR(20) NOT NULL,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ,
    UNIQUE (platform_id, size_id)
);
CREATE INDEX idx_platform_size_display_platform ON platform.size_display(platform_id);
CREATE INDEX idx_platform_size_display_size ON platform.size_display(size_id);
COMMENT ON TABLE platform.size_display IS 'Platform-specific size display formats';

-- ============================================================================
-- PRODUCT MODULE - ADDITIONAL TABLES (3 more tables found)
-- ============================================================================

CREATE TABLE IF NOT EXISTS product.inventory_financial (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    product_id BIGINT NOT NULL,
    size_id BIGINT NOT NULL,
    purchase_price DECIMAL(10, 2) NOT NULL,
    current_valuation DECIMAL(10, 2),
    depreciation_rate DECIMAL(5, 2),
    last_valuation_date DATE,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_product_inventory_financial_product ON product.inventory_financial(product_id);
COMMENT ON TABLE product.inventory_financial IS 'Inventory financial valuation';

CREATE TABLE IF NOT EXISTS product.inventory_lifecycle (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    product_id BIGINT NOT NULL,
    size_id BIGINT NOT NULL,
    received_date DATE NOT NULL,
    inspection_date DATE,
    listed_date DATE,
    sold_date DATE,
    shipped_date DATE,
    lifecycle_status VARCHAR(50) NOT NULL,
    days_in_inventory INT,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_product_inventory_lifecycle_product ON product.inventory_lifecycle(product_id);
CREATE INDEX idx_product_inventory_lifecycle_status ON product.inventory_lifecycle(lifecycle_status);
COMMENT ON TABLE product.inventory_lifecycle IS 'Product inventory lifecycle tracking';

CREATE TABLE IF NOT EXISTS product.inventory_reservation (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    product_id BIGINT NOT NULL,
    size_id BIGINT NOT NULL,
    quantity_reserved INT NOT NULL,
    reserved_for VARCHAR(100),
    reservation_date TIMESTAMPTZ NOT NULL DEFAULT now(),
    expiration_date TIMESTAMPTZ,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_product_inventory_reservation_product ON product.inventory_reservation(product_id);
CREATE INDEX idx_product_inventory_reservation_status ON product.inventory_reservation(status);
COMMENT ON TABLE product.inventory_reservation IS 'Inventory reservation tracking';

CREATE TABLE IF NOT EXISTS product.inventory_stock (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    product_id BIGINT NOT NULL,
    size_id BIGINT NOT NULL,
    condition condition_type NOT NULL DEFAULT 'new',
    quantity_available INT NOT NULL DEFAULT 0,
    quantity_reserved INT NOT NULL DEFAULT 0,
    quantity_sold INT NOT NULL DEFAULT 0,
    location VARCHAR(100),
    min_stock_level INT,
    reorder_point INT,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ,
    UNIQUE (product_id, size_id, condition, location)
);
CREATE INDEX idx_product_inventory_stock_product ON product.inventory_stock(product_id);
CREATE INDEX idx_product_inventory_stock_size ON product.inventory_stock(size_id);
COMMENT ON TABLE product.inventory_stock IS 'Current inventory stock levels';

CREATE TABLE IF NOT EXISTS product.listing (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    product_id BIGINT NOT NULL,
    platform_id BIGINT NOT NULL,
    size_id BIGINT NOT NULL,
    listing_price DECIMAL(10, 2) NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    condition condition_type NOT NULL DEFAULT 'new',
    status listing_status_type NOT NULL DEFAULT 'active',
    external_listing_id VARCHAR(255),
    listed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_product_listing_product ON product.listing(product_id);
CREATE INDEX idx_product_listing_platform ON product.listing(platform_id);
CREATE INDEX idx_product_listing_status ON product.listing(status);
COMMENT ON TABLE product.listing IS 'Product listings across platforms';

CREATE TABLE IF NOT EXISTS product.order (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    listing_id BIGINT NOT NULL,
    order_number VARCHAR(100) NOT NULL UNIQUE,
    platform_id BIGINT NOT NULL,
    buyer_info JSONB,
    sale_price DECIMAL(10, 2) NOT NULL,
    platform_fee DECIMAL(10, 2),
    shipping_fee DECIMAL(10, 2),
    tax_amount DECIMAL(10, 2),
    net_proceeds DECIMAL(10, 2),
    status order_status_type NOT NULL DEFAULT 'pending',
    order_date TIMESTAMPTZ NOT NULL,
    payment_date TIMESTAMPTZ,
    shipped_date TIMESTAMPTZ,
    delivered_date TIMESTAMPTZ,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_product_order_listing ON product.order(listing_id);
CREATE INDEX idx_product_order_platform ON product.order(platform_id);
CREATE INDEX idx_product_order_status ON product.order(status);
CREATE INDEX idx_product_order_date ON product.order(order_date);
COMMENT ON TABLE product.order IS 'Product orders';

-- ============================================================================
-- INTEGRATION MODULE - ADDITIONAL TABLE (1 more table found)
-- ============================================================================

CREATE TABLE IF NOT EXISTS integration.source_price (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    product_id BIGINT NOT NULL,
    source integration_source_type NOT NULL,
    source_identifier VARCHAR(255) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
    scraped_at TIMESTAMPTZ NOT NULL,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_integration_source_price_product ON integration.source_price(product_id);
CREATE INDEX idx_integration_source_price_source ON integration.source_price(source);
COMMENT ON TABLE integration.source_price IS 'External price data sources';

-- ============================================================================
-- TRIGGERS FOR AUTO-UPDATE OF date_updated (PHASE 2 TABLES)
-- ============================================================================

-- Analytics triggers
CREATE TRIGGER trg_analytics_current_inventory_status_mv_updated
    BEFORE UPDATE ON analytics.current_inventory_status_mv
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_analytics_daily_sales_summary_mv_updated
    BEFORE UPDATE ON analytics.daily_sales_summary_mv
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_analytics_marketplace_data_updated
    BEFORE UPDATE ON analytics.marketplace_data
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_analytics_marketplace_summary_updated
    BEFORE UPDATE ON analytics.marketplace_summary
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_analytics_monthly_pl_summary_mv_updated
    BEFORE UPDATE ON analytics.monthly_pl_summary_mv
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_analytics_platform_performance_comparison_mv_updated
    BEFORE UPDATE ON analytics.platform_performance_comparison_mv
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_analytics_product_profitability_analysis_mv_updated
    BEFORE UPDATE ON analytics.product_profitability_analysis_mv
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_analytics_supplier_performance_updated
    BEFORE UPDATE ON analytics.supplier_performance
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_analytics_supplier_performance_dashboard_mv_updated
    BEFORE UPDATE ON analytics.supplier_performance_dashboard_mv
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

-- Financial triggers
CREATE TRIGGER trg_financial_product_price_snapshot_updated
    BEFORE UPDATE ON financial.product_price_snapshot
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_financial_supplier_contract_updated
    BEFORE UPDATE ON financial.supplier_contract
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_financial_supplier_rating_history_updated
    BEFORE UPDATE ON financial.supplier_rating_history
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

-- Logging triggers
CREATE TRIGGER trg_logging_audit_trail_updated
    BEFORE UPDATE ON logging.audit_trail
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_logging_stockx_presale_marking_updated
    BEFORE UPDATE ON logging.stockx_presale_marking
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_logging_system_log_updated
    BEFORE UPDATE ON logging.system_log
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

-- Pricing triggers
CREATE TRIGGER trg_pricing_brand_multiplier_updated
    BEFORE UPDATE ON pricing.brand_multiplier
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_pricing_demand_pattern_updated
    BEFORE UPDATE ON pricing.demand_pattern
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_pricing_kpi_updated
    BEFORE UPDATE ON pricing.kpi
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_pricing_market_price_updated
    BEFORE UPDATE ON pricing.market_price
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_pricing_price_history_updated
    BEFORE UPDATE ON pricing.price_history
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_pricing_price_rule_updated
    BEFORE UPDATE ON pricing.price_rule
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_pricing_sales_forecast_updated
    BEFORE UPDATE ON pricing.sales_forecast
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

-- Realtime triggers
CREATE TRIGGER trg_realtime_event_log_updated
    BEFORE UPDATE ON realtime.event_log
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

-- Supplier triggers
CREATE TRIGGER trg_supplier_account_updated
    BEFORE UPDATE ON supplier.account
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_supplier_account_purchase_history_updated
    BEFORE UPDATE ON supplier.account_purchase_history
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_supplier_account_setting_updated
    BEFORE UPDATE ON supplier.account_setting
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

-- Transaction triggers
CREATE TRIGGER trg_transaction_transaction_updated
    BEFORE UPDATE ON transaction.transaction
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_transaction_pricing_history_updated
    BEFORE UPDATE ON transaction.pricing_history
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_transaction_stockx_listing_updated
    BEFORE UPDATE ON transaction.stockx_listing
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_transaction_stockx_order_updated
    BEFORE UPDATE ON transaction.stockx_order
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

-- Operations triggers (additional)
CREATE TRIGGER trg_operations_listing_history_updated
    BEFORE UPDATE ON operations.listing_history
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_operations_order_fulfillment_updated
    BEFORE UPDATE ON operations.order_fulfillment
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

-- Platform triggers (additional)
CREATE TRIGGER trg_platform_fee_updated
    BEFORE UPDATE ON platform.fee
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_platform_integration_updated
    BEFORE UPDATE ON platform.integration
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_platform_size_display_updated
    BEFORE UPDATE ON platform.size_display
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

-- Product triggers (additional)
CREATE TRIGGER trg_product_inventory_financial_updated
    BEFORE UPDATE ON product.inventory_financial
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_product_inventory_lifecycle_updated
    BEFORE UPDATE ON product.inventory_lifecycle
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_product_inventory_reservation_updated
    BEFORE UPDATE ON product.inventory_reservation
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_product_inventory_stock_updated
    BEFORE UPDATE ON product.inventory_stock
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_product_listing_updated
    BEFORE UPDATE ON product.listing
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_product_order_updated
    BEFORE UPDATE ON product.order
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

-- Integration triggers (additional)
CREATE TRIGGER trg_integration_source_price_updated
    BEFORE UPDATE ON integration.source_price
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

-- ============================================================================
-- SUMMARY - PHASE 2
-- ============================================================================
-- Total Tables Created: 41 (31 + 10 additional found)
--
-- Modules Completed in Phase 2:
-- ✅ analytics (9 tables)
-- ✅ financial (3 tables)
-- ✅ logging (3 tables)
-- ✅ pricing (7 tables)
-- ✅ realtime (1 table)
-- ✅ supplier (3 tables)
-- ✅ transaction (4 tables)
-- ✅ operations (2 additional tables)
-- ✅ platform (3 additional tables)
-- ✅ product (6 additional tables)
-- ✅ integration (1 additional table)
--
-- GRAND TOTAL: 64 tables (23 from Phase 1 + 41 from Phase 2)
--
-- All 54 Gibson tables converted + 10 additional discovered tables!
-- ============================================================================

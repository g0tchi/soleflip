-- Database Reset Script
-- Date: 2025-12-07
-- Purpose: Delete all business data while preserving user/auth data
--
-- PRESERVED DATA:
--   - auth.users (Login-Daten)
--   - core.system_config (StockX API Keys, etc.)
--   - compliance.user_permissions (Benutzerberechtigungen)
--   - public.alembic_version (Migration-Tracking)
--
-- DELETED DATA:
--   - All products, brands, inventory
--   - All orders, transactions, listings
--   - All analytics, forecasts, KPIs
--   - All supplier data
--   - All logs and events
--

BEGIN;

-- Disable triggers temporarily for faster deletion
SET session_replication_role = replica;

-- ============================================================================
-- DELETE ANALYTICS DATA
-- ============================================================================
TRUNCATE TABLE analytics.demand_patterns CASCADE;
TRUNCATE TABLE analytics.forecast_accuracy CASCADE;
TRUNCATE TABLE analytics.marketplace_data CASCADE;
TRUNCATE TABLE analytics.pricing_kpis CASCADE;
TRUNCATE TABLE analytics.profit_opportunities CASCADE;
TRUNCATE TABLE analytics.sales_forecasts CASCADE;

-- ============================================================================
-- DELETE CATALOG DATA (Products, Brands, Categories)
-- ============================================================================
TRUNCATE TABLE catalog.product_variant CASCADE;
TRUNCATE TABLE catalog.product CASCADE;
TRUNCATE TABLE catalog.brand_history CASCADE;
TRUNCATE TABLE catalog.brand_patterns CASCADE;
TRUNCATE TABLE catalog.brand CASCADE;
TRUNCATE TABLE catalog.category CASCADE;
TRUNCATE TABLE catalog.size_conversion CASCADE;
TRUNCATE TABLE catalog.size_master CASCADE;
TRUNCATE TABLE catalog.sizes CASCADE;

-- ============================================================================
-- DELETE FINANCIAL DATA
-- ============================================================================
TRUNCATE TABLE financial.transaction CASCADE;

-- ============================================================================
-- DELETE INTEGRATION DATA (Imports, Source Prices)
-- ============================================================================
TRUNCATE TABLE integration.import_records CASCADE;
TRUNCATE TABLE integration.import_batches CASCADE;
TRUNCATE TABLE integration.source_prices CASCADE;

-- ============================================================================
-- DELETE INVENTORY DATA
-- ============================================================================
TRUNCATE TABLE inventory.stock_reservation CASCADE;
TRUNCATE TABLE inventory.stock_metrics CASCADE;
TRUNCATE TABLE inventory.stock_metrics_backup CASCADE;
TRUNCATE TABLE inventory.stock_lifecycle CASCADE;
TRUNCATE TABLE inventory.stock_lifecycle_backup CASCADE;
TRUNCATE TABLE inventory.stock_financial CASCADE;
TRUNCATE TABLE inventory.stock_financial_backup CASCADE;
TRUNCATE TABLE inventory.stock CASCADE;

-- ============================================================================
-- DELETE LOGGING DATA
-- ============================================================================
TRUNCATE TABLE logging.event_store CASCADE;
TRUNCATE TABLE logging.stockx_presale_markings CASCADE;
TRUNCATE TABLE logging.system_logs CASCADE;

-- ============================================================================
-- DELETE OPERATIONS DATA
-- ============================================================================
TRUNCATE TABLE operations.order_fulfillment CASCADE;
TRUNCATE TABLE operations.listing_history CASCADE;
TRUNCATE TABLE operations.supplier_platform_integration CASCADE;

-- ============================================================================
-- DELETE PLATFORM DATA
-- ============================================================================
TRUNCATE TABLE platform.marketplace_fee_structure CASCADE;
TRUNCATE TABLE platform.marketplace CASCADE;

-- ============================================================================
-- DELETE PRICING DATA
-- ============================================================================
TRUNCATE TABLE pricing.price_history CASCADE;
TRUNCATE TABLE pricing.market_prices CASCADE;
TRUNCATE TABLE pricing.brand_multipliers CASCADE;
TRUNCATE TABLE pricing.price_rules CASCADE;

-- ============================================================================
-- DELETE SALES DATA
-- ============================================================================
TRUNCATE TABLE sales.listing CASCADE;
TRUNCATE TABLE sales.order CASCADE;
TRUNCATE TABLE sales.pricing_history CASCADE;

-- ============================================================================
-- DELETE SUPPLIER DATA
-- ============================================================================
TRUNCATE TABLE supplier.purchase_history CASCADE;
TRUNCATE TABLE supplier.supplier_history CASCADE;
TRUNCATE TABLE supplier.profile CASCADE;
TRUNCATE TABLE supplier.account CASCADE;

-- ============================================================================
-- DELETE REALTIME DATA
-- ============================================================================
TRUNCATE TABLE realtime.event_log CASCADE;

-- ============================================================================
-- DELETE PUBLIC DATA (except alembic_version)
-- ============================================================================
TRUNCATE TABLE public.context_documents CASCADE;

-- ============================================================================
-- DELETE COMPLIANCE DATA (except user_permissions)
-- ============================================================================
TRUNCATE TABLE compliance.business_rules CASCADE;
TRUNCATE TABLE compliance.data_retention_policies CASCADE;

-- ============================================================================
-- DELETE CORE DATA (except system_config)
-- ============================================================================
TRUNCATE TABLE core.supplier_performance CASCADE;

-- Re-enable triggers
SET session_replication_role = DEFAULT;

COMMIT;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Count rows in preserved tables (should have data)
SELECT 'auth.users' AS table_name, COUNT(*) AS row_count FROM auth.users
UNION ALL
SELECT 'core.system_config', COUNT(*) FROM core.system_config
UNION ALL
SELECT 'compliance.user_permissions', COUNT(*) FROM compliance.user_permissions
UNION ALL
SELECT 'public.alembic_version', COUNT(*) FROM public.alembic_version;

-- Count rows in deleted tables (should be 0)
SELECT 'catalog.product' AS table_name, COUNT(*) AS row_count FROM catalog.product
UNION ALL
SELECT 'inventory.stock', COUNT(*) FROM inventory.stock
UNION ALL
SELECT 'sales.order', COUNT(*) FROM sales.order
UNION ALL
SELECT 'supplier.account', COUNT(*) FROM supplier.account;

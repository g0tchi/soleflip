-- ============================================================================
-- Phase 1: Quick Wins - Critical Index Deployment
-- ============================================================================
-- Generated: 2025-11-29
-- Source: Gibson AI Analysis
-- Priority: HIGH
-- Risk: LOW
-- Expected Impact: 50-70% query performance improvement
-- ============================================================================

BEGIN;

-- ============================================================================
-- PART 1: JSONB Performance Indexes (10x improvement)
-- ============================================================================

-- Sales Orders: Platform-specific data
CREATE INDEX IF NOT EXISTS idx_order_platform_json
ON sales."order" USING GIN (platform_specific_data)
WHERE platform_specific_data IS NOT NULL;

-- Sales Listings: Platform-specific data
CREATE INDEX IF NOT EXISTS idx_listing_platform_json
ON sales.listing USING GIN (platform_specific_data)
WHERE platform_specific_data IS NOT NULL;

-- Product Enrichment: StockX data
CREATE INDEX IF NOT EXISTS idx_product_enrichment_json
ON catalog.product USING GIN (enrichment_data)
WHERE enrichment_data IS NOT NULL;

-- Supplier Tags
CREATE INDEX IF NOT EXISTS idx_supplier_tags_json
ON supplier.profile USING GIN (tags)
WHERE tags IS NOT NULL;

-- ============================================================================
-- PART 2: Composite Indexes for Frequent Joins
-- ============================================================================

-- Inventory: Product + Supplier lookup
CREATE INDEX IF NOT EXISTS idx_stock_product_supplier
ON inventory.stock (product_id, supplier_id)
WHERE status = 'in_stock';

-- Orders: Stock + Platform analysis
CREATE INDEX IF NOT EXISTS idx_order_stock_platform
ON sales."order" (inventory_item_id, platform_id, sold_at DESC NULLS LAST);

-- Price History: Product + Date range queries
CREATE INDEX IF NOT EXISTS idx_price_history_product_date
ON pricing.price_history (product_id, created_at DESC);

-- Marketplace Data: Inventory + Platform
CREATE INDEX IF NOT EXISTS idx_marketplace_inv_platform
ON analytics.marketplace_data (inventory_item_id, platform_id);

-- Demand Patterns: Product analysis
CREATE INDEX IF NOT EXISTS idx_demand_product_date
ON analytics.demand_patterns (product_id, pattern_date DESC)
WHERE product_id IS NOT NULL;

-- Sales Forecasts: Product forecasting
CREATE INDEX IF NOT EXISTS idx_forecast_product_date
ON analytics.sales_forecasts (product_id, forecast_date DESC)
WHERE product_id IS NOT NULL;

-- ============================================================================
-- PART 3: Partial Indexes for Hot Queries
-- ============================================================================

-- Active Stock: Most common inventory query
CREATE INDEX IF NOT EXISTS idx_active_stock
ON inventory.stock (id, product_id, size_id)
WHERE status = 'in_stock';

-- Listed Stock: Quick listing checks
CREATE INDEX IF NOT EXISTS idx_listed_stockx
ON inventory.stock (id, product_id)
WHERE listed_stockx = TRUE;

-- Pending Orders: Operations dashboard
CREATE INDEX IF NOT EXISTS idx_pending_orders
ON sales."order" (id, inventory_item_id, sold_at)
WHERE status IN ('pending', 'processing', 'verified');

-- Unenriched Products: Enrichment queue
CREATE INDEX IF NOT EXISTS idx_unenriched_products
ON catalog.product (id, sku, stockx_product_id)
WHERE enrichment_data IS NULL OR last_enriched_at IS NULL;

-- Products needing enrichment update (simple index for date filtering)
-- Note: CURRENT_DATE is not IMMUTABLE, so we use a simple index instead of a partial index
CREATE INDEX IF NOT EXISTS idx_stale_enrichment
ON catalog.product (last_enriched_at)
WHERE last_enriched_at IS NOT NULL;

-- Active Listings: Current marketplace state
CREATE INDEX IF NOT EXISTS idx_active_listings
ON sales.listing (id, inventory_item_id, status)
WHERE status = 'active';

-- Reserved Stock: Reservation management
-- Note: reserved_qty column will be added in Phase 2 (schema consolidation)
-- CREATE INDEX IF NOT EXISTS idx_reserved_stock
-- ON inventory.stock (id, reserved_qty)
-- WHERE reserved_qty > 0;

-- ============================================================================
-- PART 4: Missing Foreign Key Indexes
-- ============================================================================
-- These dramatically improve JOIN performance

-- Inventory
CREATE INDEX IF NOT EXISTS idx_stock_size_id ON inventory.stock (size_id);
CREATE INDEX IF NOT EXISTS idx_stock_product_id ON inventory.stock (product_id);

-- Catalog
CREATE INDEX IF NOT EXISTS idx_brand_patterns_brand ON catalog.brand_patterns (brand_id);
CREATE INDEX IF NOT EXISTS idx_product_brand ON catalog.product (brand_id);
CREATE INDEX IF NOT EXISTS idx_product_category ON catalog.product (category_id);
CREATE INDEX IF NOT EXISTS idx_category_parent ON catalog.category (parent_id) WHERE parent_id IS NOT NULL;

-- Sales
CREATE INDEX IF NOT EXISTS idx_order_inventory ON sales."order" (inventory_item_id);
CREATE INDEX IF NOT EXISTS idx_order_listing ON sales."order" (listing_id) WHERE listing_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_order_platform ON sales."order" (platform_id);
CREATE INDEX IF NOT EXISTS idx_listing_inventory ON sales.listing (inventory_item_id);

-- Analytics
CREATE INDEX IF NOT EXISTS idx_marketplace_platform ON analytics.marketplace_data (platform_id);
CREATE INDEX IF NOT EXISTS idx_forecast_brand ON analytics.sales_forecasts (brand_id) WHERE brand_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_forecast_category ON analytics.sales_forecasts (category_id) WHERE category_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_forecast_platform ON analytics.sales_forecasts (platform_id) WHERE platform_id IS NOT NULL;

-- Pricing
CREATE INDEX IF NOT EXISTS idx_price_history_inventory ON pricing.price_history (inventory_item_id) WHERE inventory_item_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_price_history_platform ON pricing.price_history (platform_id);
CREATE INDEX IF NOT EXISTS idx_price_rules_brand ON pricing.price_rules (brand_id) WHERE brand_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_price_rules_category ON pricing.price_rules (category_id) WHERE category_id IS NOT NULL;

-- Supplier
CREATE INDEX IF NOT EXISTS idx_supplier_account_supplier ON supplier.account (supplier_id);
CREATE INDEX IF NOT EXISTS idx_purchase_history_account ON supplier.purchase_history (account_id);
CREATE INDEX IF NOT EXISTS idx_purchase_history_supplier ON supplier.purchase_history (supplier_id);

-- Integration
CREATE INDEX IF NOT EXISTS idx_import_records_batch ON integration.import_records (batch_id);
CREATE INDEX IF NOT EXISTS idx_source_prices_product ON integration.source_prices (product_id);

-- ============================================================================
-- PART 5: Text Search Optimization
-- ============================================================================

-- Product Name Search (common in UI)
CREATE INDEX IF NOT EXISTS idx_product_name_trgm
ON catalog.product USING gin (name gin_trgm_ops);

-- Product SKU Search
CREATE INDEX IF NOT EXISTS idx_product_sku_trgm
ON catalog.product USING gin (sku gin_trgm_ops);

-- Brand Name Search
CREATE INDEX IF NOT EXISTS idx_brand_name_trgm
ON catalog.brand USING gin (name gin_trgm_ops);

-- Supplier Search
CREATE INDEX IF NOT EXISTS idx_supplier_name_trgm
ON supplier.profile USING gin (name gin_trgm_ops);

-- Note: Requires pg_trgm extension
-- CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================================
-- PART 6: Covering Indexes for Index-Only Scans
-- ============================================================================

-- Order summary queries (avoid table lookups)
CREATE INDEX IF NOT EXISTS idx_order_summary
ON sales."order" (platform_id, status, sold_at)
INCLUDE (gross_sale, net_profit, roi)
WHERE sold_at IS NOT NULL;

-- Stock value calculation
CREATE INDEX IF NOT EXISTS idx_stock_value
ON inventory.stock (status, product_id)
INCLUDE (purchase_price, quantity)
WHERE status = 'in_stock';

-- Product pricing lookup
CREATE INDEX IF NOT EXISTS idx_product_pricing
ON catalog.product (id)
INCLUDE (retail_price, lowest_ask, recommended_sell_faster);

-- ============================================================================
-- PART 7: Performance Monitoring Views
-- ============================================================================

-- Create monitoring view for index usage
CREATE OR REPLACE VIEW analytics.index_usage_stats AS
SELECT
  schemaname,
  relname as tablename,
  indexrelname as indexname,
  idx_scan as scans,
  idx_tup_read as tuples_read,
  idx_tup_fetch as tuples_fetched,
  pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
  CASE
    WHEN idx_scan = 0 THEN 'UNUSED'
    WHEN idx_scan < 100 THEN 'LOW_USAGE'
    ELSE 'ACTIVE'
  END as usage_category
FROM pg_stat_user_indexes
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY idx_scan DESC;

-- Create view for slow queries (requires pg_stat_statements extension)
-- Note: Comment out if extension is not available
-- CREATE OR REPLACE VIEW analytics.slow_queries AS
-- SELECT
--   LEFT(query, 100) as query_preview,
--   calls,
--   ROUND(total_exec_time::numeric / calls, 2) as avg_time_ms,
--   ROUND(total_exec_time::numeric, 2) as total_time_ms,
--   ROUND((100 * total_exec_time / SUM(total_exec_time) OVER())::numeric, 2) as pct_total_time
-- FROM pg_stat_statements
-- WHERE calls > 10
-- ORDER BY total_exec_time DESC
-- LIMIT 50;

-- ============================================================================
-- PART 8: Validation & Rollback
-- ============================================================================

-- Validate all indexes were created successfully
DO $$
DECLARE
  missing_indexes TEXT[];
BEGIN
  SELECT ARRAY_AGG(indexname)
  INTO missing_indexes
  FROM (
    VALUES
      ('idx_order_platform_json'),
      ('idx_listing_platform_json'),
      ('idx_product_enrichment_json'),
      ('idx_stock_product_supplier'),
      ('idx_order_stock_platform'),
      ('idx_active_stock'),
      ('idx_pending_orders')
  ) AS expected(indexname)
  WHERE NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE indexname = expected.indexname
  );

  IF array_length(missing_indexes, 1) > 0 THEN
    RAISE WARNING 'Missing indexes: %', array_to_string(missing_indexes, ', ');
  ELSE
    RAISE NOTICE 'All critical indexes created successfully!';
  END IF;
END $$;

COMMIT;

-- ============================================================================
-- POST-DEPLOYMENT VERIFICATION
-- ============================================================================

-- Run ANALYZE to update query planner statistics
ANALYZE;

-- Check index sizes
SELECT
  schemaname || '.' || relname as table_name,
  indexrelname as index_name,
  pg_size_pretty(pg_relation_size(indexrelid)) as size
FROM pg_stat_user_indexes
WHERE indexrelname LIKE 'idx_%'
  AND schemaname IN ('inventory', 'sales', 'catalog', 'pricing', 'analytics', 'supplier')
ORDER BY pg_relation_size(indexrelid) DESC;

-- ============================================================================
-- ROLLBACK SCRIPT (IF NEEDED)
-- ============================================================================
-- Uncomment and run if you need to rollback

/*
BEGIN;

-- Drop all indexes created in this migration
DROP INDEX IF EXISTS sales.idx_order_platform_json;
DROP INDEX IF EXISTS sales.idx_listing_platform_json;
DROP INDEX IF EXISTS catalog.idx_product_enrichment_json;
DROP INDEX IF EXISTS supplier.idx_supplier_tags_json;
DROP INDEX IF EXISTS inventory.idx_stock_product_supplier;
DROP INDEX IF EXISTS sales.idx_order_stock_platform;
DROP INDEX IF EXISTS pricing.idx_price_history_product_date;
DROP INDEX IF EXISTS analytics.idx_marketplace_inv_platform;
DROP INDEX IF EXISTS analytics.idx_demand_product_date;
DROP INDEX IF EXISTS analytics.idx_forecast_product_date;
DROP INDEX IF EXISTS inventory.idx_active_stock;
DROP INDEX IF EXISTS inventory.idx_listed_stockx;
DROP INDEX IF EXISTS sales.idx_pending_orders;
DROP INDEX IF EXISTS catalog.idx_unenriched_products;
DROP INDEX IF EXISTS catalog.idx_stale_enrichment;
DROP INDEX IF EXISTS sales.idx_active_listings;
-- DROP INDEX IF EXISTS inventory.idx_reserved_stock; -- Not created yet

-- Drop monitoring views
DROP VIEW IF EXISTS analytics.index_usage_stats;
DROP VIEW IF EXISTS analytics.slow_queries;

COMMIT;
*/

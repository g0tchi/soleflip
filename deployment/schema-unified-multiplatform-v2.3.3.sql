-- ============================================================================
-- Unified Multi-Platform Schema Migration v2.3.3
-- Date: 2025-10-21
-- Purpose: Eliminate platform-specific tables, create unified multi-platform structure
-- ============================================================================

-- This migration implements a unified multi-platform pattern that scales
-- to any number of marketplaces (StockX, eBay, GOAT, Alias, etc.) without
-- requiring schema changes.

-- BEFORE (platform-specific tables):
-- transaction.stockx_listing       ← Only StockX
-- transaction.stockx_order         ← Only StockX
-- transaction.transaction          ← Financial transactions
-- transaction.pricing_history      ← Price changes
-- sales.listing                    ← Generic listings
-- sales.order                      ← Generic orders

-- AFTER (unified multi-platform):
-- sales.listing (with platform_specific_data JSONB)  ← ALL platforms
-- sales.order (with platform_specific_data JSONB)    ← ALL platforms
-- sales.pricing_history                              ← Price tracking
-- financial.transaction                              ← Financial settlement
-- [NO platform-specific tables needed]

-- ============================================================================
-- KEY DESIGN DECISION: Unified Pattern
-- ============================================================================

-- Following the existing unified orders pattern (v2.3.1), we extend this
-- approach to eliminate ALL platform-specific tables in favor of:
--
-- 1. Shared columns for common fields (price, status, dates)
-- 2. JSONB column for platform-specific data
-- 3. GIN index for JSONB query performance

-- ============================================================================
-- MIGRATION STEPS
-- ============================================================================

-- Step 1: Extend sales.listing for multi-platform support
ALTER TABLE sales.listing
ADD COLUMN IF NOT EXISTS platform_specific_data JSONB;

CREATE INDEX IF NOT EXISTS idx_listing_platform_data
ON sales.listing USING GIN (platform_specific_data);

-- Step 2: Extend sales.order for multi-platform support
ALTER TABLE sales.order
ADD COLUMN IF NOT EXISTS platform_specific_data JSONB;

CREATE INDEX IF NOT EXISTS idx_order_platform_data
ON sales.order USING GIN (platform_specific_data);

-- Step 3: Migrate StockX data (if exists)
-- Note: In this case, tables were empty, so migration was skipped

-- Step 4: Drop platform-specific tables
DROP TABLE IF EXISTS transaction.stockx_listing CASCADE;
DROP TABLE IF EXISTS transaction.stockx_order CASCADE;

-- Step 5: Move pricing_history to sales domain
ALTER TABLE transaction.pricing_history SET SCHEMA sales;

-- Step 6: Move transaction to financial domain
ALTER TABLE transaction.transaction SET SCHEMA financial;

-- Step 7: Transaction schema is now empty and can be dropped
-- (Will be removed in init-databases.sql)

-- ============================================================================
-- UNIFIED MULTI-PLATFORM USAGE EXAMPLES
-- ============================================================================

-- Example 1: StockX Listing
INSERT INTO sales.listing (
    product_id, platform_id, size_id, listing_price,
    external_listing_id, platform_specific_data
) VALUES (
    1,
    (SELECT id FROM platform.marketplace WHERE name = 'StockX'),
    10,
    200.00,
    'stockx-abc123',
    '{
        "ask_price": 200.00,
        "bid_price": 180.00,
        "consignment_type": "instant",
        "stockx_product_id": "air-jordan-1-chicago",
        "variant_id": "size-9",
        "seller_level": "verified"
    }'::jsonb
);

-- Example 2: eBay Listing
INSERT INTO sales.listing (
    product_id, platform_id, size_id, listing_price,
    external_listing_id, platform_specific_data
) VALUES (
    1,
    (SELECT id FROM platform.marketplace WHERE name = 'eBay'),
    10,
    195.00,
    'ebay-987654321',
    '{
        "auction_end_date": "2024-01-20T18:00:00Z",
        "buy_it_now_price": 195.00,
        "listing_format": "fixed_price",
        "category_id": "15709",
        "shipping_cost": 10.00,
        "handling_time_days": 1,
        "returns_accepted": true
    }'::jsonb
);

-- Example 3: GOAT Listing
INSERT INTO sales.listing (
    product_id, platform_id, size_id, listing_price,
    external_listing_id, platform_specific_data
) VALUES (
    1,
    (SELECT id FROM platform.marketplace WHERE name = 'GOAT'),
    10,
    190.00,
    'goat-xyz789',
    '{
        "instant_ship": true,
        "consignment_status": "pending",
        "condition_grade": "A+",
        "authentication_required": true,
        "payout_percentage": 0.88
    }'::jsonb
);

-- Example 4: Alias Listing (new platform - no schema change needed!)
INSERT INTO sales.listing (
    product_id, platform_id, size_id, listing_price,
    external_listing_id, platform_specific_data
) VALUES (
    1,
    (SELECT id FROM platform.marketplace WHERE name = 'Alias'),
    10,
    185.00,
    'alias-def456',
    '{
        "reserve_price": 170.00,
        "auction_type": "silent",
        "listing_duration_hours": 48,
        "verification_status": "authenticated"
    }'::jsonb
);

-- ============================================================================
-- QUERYING PLATFORM-SPECIFIC DATA
-- ============================================================================

-- Query 1: Find all StockX instant consignment listings
SELECT
    l.id,
    l.listing_price,
    l.platform_specific_data->>'ask_price' as ask_price,
    l.platform_specific_data->>'bid_price' as bid_price
FROM sales.listing l
JOIN platform.marketplace p ON l.platform_id = p.id
WHERE p.name = 'StockX'
  AND l.platform_specific_data->>'consignment_type' = 'instant';

-- Query 2: Find all eBay auctions ending today
SELECT
    l.id,
    l.external_listing_id,
    l.listing_price,
    (l.platform_specific_data->>'auction_end_date')::timestamptz as ends_at
FROM sales.listing l
JOIN platform.marketplace p ON l.platform_id = p.id
WHERE p.name = 'eBay'
  AND (l.platform_specific_data->>'auction_end_date')::timestamptz < now() + interval '1 day';

-- Query 3: Find all GOAT instant ship products
SELECT
    l.id,
    cat.name as product_name,
    l.listing_price,
    l.platform_specific_data->>'condition_grade' as condition
FROM sales.listing l
JOIN catalog.product cat ON l.product_id = cat.id
JOIN platform.marketplace p ON l.platform_id = p.id
WHERE p.name = 'GOAT'
  AND (l.platform_specific_data->>'instant_ship')::boolean = true;

-- Query 4: Cross-platform price comparison
SELECT
    p.name as platform,
    COUNT(*) as total_listings,
    AVG(l.listing_price) as avg_price,
    MIN(l.listing_price) as min_price,
    MAX(l.listing_price) as max_price
FROM sales.listing l
JOIN platform.marketplace p ON l.platform_id = p.id
WHERE l.product_id = 1
  AND l.status = 'active'
GROUP BY p.name
ORDER BY avg_price;

-- ============================================================================
-- DOMAIN STRUCTURE AFTER MIGRATION
-- ============================================================================

-- SALES Domain (3 tables) - Sales/Marketing Team
-- ├── listing              ← Unified multi-platform listings
-- ├── order                ← Unified multi-platform orders
-- └── pricing_history      ← Price change tracking

-- FINANCIAL Domain (4 tables) - Finance/Accounting Team
-- ├── transaction          ← Financial settlements/payments
-- ├── product_price_snapshot
-- ├── supplier_contract
-- └── supplier_rating_history

-- PLATFORM Domain (remains unchanged)
-- ├── marketplace          ← Platform registry (StockX, eBay, GOAT, Alias, etc.)
-- ├── fee
-- ├── integration
-- └── size_display

-- ============================================================================
-- BENEFITS OF UNIFIED PATTERN
-- ============================================================================

-- ✅ Scalability
--    - Add new platforms (Alias, Grailed, etc.) without schema changes
--    - Just insert new row in platform.marketplace and start using

-- ✅ Consistency
--    - Single source of truth for all listings/orders
--    - Unified reporting and analytics

-- ✅ Performance
--    - GIN indexes make JSONB queries fast
--    - PostgreSQL JSONB is optimized for this use case

-- ✅ Flexibility
--    - Platform-specific fields can evolve independently
--    - No ALTER TABLE migrations for platform changes

-- ✅ Development Speed
--    - One code path for all platforms
--    - Easier testing and maintenance

-- ============================================================================
-- FINAL COUNTS
-- ============================================================================

-- After this migration:
-- - catalog: 6 tables
-- - inventory: 4 tables
-- - sales: 3 tables (listing, order, pricing_history)
-- - financial: 4 tables (transaction + 3 existing)
-- - product: 2 tables
-- - core: 6 tables
-- - supplier: 3 tables
-- - analytics: 9 tables
-- - pricing: 7 tables
-- - platform: 4 tables
-- - integration: 4 tables
-- - operations: 3 tables
-- - logging: 3 tables
-- - compliance: 3 tables
-- - realtime: 1 table
-- TOTAL: 62 tables (down from 64 - eliminated 2 platform-specific tables)

-- transaction schema eliminated (was 4 tables, now distributed to sales/financial)

-- ============================================================================
-- NOTE
-- ============================================================================

-- This migration has been applied to the running database.
-- This file documents the changes for:
-- 1. Schema recreation (update init-databases.sql)
-- 2. Alembic migration generation
-- 3. Platform expansion guide (how to add new marketplaces)

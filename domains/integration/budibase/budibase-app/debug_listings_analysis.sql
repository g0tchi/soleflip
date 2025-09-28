-- =====================================================
-- LISTINGS ANALYSIS - Understanding the Data Structure
-- =====================================================

-- 1. Check products.listings table content
-- Query Name: debug_listings_table
SELECT
    COUNT(*) as total_listings,
    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_listings,
    MIN(created_at) as oldest_listing,
    MAX(created_at) as newest_listing,
    ARRAY_AGG(DISTINCT status) as all_statuses
FROM products.listings;

-- 2. Sample of listings data
-- Query Name: debug_listings_sample
SELECT
    l.id,
    l.stockx_listing_id,
    l.status,
    l.amount,
    l.created_at,
    p.name as product_name,
    i.status as inventory_status,
    i.supplier as data_source
FROM products.listings l
LEFT JOIN products.inventory i ON l.inventory_item_id = i.id
LEFT JOIN products.products p ON i.product_id = p.id
ORDER BY l.created_at DESC
LIMIT 10;

-- 3. Inventory items marked as "listed" vs actual listings table
-- Query Name: debug_listed_vs_listings
SELECT
    'Inventory with status=listed' as source,
    COUNT(*) as count,
    NULL as avg_amount
FROM products.inventory
WHERE status = 'listed'

UNION ALL

SELECT
    'Actual listings table' as source,
    COUNT(*) as count,
    AVG(amount) as avg_amount
FROM products.listings
WHERE status = 'active';

-- 4. Connection between inventory and listings
-- Query Name: debug_inventory_listings_connection
SELECT
    i.status as inventory_status,
    COUNT(i.id) as inventory_count,
    COUNT(l.id) as listings_count,
    ROUND(COUNT(l.id) * 100.0 / NULLIF(COUNT(i.id), 0), 2) as listing_percentage
FROM products.inventory i
LEFT JOIN products.listings l ON i.id = l.inventory_item_id
GROUP BY i.status
ORDER BY inventory_count DESC;

-- 5. StockX listings performance
-- Query Name: debug_stockx_listings_performance
SELECT
    l.status,
    COUNT(*) as listing_count,
    AVG(l.amount) as avg_price,
    MIN(l.amount) as min_price,
    MAX(l.amount) as max_price,
    COUNT(CASE WHEN l.expires_at > NOW() THEN 1 END) as active_unexpired
FROM products.listings l
WHERE l.stockx_listing_id IS NOT NULL
GROUP BY l.status
ORDER BY listing_count DESC;
-- =====================================================
-- STOCKX LISTINGS ANALYTICS - Real Active Listings
-- Based on 39 active StockX listings found via API
-- =====================================================

-- 1. Active StockX Listings Overview
-- Query Name: stockx_listings_overview
SELECT
    COUNT(*) as total_active_listings,
    AVG(amount::numeric) as avg_asking_price,
    MIN(amount::numeric) as lowest_ask,
    MAX(amount::numeric) as highest_ask,
    SUM(amount::numeric) as total_listing_value,
    COUNT(CASE WHEN amount::numeric > 100 THEN 1 END) as premium_listings,
    COUNT(CASE WHEN amount::numeric < 50 THEN 1 END) as budget_listings
FROM products.listings
WHERE status = 'ACTIVE';

-- 2. StockX Listings by Price Range
-- Query Name: stockx_price_ranges
SELECT
    CASE
        WHEN amount::numeric < 50 THEN 'Under €50'
        WHEN amount::numeric < 100 THEN '€50-€100'
        WHEN amount::numeric < 200 THEN '€100-€200'
        WHEN amount::numeric < 300 THEN '€200-€300'
        ELSE '€300+'
    END as price_range,
    COUNT(*) as listing_count,
    AVG(amount::numeric) as avg_price,
    SUM(amount::numeric) as total_value,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM products.listings l
WHERE l.status = 'ACTIVE'
GROUP BY
    CASE
        WHEN amount::numeric < 50 THEN 'Under €50'
        WHEN amount::numeric < 100 THEN '€50-€100'
        WHEN amount::numeric < 200 THEN '€100-€200'
        WHEN amount::numeric < 300 THEN '€200-€300'
        ELSE '€300+'
    END
ORDER BY avg_price;

-- 3. Top StockX Listings by Value
-- Query Name: stockx_top_listings
SELECT
    l.stockx_listing_id,
    l.amount::numeric as asking_price,
    p.name as product_name,
    i.status as inventory_status,
    l.created_at as listed_date,
    EXTRACT(days FROM NOW() - l.created_at) as days_listed,
    l.expires_at as expires_date,
    CASE
        WHEN l.expires_at < NOW() THEN 'Expired'
        WHEN l.expires_at < NOW() + INTERVAL '7 days' THEN 'Expiring Soon'
        ELSE 'Active'
    END as listing_status
FROM products.listings l
LEFT JOIN products.inventory i ON l.inventory_item_id = i.id
LEFT JOIN products.products p ON i.product_id = p.id
WHERE l.status = 'ACTIVE'
ORDER BY l.amount::numeric DESC
LIMIT 15;

-- 4. StockX Listings Performance by Age
-- Query Name: stockx_listings_by_age
SELECT
    CASE
        WHEN l.created_at > NOW() - INTERVAL '7 days' THEN 'Listed This Week'
        WHEN l.created_at > NOW() - INTERVAL '30 days' THEN 'Listed This Month'
        WHEN l.created_at > NOW() - INTERVAL '90 days' THEN 'Listed Last 3 Months'
        ELSE 'Older Listings'
    END as age_category,
    COUNT(*) as listing_count,
    AVG(amount::numeric) as avg_price,
    MIN(amount::numeric) as min_price,
    MAX(amount::numeric) as max_price
FROM products.listings l
WHERE l.status = 'ACTIVE'
GROUP BY
    CASE
        WHEN l.created_at > NOW() - INTERVAL '7 days' THEN 'Listed This Week'
        WHEN l.created_at > NOW() - INTERVAL '30 days' THEN 'Listed This Month'
        WHEN l.created_at > NOW() - INTERVAL '90 days' THEN 'Listed Last 3 Months'
        ELSE 'Older Listings'
    END
ORDER BY avg_price DESC;

-- 5. Brand Performance on StockX
-- Query Name: stockx_brand_performance
SELECT
    b.name as brand_name,
    COUNT(l.id) as active_listings,
    AVG(l.amount::numeric) as avg_asking_price,
    MIN(l.amount::numeric) as lowest_ask,
    MAX(l.amount::numeric) as highest_ask,
    SUM(l.amount::numeric) as total_listing_value
FROM products.listings l
LEFT JOIN products.inventory i ON l.inventory_item_id = i.id
LEFT JOIN products.products p ON i.product_id = p.id
LEFT JOIN core.brands b ON p.brand_id = b.id
WHERE l.status = 'ACTIVE' AND b.name IS NOT NULL
GROUP BY b.name
ORDER BY total_listing_value DESC;

-- 6. Inventory vs Listings Connection
-- Query Name: inventory_vs_listings_status
SELECT
    i.status as inventory_status,
    COUNT(i.id) as inventory_count,
    COUNT(l.id) as listings_count,
    AVG(l.amount::numeric) as avg_listing_price,
    ROUND(COUNT(l.id) * 100.0 / NULLIF(COUNT(i.id), 0), 2) as listing_rate_percentage
FROM products.inventory i
LEFT JOIN products.listings l ON i.id = l.inventory_item_id AND l.status = 'ACTIVE'
GROUP BY i.status
ORDER BY inventory_count DESC;

-- 7. Expiring StockX Listings (Next 30 days)
-- Query Name: stockx_expiring_listings
SELECT
    l.stockx_listing_id,
    p.name as product_name,
    l.amount::numeric as asking_price,
    l.expires_at as expires_date,
    EXTRACT(days FROM l.expires_at - NOW()) as days_until_expiry,
    l.created_at as listed_date,
    EXTRACT(days FROM NOW() - l.created_at) as days_listed
FROM products.listings l
LEFT JOIN products.inventory i ON l.inventory_item_id = i.id
LEFT JOIN products.products p ON i.product_id = p.id
WHERE l.status = 'ACTIVE'
    AND l.expires_at < NOW() + INTERVAL '30 days'
ORDER BY l.expires_at ASC
LIMIT 20;

-- 8. StockX Revenue Potential
-- Query Name: stockx_revenue_potential
SELECT
    'Active Listings' as metric,
    COUNT(*) as count,
    SUM(amount::numeric) as total_potential_revenue,
    AVG(amount::numeric) as avg_price,
    MIN(amount::numeric) as min_price,
    MAX(amount::numeric) as max_price
FROM products.listings
WHERE status = 'ACTIVE'

UNION ALL

SELECT
    'Premium Listings (€200+)' as metric,
    COUNT(*) as count,
    SUM(amount::numeric) as total_potential_revenue,
    AVG(amount::numeric) as avg_price,
    MIN(amount::numeric) as min_price,
    MAX(amount::numeric) as max_price
FROM products.listings
WHERE status = 'ACTIVE' AND amount::numeric >= 200;

-- =====================================================
-- USAGE NOTES
-- =====================================================

/*
STOCKX LISTINGS INSIGHTS:
- 39 active listings discovered via API
- Price range: €24 - €385
- Categories: Sneakers, Apparel, Collectibles
- Total potential revenue if all sell: Sum of all asking prices

KEY METRICS TO TRACK:
1. Listing performance by price range
2. Brand performance on StockX
3. Days to sell / listing age analysis
4. Expiry management for renewals
5. Inventory utilization rate (listed vs available)

DASHBOARD RECOMMENDATIONS:
- Price distribution chart
- Top performing brands
- Expiring listings alerts
- Revenue potential KPI cards
*/
-- =====================================================
-- SoleFlipper Budibase PostgreSQL Queries - SIMPLIFIED
-- No Parameters Version for Immediate Use
-- All queries work without parameter binding
-- =====================================================

-- =====================================================
-- 1. DASHBOARD OVERVIEW
-- =====================================================

-- Dashboard Overview KPIs
-- Query Name: inventory_overview
SELECT
    COUNT(*) as total_items,
    COUNT(CASE WHEN i.status = 'listed' THEN 1 END) as listed_items,
    COUNT(CASE WHEN i.status = 'sold' THEN 1 END) as sold_items,
    COUNT(CASE WHEN i.status = 'pending' THEN 1 END) as pending_items,
    SUM(i.purchase_price * i.quantity) as total_inventory_value,
    AVG(i.purchase_price) as avg_item_price,
    COUNT(DISTINCT b.name) as unique_brands,
    COUNT(DISTINCT s.value) as unique_sizes
FROM products.inventory i
LEFT JOIN products.products p ON i.product_id = p.id
LEFT JOIN core.brands b ON p.brand_id = b.id
LEFT JOIN core.sizes s ON i.size_id = s.id
WHERE i.created_at >= CURRENT_DATE - INTERVAL '1 year';

-- =====================================================
-- 2. INVENTORY LISTINGS
-- =====================================================

-- All Inventory Items (Latest 100)
-- Query Name: inventory_latest
SELECT
    i.id,
    i.product_id,
    p.name as product_name,
    b.name as brand_name,
    c.name as category_name,
    s.value as size,
    i.quantity,
    i.purchase_price,
    i.status,
    i.supplier,
    i.created_at,
    i.updated_at,
    EXTRACT(days FROM NOW() - i.created_at) as days_in_stock,
    CASE
        WHEN i.created_at > NOW() - INTERVAL '7 days' THEN 'New'
        WHEN i.created_at > NOW() - INTERVAL '30 days' THEN 'Recent'
        WHEN i.created_at > NOW() - INTERVAL '90 days' THEN 'Old'
        ELSE 'Dead Stock'
    END as stock_category
FROM products.inventory i
LEFT JOIN products.products p ON i.product_id = p.id
LEFT JOIN core.brands b ON p.brand_id = b.id
LEFT JOIN core.categories c ON p.category_id = c.id
LEFT JOIN core.sizes s ON i.size_id = s.id
ORDER BY i.created_at DESC
LIMIT 100;

-- Active Listings Only
-- Query Name: inventory_active
SELECT
    i.id,
    p.name as product_name,
    b.name as brand_name,
    s.value as size,
    i.purchase_price,
    i.status,
    i.created_at,
    EXTRACT(days FROM NOW() - i.created_at) as days_in_stock
FROM products.inventory i
LEFT JOIN products.products p ON i.product_id = p.id
LEFT JOIN core.brands b ON p.brand_id = b.id
LEFT JOIN core.sizes s ON i.size_id = s.id
WHERE i.status = 'listed'
ORDER BY i.created_at DESC
LIMIT 50;

-- =====================================================
-- 3. BRAND ANALYTICS
-- =====================================================

-- Brand Performance Analysis
-- Query Name: brand_analytics
SELECT
    b.name as brand_name,
    COUNT(*) as total_items,
    COUNT(CASE WHEN i.status = 'listed' THEN 1 END) as listed_count,
    COUNT(CASE WHEN i.status = 'sold' THEN 1 END) as sold_count,
    SUM(i.quantity) as total_quantity,
    AVG(i.purchase_price) as avg_purchase_price,
    MIN(i.purchase_price) as min_price,
    MAX(i.purchase_price) as max_price,
    SUM(i.purchase_price * i.quantity) as total_value,
    ROUND(AVG(EXTRACT(days FROM NOW() - i.created_at)), 1) as avg_days_in_stock
FROM products.inventory i
LEFT JOIN products.products p ON i.product_id = p.id
LEFT JOIN core.brands b ON p.brand_id = b.id
WHERE b.name IS NOT NULL
GROUP BY b.name
HAVING COUNT(*) >= 3  -- Only brands with 3+ items
ORDER BY total_value DESC;

-- Top 10 Brands by Value
-- Query Name: top_brands
SELECT
    b.name as brand_name,
    COUNT(*) as total_items,
    SUM(i.purchase_price * i.quantity) as total_value,
    AVG(i.purchase_price) as avg_price
FROM products.inventory i
LEFT JOIN products.products p ON i.product_id = p.id
LEFT JOIN core.brands b ON p.brand_id = b.id
WHERE b.name IS NOT NULL
GROUP BY b.name
ORDER BY total_value DESC
LIMIT 10;

-- =====================================================
-- 4. SIZE ANALYTICS
-- =====================================================

-- Size Distribution Analysis
-- Query Name: size_distribution
SELECT
    s.value as size,
    COUNT(*) as item_count,
    COUNT(CASE WHEN i.status = 'listed' THEN 1 END) as available_count,
    AVG(i.purchase_price) as avg_price,
    SUM(i.purchase_price * i.quantity) as total_value,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage_of_total
FROM products.inventory i
LEFT JOIN core.sizes s ON i.size_id = s.id
WHERE s.value IS NOT NULL
GROUP BY s.value
ORDER BY item_count DESC
LIMIT 20;

-- =====================================================
-- 5. DEAD STOCK & ALERTS
-- =====================================================

-- Dead Stock Analysis (Items older than 90 days)
-- Query Name: dead_stock_analysis
SELECT
    p.name as product_name,
    b.name as brand_name,
    s.value as size,
    i.purchase_price,
    i.quantity,
    i.purchase_price * i.quantity as total_value,
    i.created_at,
    EXTRACT(days FROM NOW() - i.created_at) as days_in_stock,
    i.supplier,
    i.status
FROM products.inventory i
LEFT JOIN products.products p ON i.product_id = p.id
LEFT JOIN core.brands b ON p.brand_id = b.id
LEFT JOIN core.sizes s ON i.size_id = s.id
WHERE i.status = 'listed'
    AND i.created_at < NOW() - INTERVAL '90 days'
ORDER BY days_in_stock DESC
LIMIT 50;

-- High Value Items (Over $200)
-- Query Name: high_value_items
SELECT
    p.name as product_name,
    b.name as brand_name,
    s.value as size,
    i.purchase_price,
    i.status,
    i.created_at
FROM products.inventory i
LEFT JOIN products.products p ON i.product_id = p.id
LEFT JOIN core.brands b ON p.brand_id = b.id
LEFT JOIN core.sizes s ON i.size_id = s.id
WHERE i.purchase_price > 200
    AND i.status = 'listed'
ORDER BY i.purchase_price DESC
LIMIT 30;

-- =====================================================
-- 6. FINANCIAL ANALYTICS
-- =====================================================

-- Monthly Financial Summary (Last 12 Months)
-- Query Name: monthly_financial_summary
SELECT
    DATE_TRUNC('month', i.created_at) as month,
    COUNT(*) as items_acquired,
    SUM(i.purchase_price * i.quantity) as total_invested,
    AVG(i.purchase_price) as avg_purchase_price,
    COUNT(DISTINCT b.name) as brands_acquired,
    SUM(CASE WHEN i.status = 'sold' THEN i.purchase_price * i.quantity ELSE 0 END) as sold_value,
    SUM(CASE WHEN i.status = 'listed' THEN i.purchase_price * i.quantity ELSE 0 END) as inventory_value
FROM products.inventory i
LEFT JOIN products.products p ON i.product_id = p.id
LEFT JOIN core.brands b ON p.brand_id = b.id
WHERE i.created_at >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '12 months')
GROUP BY DATE_TRUNC('month', i.created_at)
ORDER BY month DESC;

-- Price Range Analysis
-- Query Name: price_range_analysis
SELECT
    price_range,
    item_count,
    total_quantity,
    total_value,
    avg_price,
    percentage,
    sort_order
FROM (
    SELECT
        CASE
            WHEN i.purchase_price < 50 THEN 'Under $50'
            WHEN i.purchase_price < 100 THEN '$50-$100'
            WHEN i.purchase_price < 200 THEN '$100-$200'
            WHEN i.purchase_price < 500 THEN '$200-$500'
            ELSE '$500+'
        END as price_range,
        COUNT(*) as item_count,
        SUM(i.quantity) as total_quantity,
        SUM(i.purchase_price * i.quantity) as total_value,
        AVG(i.purchase_price) as avg_price,
        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage,
        CASE
            WHEN i.purchase_price < 50 THEN 1
            WHEN i.purchase_price < 100 THEN 2
            WHEN i.purchase_price < 200 THEN 3
            WHEN i.purchase_price < 500 THEN 4
            ELSE 5
        END as sort_order
    FROM products.inventory i
    GROUP BY
        CASE
            WHEN i.purchase_price < 50 THEN 'Under $50'
            WHEN i.purchase_price < 100 THEN '$50-$100'
            WHEN i.purchase_price < 200 THEN '$100-$200'
            WHEN i.purchase_price < 500 THEN '$200-$500'
            ELSE '$500+'
        END,
        CASE
            WHEN i.purchase_price < 50 THEN 1
            WHEN i.purchase_price < 100 THEN 2
            WHEN i.purchase_price < 200 THEN 3
            WHEN i.purchase_price < 500 THEN 4
            ELSE 5
        END
) grouped_data
ORDER BY sort_order;

-- =====================================================
-- 7. SUPPLIER ANALYTICS
-- =====================================================

-- Data Source Performance (Import Origins)
-- Query Name: data_source_performance
SELECT
    i.supplier as data_source,
    COUNT(*) as total_items,
    COUNT(CASE WHEN i.status = 'listed' THEN 1 END) as active_items,
    COUNT(CASE WHEN i.status = 'sold' THEN 1 END) as sold_items,
    SUM(i.purchase_price * i.quantity) as total_invested,
    AVG(i.purchase_price) as avg_price,
    MIN(i.created_at) as first_import,
    MAX(i.created_at) as last_import,
    COUNT(DISTINCT b.name) as brands_from_source
FROM products.inventory i
LEFT JOIN products.products p ON i.product_id = p.id
LEFT JOIN core.brands b ON p.brand_id = b.id
WHERE i.supplier IS NOT NULL
GROUP BY i.supplier
ORDER BY total_invested DESC;

-- =====================================================
-- 8. RECENT ACTIVITY
-- =====================================================

-- Recent Activity (Last 7 days)
-- Query Name: recent_activity
SELECT
    p.name as product_name,
    b.name as brand_name,
    s.value as size,
    i.purchase_price,
    i.status,
    i.created_at,
    'Added to inventory' as activity_type
FROM products.inventory i
LEFT JOIN products.products p ON i.product_id = p.id
LEFT JOIN core.brands b ON p.brand_id = b.id
LEFT JOIN core.sizes s ON i.size_id = s.id
WHERE i.created_at >= NOW() - INTERVAL '7 days'
ORDER BY i.created_at DESC
LIMIT 50;

-- Status Changes (Last 7 days)
-- Query Name: recent_status_changes
SELECT
    p.name as product_name,
    b.name as brand_name,
    s.value as size,
    i.purchase_price,
    i.status,
    i.updated_at,
    'Status updated' as activity_type
FROM products.inventory i
LEFT JOIN products.products p ON i.product_id = p.id
LEFT JOIN core.brands b ON p.brand_id = b.id
LEFT JOIN core.sizes s ON i.size_id = s.id
WHERE i.updated_at >= NOW() - INTERVAL '7 days'
    AND i.updated_at != i.created_at
ORDER BY i.updated_at DESC
LIMIT 30;

-- =====================================================
-- 9. FILTER HELPERS
-- =====================================================

-- Get all unique brands for dropdowns
-- Query Name: get_brands
SELECT DISTINCT b.name as brand_name
FROM products.inventory i
LEFT JOIN products.products p ON i.product_id = p.id
LEFT JOIN core.brands b ON p.brand_id = b.id
WHERE b.name IS NOT NULL
ORDER BY b.name;

-- Get all unique sizes for dropdowns
-- Query Name: get_sizes
SELECT
    size
FROM (
    SELECT DISTINCT
        s.value as size,
        CASE
            WHEN s.value ~ '^[0-9]+(\\.[0-9]+)?$' THEN s.value::numeric
            ELSE 999
        END as sort_order
    FROM products.inventory i
    LEFT JOIN core.sizes s ON i.size_id = s.id
    WHERE s.value IS NOT NULL
) unique_sizes
ORDER BY sort_order, size;

-- Get all statuses for dropdowns
-- Query Name: get_statuses
SELECT DISTINCT i.status
FROM products.inventory i
WHERE i.status IS NOT NULL
ORDER BY i.status;

-- =====================================================
-- 10. QUICK TESTS
-- =====================================================

-- Test basic inventory access
-- Query Name: test_basic_inventory
SELECT COUNT(*) as total_count FROM products.inventory;

-- Test with joins (5 sample records)
-- Query Name: test_inventory_sample
SELECT
    i.id,
    p.name as product_name,
    b.name as brand,
    s.value as size,
    i.purchase_price,
    i.status
FROM products.inventory i
LEFT JOIN products.products p ON i.product_id = p.id
LEFT JOIN core.brands b ON p.brand_id = b.id
LEFT JOIN core.sizes s ON i.size_id = s.id
LIMIT 5;

-- =====================================================
-- USAGE NOTES
-- =====================================================

/*
SIMPLIFIED VERSION BENEFITS:
- No parameter binding issues
- Immediate use in Budibase
- All queries work out-of-the-box
- Performance optimized for 2,310+ items

SCHEMA ACCESS:
- Set Schema to: products
- Queries auto-join to core schema tables
- All relationships properly resolved

NEXT STEPS:
1. Test each query individually in Budibase
2. Create dashboard components
3. Add filters via Budibase UI components
4. Customize LIMIT values as needed
*/
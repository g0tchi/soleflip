-- =====================================================
-- SoleFlipper Budibase PostgreSQL Queries - CORRECTED
-- Direct Database Access for Optimal Performance
-- Fixed for actual schema: products.inventory (not inventory.items)
-- =====================================================

-- =====================================================
-- 1. INVENTORY MANAGEMENT QUERIES
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

-- Inventory Items List with Filters
-- Query Name: inventory_items_filtered
-- Parameters: $1=brand_filter, $2=status_filter, $3=size_filter, $4=search_query, $5=limit_count, $6=offset_count
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
WHERE
    ($1::text IS NULL OR b.name = $1)
    AND ($2::text IS NULL OR i.status = $2)
    AND ($3::text IS NULL OR s.value = $3)
    AND ($4::text IS NULL OR
         p.name ILIKE '%' || $4 || '%' OR
         b.name ILIKE '%' || $4 || '%')
ORDER BY i.created_at DESC
LIMIT COALESCE($5::int, 50)
OFFSET COALESCE($6::int, 0);

-- =====================================================
-- 2. ANALYTICS & REPORTING QUERIES
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
HAVING COUNT(*) >= 5  -- Only brands with 5+ items
ORDER BY total_value DESC;

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
ORDER BY
    CASE
        WHEN s.value ~ '^[0-9]+(\.[0-9]+)?$' THEN s.value::numeric
        ELSE 999
    END,
    s.value;

-- Daily Inventory Trends (Last 30 Days)
-- Query Name: inventory_trends
SELECT
    DATE(i.created_at) as date,
    COUNT(*) as items_added,
    SUM(i.purchase_price * i.quantity) as daily_value_added,
    COUNT(DISTINCT b.name) as brands_added,
    AVG(i.purchase_price) as avg_daily_price
FROM products.inventory i
LEFT JOIN products.products p ON i.product_id = p.id
LEFT JOIN core.brands b ON p.brand_id = b.id
WHERE i.created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(i.created_at)
ORDER BY date;

-- =====================================================
-- 3. DEAD STOCK & PERFORMANCE ANALYSIS
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
ORDER BY days_in_stock DESC, total_value DESC;

-- Fast Moving Items (if you have sales data)
-- Query Name: fast_moving_items
-- Note: This assumes you have transaction/order data
SELECT
    p.name as product_name,
    b.name as brand_name,
    s.value as size,
    i.purchase_price,
    COUNT(t.*) as times_sold,
    AVG(EXTRACT(days FROM t.created_at - i.created_at)) as avg_days_to_sell
FROM products.inventory i
LEFT JOIN products.products p ON i.product_id = p.id
LEFT JOIN core.brands b ON p.brand_id = b.id
LEFT JOIN core.sizes s ON i.size_id = s.id
LEFT JOIN transactions.transactions t ON i.id = t.inventory_id
WHERE t.created_at >= NOW() - INTERVAL '30 days'
    AND i.status = 'sold'
GROUP BY p.name, b.name, s.value, i.purchase_price
HAVING COUNT(t.*) > 1
ORDER BY times_sold DESC, avg_days_to_sell ASC;

-- =====================================================
-- 4. FINANCIAL ANALYTICS
-- =====================================================

-- Monthly Financial Summary
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
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM products.inventory i
GROUP BY
    CASE
        WHEN i.purchase_price < 50 THEN 'Under $50'
        WHEN i.purchase_price < 100 THEN '$50-$100'
        WHEN i.purchase_price < 200 THEN '$100-$200'
        WHEN i.purchase_price < 500 THEN '$200-$500'
        ELSE '$500+'
    END
ORDER BY
    CASE
        WHEN i.purchase_price < 50 THEN 1
        WHEN i.purchase_price < 100 THEN 2
        WHEN i.purchase_price < 200 THEN 3
        WHEN i.purchase_price < 500 THEN 4
        ELSE 5
    END;

-- =====================================================
-- 5. SUPPLIER ANALYSIS
-- =====================================================

-- Supplier Performance
-- Query Name: supplier_performance
SELECT
    i.supplier,
    COUNT(*) as total_items,
    COUNT(CASE WHEN i.status = 'listed' THEN 1 END) as active_items,
    COUNT(CASE WHEN i.status = 'sold' THEN 1 END) as sold_items,
    SUM(i.purchase_price * i.quantity) as total_invested,
    AVG(i.purchase_price) as avg_price,
    MIN(i.created_at) as first_purchase,
    MAX(i.created_at) as last_purchase,
    COUNT(DISTINCT b.name) as brands_supplied
FROM products.inventory i
LEFT JOIN products.products p ON i.product_id = p.id
LEFT JOIN core.brands b ON p.brand_id = b.id
WHERE i.supplier IS NOT NULL
GROUP BY i.supplier
ORDER BY total_invested DESC;

-- =====================================================
-- 6. SEARCH & FILTER HELPERS
-- =====================================================

-- Get all unique brands for filter dropdown
-- Query Name: get_brands
SELECT DISTINCT b.name as brand_name
FROM products.inventory i
LEFT JOIN products.products p ON i.product_id = p.id
LEFT JOIN core.brands b ON p.brand_id = b.id
WHERE b.name IS NOT NULL
ORDER BY b.name;

-- Get all unique sizes for filter dropdown
-- Query Name: get_sizes
SELECT DISTINCT s.value as size
FROM products.inventory i
LEFT JOIN core.sizes s ON i.size_id = s.id
WHERE s.value IS NOT NULL
ORDER BY
    CASE
        WHEN s.value ~ '^[0-9]+(\.[0-9]+)?$' THEN s.value::numeric
        ELSE 999
    END,
    s.value;

-- Get all statuses for filter dropdown
-- Query Name: get_statuses
SELECT DISTINCT i.status
FROM products.inventory i
WHERE i.status IS NOT NULL
ORDER BY i.status;

-- =====================================================
-- 7. REAL-TIME MONITORING
-- =====================================================

-- Recent Activity (Last 24 hours)
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
WHERE i.created_at >= NOW() - INTERVAL '24 hours'
UNION ALL
SELECT
    p.name as product_name,
    b.name as brand_name,
    s.value as size,
    i.purchase_price,
    i.status,
    i.updated_at as created_at,
    'Status updated' as activity_type
FROM products.inventory i
LEFT JOIN products.products p ON i.product_id = p.id
LEFT JOIN core.brands b ON p.brand_id = b.id
LEFT JOIN core.sizes s ON i.size_id = s.id
WHERE i.updated_at >= NOW() - INTERVAL '24 hours'
    AND i.updated_at != i.created_at
ORDER BY created_at DESC
LIMIT 50;

-- Inventory Alerts
-- Query Name: inventory_alerts
SELECT
    'Dead Stock Alert' as alert_type,
    COUNT(*) as count,
    'Items older than 90 days' as description
FROM products.inventory i
WHERE i.status = 'listed' AND i.created_at < NOW() - INTERVAL '90 days'
UNION ALL
SELECT
    'Low Stock Alert' as alert_type,
    COUNT(*) as count,
    'Items with quantity = 1' as description
FROM products.inventory i
WHERE i.quantity = 1 AND i.status = 'listed'
UNION ALL
SELECT
    'High Value Items' as alert_type,
    COUNT(*) as count,
    'Items over $500' as description
FROM products.inventory i
WHERE i.purchase_price > 500 AND i.status = 'listed';

-- =====================================================
-- 8. SIMPLE TEST QUERIES FOR VERIFICATION
-- =====================================================

-- Test basic inventory access
-- Query Name: test_basic_inventory
SELECT COUNT(*) as total_count FROM products.inventory;

-- Test with joins
-- Query Name: test_inventory_with_details
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
-- USAGE NOTES FOR BUDIBASE
-- =====================================================

/*
CORRECTED SCHEMA STRUCTURE:
- Main inventory table: products.inventory
- Product details: products.products
- Size information: core.sizes
- Brand information: stored in products.brand field

PARAMETER SYNTAX FOR BUDIBASE:
- Use $1, $2, $3 etc. for parameterized queries
- Not {{parameter}} syntax (that was wrong)

EXAMPLE BUDIBASE DATA SOURCE CONFIG:
- Host: postgres
- Port: 5432
- Database: soleflip
- Schema: public (Budibase will see all schemas)
- User: your_db_user
- Password: your_db_password

PERFORMANCE TIPS:
- These queries use LEFT JOINs for safety
- Indexes should exist on: product_id, size_id, status, created_at
- For large datasets, add LIMIT clauses
*/
-- =====================================================
-- SoleFlipper Business Intelligence Views
-- Optimized Database Views for Budibase Dashboards
-- =====================================================

-- =====================================================
-- 1. MAIN DASHBOARD VIEW
-- =====================================================

-- Primary dashboard view with all key metrics
CREATE OR REPLACE VIEW budibase_dashboard_overview AS
SELECT
    -- Inventory Metrics
    (SELECT COUNT(*) FROM inventory.items) as total_inventory_items,
    (SELECT COUNT(*) FROM inventory.items WHERE status = 'listed') as active_listings,
    (SELECT COUNT(*) FROM inventory.items WHERE status = 'sold') as sold_items,
    (SELECT COUNT(*) FROM inventory.items WHERE created_at >= CURRENT_DATE - INTERVAL '7 days') as new_items_week,

    -- Financial Metrics
    (SELECT COALESCE(SUM(purchase_price * quantity), 0) FROM inventory.items WHERE status = 'listed') as total_inventory_value,
    (SELECT COALESCE(AVG(purchase_price), 0) FROM inventory.items WHERE status = 'listed') as avg_item_value,
    (SELECT COALESCE(SUM(purchase_price * quantity), 0) FROM inventory.items WHERE created_at >= CURRENT_DATE - INTERVAL '30 days') as monthly_investment,

    -- Performance Metrics
    (SELECT COUNT(DISTINCT brand_name) FROM inventory.items) as total_brands,
    (SELECT COUNT(DISTINCT size) FROM inventory.items) as total_sizes,
    (SELECT COUNT(*) FROM inventory.items WHERE created_at < CURRENT_DATE - INTERVAL '90 days' AND status = 'listed') as dead_stock_count,

    -- Recent Activity
    (SELECT COUNT(*) FROM inventory.items WHERE created_at >= CURRENT_DATE - INTERVAL '24 hours') as items_added_today,
    (SELECT COUNT(*) FROM inventory.items WHERE updated_at >= CURRENT_DATE - INTERVAL '24 hours' AND updated_at != created_at) as items_updated_today,

    -- Top Performers
    (SELECT brand_name FROM inventory.items GROUP BY brand_name ORDER BY COUNT(*) DESC LIMIT 1) as top_brand_by_count,
    (SELECT brand_name FROM inventory.items WHERE status = 'listed' GROUP BY brand_name ORDER BY SUM(purchase_price * quantity) DESC LIMIT 1) as top_brand_by_value,

    -- Alerts
    (SELECT COUNT(*) FROM inventory.items WHERE purchase_price > 500 AND status = 'listed') as high_value_items,
    (SELECT COUNT(*) FROM inventory.items WHERE quantity = 1 AND status = 'listed') as low_stock_items;

-- =====================================================
-- 2. INVENTORY ANALYTICS VIEW
-- =====================================================

-- Comprehensive inventory view with calculated fields
CREATE OR REPLACE VIEW budibase_inventory_analytics AS
SELECT
    i.id,
    i.product_id,
    i.product_name,
    i.brand_name,
    i.category_name,
    i.size,
    i.quantity,
    i.purchase_price,
    i.purchase_price * i.quantity as total_value,
    i.status,
    i.supplier,
    i.created_at,
    i.updated_at,

    -- Calculated Analytics Fields
    EXTRACT(days FROM NOW() - i.created_at) as days_in_stock,

    -- Stock Age Categories
    CASE
        WHEN i.created_at > NOW() - INTERVAL '7 days' THEN 'New (< 7 days)'
        WHEN i.created_at > NOW() - INTERVAL '30 days' THEN 'Recent (7-30 days)'
        WHEN i.created_at > NOW() - INTERVAL '90 days' THEN 'Old (30-90 days)'
        ELSE 'Dead Stock (90+ days)'
    END as stock_age_category,

    -- Price Categories
    CASE
        WHEN i.purchase_price < 50 THEN 'Budget (< $50)'
        WHEN i.purchase_price < 100 THEN 'Mid-Range ($50-$100)'
        WHEN i.purchase_price < 200 THEN 'Premium ($100-$200)'
        WHEN i.purchase_price < 500 THEN 'Luxury ($200-$500)'
        ELSE 'Ultra-Premium ($500+)'
    END as price_category,

    -- Performance Indicators
    CASE
        WHEN i.status = 'sold' AND i.created_at > NOW() - INTERVAL '30 days' THEN 'Fast Mover'
        WHEN i.status = 'listed' AND i.created_at < NOW() - INTERVAL '90 days' THEN 'Dead Stock'
        WHEN i.purchase_price > 500 THEN 'High Value'
        WHEN i.quantity = 1 THEN 'Low Stock'
        ELSE 'Normal'
    END as performance_flag,

    -- Size standardization for analytics
    CASE
        WHEN i.size ~ '^[0-9]+(\.[0-9]+)?$' THEN i.size::numeric
        ELSE NULL
    END as numeric_size,

    -- Brand tier classification (based on average prices)
    CASE
        WHEN (SELECT AVG(purchase_price) FROM inventory.items i2 WHERE i2.brand_name = i.brand_name) > 300 THEN 'Tier 1 (Premium)'
        WHEN (SELECT AVG(purchase_price) FROM inventory.items i2 WHERE i2.brand_name = i.brand_name) > 150 THEN 'Tier 2 (Mid-Range)'
        ELSE 'Tier 3 (Budget)'
    END as brand_tier

FROM inventory.items i;

-- =====================================================
-- 3. BRAND PERFORMANCE VIEW
-- =====================================================

-- Brand analytics with comprehensive metrics
CREATE OR REPLACE VIEW budibase_brand_performance AS
SELECT
    brand_name,

    -- Volume Metrics
    COUNT(*) as total_items,
    COUNT(CASE WHEN status = 'listed' THEN 1 END) as active_items,
    COUNT(CASE WHEN status = 'sold' THEN 1 END) as sold_items,
    SUM(quantity) as total_quantity,

    -- Financial Metrics
    SUM(purchase_price * quantity) as total_investment,
    AVG(purchase_price) as avg_price,
    MIN(purchase_price) as min_price,
    MAX(purchase_price) as max_price,
    STDDEV(purchase_price) as price_variance,

    -- Performance Metrics
    ROUND(AVG(EXTRACT(days FROM NOW() - created_at)), 1) as avg_days_in_stock,
    COUNT(CASE WHEN created_at < NOW() - INTERVAL '90 days' AND status = 'listed' THEN 1 END) as dead_stock_count,
    COUNT(CASE WHEN created_at > NOW() - INTERVAL '7 days' THEN 1 END) as recent_additions,

    -- Market Share
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM inventory.items), 2) as market_share_percentage,
    ROUND(SUM(purchase_price * quantity) * 100.0 / (SELECT SUM(purchase_price * quantity) FROM inventory.items), 2) as value_share_percentage,

    -- Diversity Metrics
    COUNT(DISTINCT size) as size_variety,
    COUNT(DISTINCT category_name) as category_variety,
    COUNT(DISTINCT supplier) as supplier_count,

    -- Quality Indicators
    CASE
        WHEN AVG(purchase_price) > 300 THEN 'Premium Brand'
        WHEN AVG(purchase_price) > 150 THEN 'Mid-Range Brand'
        ELSE 'Budget Brand'
    END as brand_classification,

    -- Activity Dates
    MIN(created_at) as first_acquisition,
    MAX(created_at) as latest_acquisition,

    -- ROI Potential (if we had sales data)
    CASE
        WHEN COUNT(CASE WHEN status = 'sold' THEN 1 END) > 0 THEN 'Proven Seller'
        WHEN AVG(EXTRACT(days FROM NOW() - created_at)) < 30 THEN 'New Brand'
        WHEN COUNT(CASE WHEN created_at < NOW() - INTERVAL '90 days' AND status = 'listed' THEN 1 END) > COUNT(*) * 0.5 THEN 'Slow Moving'
        ELSE 'Stable'
    END as sales_performance

FROM inventory.items
GROUP BY brand_name
HAVING COUNT(*) >= 3  -- Only brands with 3+ items for statistical relevance
ORDER BY total_investment DESC;

-- =====================================================
-- 4. SIZE ANALYTICS VIEW
-- =====================================================

-- Size-based market analysis
CREATE OR REPLACE VIEW budibase_size_analytics AS
SELECT
    size,

    -- Volume Metrics
    COUNT(*) as item_count,
    COUNT(CASE WHEN status = 'listed' THEN 1 END) as available_count,
    SUM(quantity) as total_quantity,

    -- Financial Metrics
    AVG(purchase_price) as avg_price,
    MIN(purchase_price) as min_price,
    MAX(purchase_price) as max_price,
    SUM(purchase_price * quantity) as total_value,

    -- Market Analysis
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM inventory.items), 2) as market_share_percentage,

    -- Brand Diversity
    COUNT(DISTINCT brand_name) as brand_count,
    STRING_AGG(DISTINCT brand_name, ', ' ORDER BY brand_name) as brands_available,

    -- Performance Metrics
    AVG(EXTRACT(days FROM NOW() - created_at)) as avg_days_in_stock,
    COUNT(CASE WHEN created_at < NOW() - INTERVAL '90 days' AND status = 'listed' THEN 1 END) as dead_stock_count,

    -- Size Classification
    CASE
        WHEN size ~ '^[0-9]+(\.[0-9]+)?$' THEN 'Numeric Size'
        ELSE 'Non-Numeric Size'
    END as size_type,

    -- Numeric size for sorting (when applicable)
    CASE
        WHEN size ~ '^[0-9]+(\.[0-9]+)?$' THEN size::numeric
        ELSE NULL
    END as numeric_size_value,

    -- Demand Classification
    CASE
        WHEN COUNT(*) > (SELECT AVG(size_count) FROM (SELECT COUNT(*) as size_count FROM inventory.items GROUP BY size) subq) * 1.5 THEN 'High Demand'
        WHEN COUNT(*) > (SELECT AVG(size_count) FROM (SELECT COUNT(*) as size_count FROM inventory.items GROUP BY size) subq) * 0.5 THEN 'Medium Demand'
        ELSE 'Low Demand'
    END as demand_category

FROM inventory.items
GROUP BY size
ORDER BY
    CASE
        WHEN size ~ '^[0-9]+(\.[0-9]+)?$' THEN size::numeric
        ELSE 999
    END,
    size;

-- =====================================================
-- 5. FINANCIAL TRENDS VIEW
-- =====================================================

-- Daily/Monthly financial trends
CREATE OR REPLACE VIEW budibase_financial_trends AS
SELECT
    DATE(created_at) as date,
    DATE_TRUNC('week', created_at) as week,
    DATE_TRUNC('month', created_at) as month,

    -- Daily Metrics
    COUNT(*) as items_acquired,
    SUM(purchase_price * quantity) as daily_investment,
    AVG(purchase_price) as avg_daily_price,

    -- Running Totals
    SUM(COUNT(*)) OVER (ORDER BY DATE(created_at)) as cumulative_items,
    SUM(SUM(purchase_price * quantity)) OVER (ORDER BY DATE(created_at)) as cumulative_investment,

    -- Diversity Metrics
    COUNT(DISTINCT brand_name) as brands_acquired,
    COUNT(DISTINCT size) as sizes_acquired,
    COUNT(DISTINCT supplier) as suppliers_used,

    -- Quality Metrics
    MIN(purchase_price) as min_daily_price,
    MAX(purchase_price) as max_daily_price,
    STDDEV(purchase_price) as price_variance,

    -- Comparison to Historical Average
    CASE
        WHEN SUM(purchase_price * quantity) > (SELECT AVG(daily_investment) FROM (SELECT DATE(created_at), SUM(purchase_price * quantity) as daily_investment FROM inventory.items GROUP BY DATE(created_at)) subq) * 1.5 THEN 'High Investment Day'
        WHEN SUM(purchase_price * quantity) < (SELECT AVG(daily_investment) FROM (SELECT DATE(created_at), SUM(purchase_price * quantity) as daily_investment FROM inventory.items GROUP BY DATE(created_at)) subq) * 0.5 THEN 'Low Investment Day'
        ELSE 'Normal Day'
    END as investment_category

FROM inventory.items
WHERE created_at >= CURRENT_DATE - INTERVAL '1 year'
GROUP BY DATE(created_at), DATE_TRUNC('week', created_at), DATE_TRUNC('month', created_at)
ORDER BY date DESC;

-- =====================================================
-- 6. SUPPLIER PERFORMANCE VIEW
-- =====================================================

-- Supplier analysis and performance metrics
CREATE OR REPLACE VIEW budibase_supplier_performance AS
SELECT
    supplier,

    -- Volume Metrics
    COUNT(*) as total_items_supplied,
    COUNT(CASE WHEN status = 'listed' THEN 1 END) as active_items,
    COUNT(CASE WHEN status = 'sold' THEN 1 END) as sold_items,
    SUM(quantity) as total_quantity,

    -- Financial Metrics
    SUM(purchase_price * quantity) as total_investment,
    AVG(purchase_price) as avg_price,
    MIN(purchase_price) as min_price,
    MAX(purchase_price) as max_price,

    -- Diversity Metrics
    COUNT(DISTINCT brand_name) as brands_supplied,
    COUNT(DISTINCT size) as sizes_supplied,
    COUNT(DISTINCT category_name) as categories_supplied,

    -- Time Metrics
    MIN(created_at) as first_transaction,
    MAX(created_at) as last_transaction,
    EXTRACT(days FROM MAX(created_at) - MIN(created_at)) as relationship_duration_days,

    -- Performance Indicators
    AVG(EXTRACT(days FROM NOW() - created_at)) as avg_item_age,
    COUNT(CASE WHEN created_at < NOW() - INTERVAL '90 days' AND status = 'listed' THEN 1 END) as dead_stock_count,

    -- Market Share
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM inventory.items), 2) as volume_market_share,
    ROUND(SUM(purchase_price * quantity) * 100.0 / (SELECT SUM(purchase_price * quantity) FROM inventory.items), 2) as value_market_share,

    -- Supplier Classification
    CASE
        WHEN COUNT(*) > 100 THEN 'Major Supplier'
        WHEN COUNT(*) > 50 THEN 'Regular Supplier'
        WHEN COUNT(*) > 10 THEN 'Minor Supplier'
        ELSE 'Occasional Supplier'
    END as supplier_tier,

    -- Quality Assessment
    CASE
        WHEN AVG(purchase_price) > 200 THEN 'Premium Supplier'
        WHEN AVG(purchase_price) > 100 THEN 'Mid-Range Supplier'
        ELSE 'Budget Supplier'
    END as quality_tier,

    -- Activity Status
    CASE
        WHEN MAX(created_at) > NOW() - INTERVAL '30 days' THEN 'Active'
        WHEN MAX(created_at) > NOW() - INTERVAL '90 days' THEN 'Recent'
        ELSE 'Inactive'
    END as activity_status

FROM inventory.items
GROUP BY supplier
ORDER BY total_investment DESC;

-- =====================================================
-- 7. ALERTS AND MONITORING VIEW
-- =====================================================

-- Real-time alerts and monitoring
CREATE OR REPLACE VIEW budibase_alerts_monitoring AS
SELECT
    'Inventory Alert' as alert_category,
    alert_type,
    alert_count,
    alert_description,
    severity_level,
    action_required
FROM (
    SELECT
        'Dead Stock' as alert_type,
        COUNT(*) as alert_count,
        'Items older than 90 days still listed' as alert_description,
        CASE WHEN COUNT(*) > 50 THEN 'High' WHEN COUNT(*) > 20 THEN 'Medium' ELSE 'Low' END as severity_level,
        'Review pricing and consider promotions' as action_required
    FROM inventory.items
    WHERE status = 'listed' AND created_at < NOW() - INTERVAL '90 days'

    UNION ALL

    SELECT
        'High Value at Risk' as alert_type,
        COUNT(*) as alert_count,
        'High value items (>$500) sitting too long' as alert_description,
        CASE WHEN COUNT(*) > 10 THEN 'High' WHEN COUNT(*) > 5 THEN 'Medium' ELSE 'Low' END as severity_level,
        'Priority review for premium items' as action_required
    FROM inventory.items
    WHERE purchase_price > 500 AND status = 'listed' AND created_at < NOW() - INTERVAL '60 days'

    UNION ALL

    SELECT
        'Low Stock Warning' as alert_type,
        COUNT(*) as alert_count,
        'Items with only 1 unit remaining' as alert_description,
        'Medium' as severity_level,
        'Consider restocking popular items' as action_required
    FROM inventory.items
    WHERE quantity = 1 AND status = 'listed'

    UNION ALL

    SELECT
        'New Inventory' as alert_type,
        COUNT(*) as alert_count,
        'Items added in last 24 hours' as alert_description,
        'Info' as severity_level,
        'Review and categorize new items' as action_required
    FROM inventory.items
    WHERE created_at >= NOW() - INTERVAL '24 hours'

    UNION ALL

    SELECT
        'Brand Concentration Risk' as alert_type,
        COUNT(*) as alert_count,
        'Brands with >30% of total inventory value' as alert_description,
        'Medium' as severity_level,
        'Diversify inventory across brands' as action_required
    FROM (
        SELECT brand_name
        FROM inventory.items
        GROUP BY brand_name
        HAVING SUM(purchase_price * quantity) > (SELECT SUM(purchase_price * quantity) * 0.3 FROM inventory.items)
    ) concentrated_brands
) alerts
WHERE alert_count > 0
ORDER BY
    CASE severity_level
        WHEN 'High' THEN 1
        WHEN 'Medium' THEN 2
        WHEN 'Low' THEN 3
        ELSE 4
    END,
    alert_count DESC;

-- =====================================================
-- Index Recommendations for Performance
-- =====================================================

-- Uncomment these if needed for better query performance:

-- CREATE INDEX IF NOT EXISTS idx_inventory_brand_status ON inventory.items(brand_name, status);
-- CREATE INDEX IF NOT EXISTS idx_inventory_created_at ON inventory.items(created_at);
-- CREATE INDEX IF NOT EXISTS idx_inventory_price_range ON inventory.items(purchase_price);
-- CREATE INDEX IF NOT EXISTS idx_inventory_size_status ON inventory.items(size, status);
-- CREATE INDEX IF NOT EXISTS idx_inventory_supplier_date ON inventory.items(supplier, created_at);

-- =====================================================
-- Refresh Instructions
-- =====================================================

-- These views will automatically update as the underlying data changes.
-- For materialized views (if needed for performance), use:
-- REFRESH MATERIALIZED VIEW view_name;

-- To drop all views if needed:
-- DROP VIEW IF EXISTS budibase_dashboard_overview CASCADE;
-- DROP VIEW IF EXISTS budibase_inventory_analytics CASCADE;
-- DROP VIEW IF EXISTS budibase_brand_performance CASCADE;
-- DROP VIEW IF EXISTS budibase_size_analytics CASCADE;
-- DROP VIEW IF EXISTS budibase_financial_trends CASCADE;
-- DROP VIEW IF EXISTS budibase_supplier_performance CASCADE;
-- DROP VIEW IF EXISTS budibase_alerts_monitoring CASCADE;
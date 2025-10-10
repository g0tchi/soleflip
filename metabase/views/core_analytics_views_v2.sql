-- =============================================================================
-- METABASE KPI DASHBOARD VIEWS - v2.2.6
-- =============================================================================
-- Updated to use transactions.orders instead of deprecated sales.transactions
-- Includes ROI calculations and VAT-aware profit metrics
-- =============================================================================

-- =============================================================================
-- 1. REVENUE METRICS VIEWS
-- =============================================================================

-- Daily Revenue Summary (Updated for transactions.orders)
CREATE OR REPLACE VIEW analytics.daily_revenue AS
SELECT
    DATE(sold_at) as sale_date,
    COUNT(*) as transactions_count,
    SUM(gross_sale) as gross_revenue,
    SUM(platform_fee) as total_fees,
    SUM(net_proceeds) as net_proceeds,
    SUM(net_profit) as net_profit,
    AVG(gross_sale) as avg_order_value,
    AVG(roi) as avg_roi_percent
FROM transactions.orders
WHERE sold_at IS NOT NULL
GROUP BY DATE(sold_at)
ORDER BY sale_date DESC;

-- Monthly Revenue Summary
CREATE OR REPLACE VIEW analytics.monthly_revenue AS
SELECT
    DATE_TRUNC('month', sold_at) as month,
    COUNT(*) as transactions_count,
    SUM(gross_sale) as gross_revenue,
    SUM(platform_fee) as total_fees,
    SUM(net_proceeds) as net_proceeds,
    SUM(net_profit) as net_profit,
    SUM(gross_profit) as gross_profit,
    AVG(gross_sale) as avg_order_value,
    AVG(roi) as avg_roi_percent,
    COUNT(DISTINCT DATE(sold_at)) as active_days
FROM transactions.orders
WHERE sold_at IS NOT NULL
GROUP BY DATE_TRUNC('month', sold_at)
ORDER BY month DESC;

-- Revenue Growth Metrics
CREATE OR REPLACE VIEW analytics.revenue_growth AS
WITH monthly_data AS (
    SELECT
        DATE_TRUNC('month', sold_at) as month,
        SUM(gross_sale) as revenue,
        SUM(net_profit) as profit,
        COUNT(*) as transactions,
        AVG(roi) as avg_roi
    FROM transactions.orders
    WHERE sold_at IS NOT NULL
    GROUP BY DATE_TRUNC('month', sold_at)
),
growth_calc AS (
    SELECT
        month,
        revenue,
        profit,
        transactions,
        avg_roi,
        LAG(revenue) OVER (ORDER BY month) as prev_month_revenue,
        LAG(profit) OVER (ORDER BY month) as prev_month_profit,
        LAG(transactions) OVER (ORDER BY month) as prev_month_transactions
    FROM monthly_data
)
SELECT
    month,
    revenue,
    profit,
    transactions,
    avg_roi,
    prev_month_revenue,
    prev_month_profit,
    CASE
        WHEN prev_month_revenue > 0 THEN
            ROUND(((revenue - prev_month_revenue) / prev_month_revenue * 100)::numeric, 2)
        ELSE NULL
    END as revenue_growth_percent,
    CASE
        WHEN prev_month_profit > 0 THEN
            ROUND(((profit - prev_month_profit) / prev_month_profit * 100)::numeric, 2)
        ELSE NULL
    END as profit_growth_percent,
    CASE
        WHEN prev_month_transactions > 0 THEN
            ROUND(((transactions - prev_month_transactions) / prev_month_transactions::numeric * 100)::numeric, 2)
        ELSE NULL
    END as transaction_growth_percent
FROM growth_calc
ORDER BY month DESC;

-- =============================================================================
-- 2. PRODUCT PERFORMANCE VIEWS
-- =============================================================================

-- Top Products by Revenue (with ROI)
CREATE OR REPLACE VIEW analytics.top_products_revenue AS
SELECT
    p.name as product_name,
    p.sku as product_sku,
    b.name as brand_name,
    COUNT(o.id) as total_sales,
    SUM(o.gross_sale) as total_revenue,
    SUM(o.net_profit) as total_net_profit,
    SUM(o.gross_profit) as total_gross_profit,
    AVG(o.gross_sale) as avg_sale_price,
    AVG(o.roi) as avg_roi_percent,
    MIN(o.sold_at) as first_sale,
    MAX(o.sold_at) as last_sale,
    ROUND((SUM(o.net_profit) / NULLIF(SUM(o.gross_sale), 0) * 100)::numeric, 2) as net_profit_margin_percent
FROM transactions.orders o
JOIN products.inventory i ON o.inventory_item_id = i.id
JOIN products.products p ON i.product_id = p.id
LEFT JOIN core.brands b ON p.brand_id = b.id
WHERE o.sold_at IS NOT NULL
GROUP BY p.id, p.name, p.sku, b.name
ORDER BY total_revenue DESC;

-- Brand Performance (with ROI)
CREATE OR REPLACE VIEW analytics.brand_performance AS
SELECT
    COALESCE(b.name, 'Unknown Brand') as brand_name,
    COUNT(o.id) as total_sales,
    SUM(o.gross_sale) as total_revenue,
    SUM(o.net_profit) as total_net_profit,
    SUM(o.gross_profit) as total_gross_profit,
    AVG(o.gross_sale) as avg_sale_price,
    AVG(o.roi) as avg_roi_percent,
    COUNT(DISTINCT p.id) as unique_products,
    ROUND((SUM(o.net_profit) / NULLIF(SUM(o.gross_sale), 0) * 100)::numeric, 2) as net_profit_margin_percent,
    MIN(o.sold_at) as first_sale,
    MAX(o.sold_at) as last_sale
FROM transactions.orders o
JOIN products.inventory i ON o.inventory_item_id = i.id
JOIN products.products p ON i.product_id = p.id
LEFT JOIN core.brands b ON p.brand_id = b.id
WHERE o.sold_at IS NOT NULL
GROUP BY b.name
ORDER BY total_revenue DESC;

-- Product Size Analysis
CREATE OR REPLACE VIEW analytics.product_size_analysis AS
SELECT
    s.value as size,
    s.region as size_region,
    COUNT(o.id) as total_sales,
    SUM(o.gross_sale) as total_revenue,
    SUM(o.net_profit) as total_net_profit,
    AVG(o.gross_sale) as avg_sale_price,
    AVG(o.roi) as avg_roi_percent,
    COUNT(DISTINCT p.id) as unique_products
FROM transactions.orders o
JOIN products.inventory i ON o.inventory_item_id = i.id
JOIN products.products p ON i.product_id = p.id
JOIN core.sizes s ON i.size_id = s.id
WHERE o.sold_at IS NOT NULL
GROUP BY s.value, s.region
ORDER BY total_revenue DESC;

-- =============================================================================
-- 3. PLATFORM ANALYSIS VIEWS
-- =============================================================================

-- Platform Performance (Updated for multi-platform support)
CREATE OR REPLACE VIEW analytics.platform_performance AS
SELECT
    p.name as platform_name,
    p.slug as platform_slug,
    COUNT(o.id) as total_transactions,
    SUM(o.gross_sale) as total_revenue,
    SUM(o.platform_fee) as total_fees_paid,
    SUM(o.net_profit) as total_net_profit,
    SUM(o.gross_profit) as total_gross_profit,
    AVG(o.gross_sale) as avg_transaction_value,
    AVG(o.platform_fee) as avg_fee_amount,
    AVG(o.roi) as avg_roi_percent,
    ROUND((AVG(o.platform_fee) / NULLIF(AVG(o.gross_sale), 0) * 100)::numeric, 2) as avg_fee_percentage,
    MIN(o.sold_at) as first_transaction,
    MAX(o.sold_at) as last_transaction
FROM transactions.orders o
JOIN core.platforms p ON o.platform_id = p.id
WHERE o.sold_at IS NOT NULL
GROUP BY p.id, p.name, p.slug
ORDER BY total_revenue DESC;

-- Platform Monthly Trends
CREATE OR REPLACE VIEW analytics.platform_monthly_trends AS
SELECT
    DATE_TRUNC('month', o.sold_at) as month,
    p.name as platform_name,
    COUNT(o.id) as transactions,
    SUM(o.gross_sale) as revenue,
    SUM(o.platform_fee) as fees_paid,
    SUM(o.net_profit) as net_profit,
    AVG(o.gross_sale) as avg_order_value,
    AVG(o.roi) as avg_roi_percent
FROM transactions.orders o
JOIN core.platforms p ON o.platform_id = p.id
WHERE o.sold_at IS NOT NULL
GROUP BY DATE_TRUNC('month', o.sold_at), p.name
ORDER BY month DESC, revenue DESC;

-- =============================================================================
-- 4. ROI & PROFITABILITY ANALYSIS (NEW!)
-- =============================================================================

-- ROI Distribution Analysis
CREATE OR REPLACE VIEW analytics.roi_distribution AS
WITH roi_brackets AS (
    SELECT
        CASE
            WHEN roi < -20 THEN 'Loss > 20%'
            WHEN roi >= -20 AND roi < -10 THEN 'Loss 10-20%'
            WHEN roi >= -10 AND roi < 0 THEN 'Loss 0-10%'
            WHEN roi >= 0 AND roi < 10 THEN 'Profit 0-10%'
            WHEN roi >= 10 AND roi < 25 THEN 'Profit 10-25%'
            WHEN roi >= 25 AND roi < 50 THEN 'Profit 25-50%'
            WHEN roi >= 50 THEN 'Profit > 50%'
            ELSE 'Unknown'
        END as roi_bracket,
        gross_sale,
        net_profit,
        roi
    FROM transactions.orders
    WHERE roi IS NOT NULL AND sold_at IS NOT NULL
)
SELECT
    roi_bracket,
    COUNT(*) as transactions_count,
    SUM(gross_sale) as total_revenue,
    SUM(net_profit) as total_net_profit,
    AVG(roi) as avg_roi_in_bracket,
    MIN(roi) as min_roi,
    MAX(roi) as max_roi
FROM roi_brackets
GROUP BY roi_bracket
ORDER BY
    CASE roi_bracket
        WHEN 'Loss > 20%' THEN 1
        WHEN 'Loss 10-20%' THEN 2
        WHEN 'Loss 0-10%' THEN 3
        WHEN 'Profit 0-10%' THEN 4
        WHEN 'Profit 10-25%' THEN 5
        WHEN 'Profit 25-50%' THEN 6
        WHEN 'Profit > 50%' THEN 7
        ELSE 8
    END;

-- Purchase vs Sale Analysis (with VAT consideration)
CREATE OR REPLACE VIEW analytics.purchase_vs_sale_analysis AS
SELECT
    DATE_TRUNC('month', i.purchase_date) as purchase_month,
    DATE_TRUNC('month', o.sold_at) as sale_month,
    COUNT(o.id) as items_sold,
    SUM(i.purchase_price) as total_purchase_net,
    SUM(i.gross_purchase_price) as total_purchase_gross,
    SUM(i.vat_amount) as total_vat_paid,
    SUM(o.gross_sale) as total_sale_price,
    SUM(o.net_proceeds) as total_net_proceeds,
    SUM(o.net_profit) as total_net_profit,
    AVG(o.roi) as avg_roi_percent,
    -- Shelf life analysis
    AVG(EXTRACT(DAYS FROM (o.sold_at - i.purchase_date))) as avg_shelf_life_days,
    MIN(EXTRACT(DAYS FROM (o.sold_at - i.purchase_date))) as min_shelf_life_days,
    MAX(EXTRACT(DAYS FROM (o.sold_at - i.purchase_date))) as max_shelf_life_days
FROM transactions.orders o
JOIN products.inventory i ON o.inventory_item_id = i.id
WHERE o.sold_at IS NOT NULL AND i.purchase_date IS NOT NULL
GROUP BY DATE_TRUNC('month', i.purchase_date), DATE_TRUNC('month', o.sold_at)
ORDER BY purchase_month DESC, sale_month DESC;

-- Supplier Profitability Analysis (with VAT)
CREATE OR REPLACE VIEW analytics.supplier_profitability AS
SELECT
    COALESCE(s.name, 'Unknown Supplier') as supplier_name,
    s.slug as supplier_slug,
    COUNT(DISTINCT i.id) as total_items_purchased,
    COUNT(DISTINCT o.id) as total_items_sold,
    SUM(i.purchase_price) as total_purchase_net,
    SUM(i.gross_purchase_price) as total_purchase_gross,
    SUM(i.vat_amount) as total_vat_paid,
    SUM(o.gross_sale) as total_sale_revenue,
    SUM(o.net_proceeds) as total_net_proceeds,
    SUM(o.net_profit) as total_net_profit,
    AVG(o.roi) as avg_roi_percent,
    -- Calculate sell-through rate
    ROUND((COUNT(DISTINCT o.id)::numeric / NULLIF(COUNT(DISTINCT i.id), 0) * 100), 2) as sell_through_rate_percent
FROM products.inventory i
LEFT JOIN core.suppliers s ON i.supplier_id = s.id
LEFT JOIN transactions.orders o ON o.inventory_item_id = i.id AND o.sold_at IS NOT NULL
WHERE i.purchase_date IS NOT NULL
GROUP BY s.id, s.name, s.slug
ORDER BY total_net_profit DESC NULLS LAST;

-- =============================================================================
-- 5. TIME-BASED ANALYSIS VIEWS
-- =============================================================================

-- Sales by Day of Week
CREATE OR REPLACE VIEW analytics.sales_by_weekday AS
SELECT
    EXTRACT(DOW FROM sold_at) as day_of_week_num,
    TO_CHAR(sold_at, 'Day') as day_of_week_name,
    COUNT(*) as total_sales,
    SUM(gross_sale) as total_revenue,
    SUM(net_profit) as total_net_profit,
    AVG(gross_sale) as avg_order_value,
    AVG(roi) as avg_roi_percent
FROM transactions.orders
WHERE sold_at IS NOT NULL
GROUP BY EXTRACT(DOW FROM sold_at), TO_CHAR(sold_at, 'Day')
ORDER BY day_of_week_num;

-- Sales by Hour of Day
CREATE OR REPLACE VIEW analytics.sales_by_hour AS
SELECT
    EXTRACT(HOUR FROM sold_at) as hour_of_day,
    COUNT(*) as total_sales,
    SUM(gross_sale) as total_revenue,
    SUM(net_profit) as total_net_profit,
    AVG(gross_sale) as avg_order_value,
    AVG(roi) as avg_roi_percent
FROM transactions.orders
WHERE sold_at IS NOT NULL
GROUP BY EXTRACT(HOUR FROM sold_at)
ORDER BY hour_of_day;

-- =============================================================================
-- 6. BUSINESS KPIs DASHBOARD VIEW
-- =============================================================================

-- Executive Dashboard Summary (Updated with ROI)
CREATE OR REPLACE VIEW analytics.executive_dashboard AS
WITH current_month AS (
    SELECT
        COUNT(*) as current_month_sales,
        SUM(gross_sale) as current_month_revenue,
        SUM(net_profit) as current_month_profit,
        AVG(gross_sale) as current_month_aov,
        AVG(roi) as current_month_avg_roi
    FROM transactions.orders
    WHERE DATE_TRUNC('month', sold_at) = DATE_TRUNC('month', CURRENT_DATE)
),
previous_month AS (
    SELECT
        COUNT(*) as previous_month_sales,
        SUM(gross_sale) as previous_month_revenue,
        SUM(net_profit) as previous_month_profit,
        AVG(gross_sale) as previous_month_aov,
        AVG(roi) as previous_month_avg_roi
    FROM transactions.orders
    WHERE DATE_TRUNC('month', sold_at) = DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
),
all_time AS (
    SELECT
        COUNT(*) as total_transactions,
        SUM(gross_sale) as total_revenue,
        SUM(net_profit) as total_net_profit,
        SUM(gross_profit) as total_gross_profit,
        AVG(gross_sale) as avg_order_value,
        AVG(roi) as avg_roi_percent,
        COUNT(DISTINCT DATE(sold_at)) as active_days,
        MIN(sold_at) as first_transaction,
        MAX(sold_at) as last_transaction
    FROM transactions.orders
    WHERE sold_at IS NOT NULL
),
inventory_stats AS (
    SELECT
        COUNT(*) FILTER (WHERE status = 'in_stock') as items_in_stock,
        COUNT(*) FILTER (WHERE status = 'sold') as items_sold,
        SUM(gross_purchase_price) FILTER (WHERE status = 'in_stock') as inventory_value
    FROM products.inventory
)
SELECT
    -- Current Performance
    cm.current_month_sales,
    cm.current_month_revenue,
    cm.current_month_profit,
    cm.current_month_aov,
    cm.current_month_avg_roi,

    -- Previous Month Comparison
    pm.previous_month_sales,
    pm.previous_month_revenue,
    pm.previous_month_profit,
    pm.previous_month_aov,
    pm.previous_month_avg_roi,

    -- Growth Calculations
    CASE
        WHEN pm.previous_month_sales > 0 THEN
            ROUND(((cm.current_month_sales - pm.previous_month_sales) / pm.previous_month_sales::numeric * 100), 2)
        ELSE NULL
    END as sales_growth_percent,

    CASE
        WHEN pm.previous_month_revenue > 0 THEN
            ROUND(((cm.current_month_revenue - pm.previous_month_revenue) / pm.previous_month_revenue * 100)::numeric, 2)
        ELSE NULL
    END as revenue_growth_percent,

    CASE
        WHEN pm.previous_month_profit > 0 THEN
            ROUND(((cm.current_month_profit - pm.previous_month_profit) / pm.previous_month_profit * 100)::numeric, 2)
        ELSE NULL
    END as profit_growth_percent,

    -- All Time Stats
    at.total_transactions,
    at.total_revenue,
    at.total_net_profit,
    at.total_gross_profit,
    at.avg_order_value,
    at.avg_roi_percent,
    at.active_days,
    at.first_transaction,
    at.last_transaction,

    -- Inventory Stats
    inv.items_in_stock,
    inv.items_sold,
    inv.inventory_value,

    -- Calculated Metrics
    ROUND((at.total_revenue / NULLIF(at.active_days, 0))::numeric, 2) as avg_daily_revenue,
    ROUND((at.total_net_profit / NULLIF(at.total_revenue, 0) * 100)::numeric, 2) as overall_profit_margin_percent
FROM current_month cm
CROSS JOIN previous_month pm
CROSS JOIN all_time at
CROSS JOIN inventory_stats inv;

-- =============================================================================
-- 7. INVENTORY INSIGHTS VIEWS
-- =============================================================================

-- Inventory Status Overview (Enhanced with purchase data)
CREATE OR REPLACE VIEW analytics.inventory_overview AS
SELECT
    i.status,
    COUNT(*) as items_count,
    COUNT(DISTINCT p.id) as unique_products,
    COUNT(DISTINCT b.name) as unique_brands,
    SUM(i.purchase_price) as total_purchase_value_net,
    SUM(i.gross_purchase_price) as total_purchase_value_gross,
    SUM(i.vat_amount) as total_vat_paid,
    AVG(i.purchase_price) as avg_purchase_price_net,
    AVG(i.gross_purchase_price) as avg_purchase_price_gross,
    AVG(i.roi_percentage) as avg_roi_percent
FROM products.inventory i
JOIN products.products p ON i.product_id = p.id
LEFT JOIN core.brands b ON p.brand_id = b.id
GROUP BY i.status
ORDER BY items_count DESC;

-- Product Velocity (Sales Frequency) - Updated
CREATE OR REPLACE VIEW analytics.product_velocity AS
SELECT
    p.name as product_name,
    p.sku,
    b.name as brand_name,
    COUNT(o.id) as total_sales,
    EXTRACT(DAYS FROM (MAX(o.sold_at) - MIN(o.sold_at))) as days_selling,
    CASE
        WHEN EXTRACT(DAYS FROM (MAX(o.sold_at) - MIN(o.sold_at))) > 0 THEN
            ROUND((COUNT(o.id) / EXTRACT(DAYS FROM (MAX(o.sold_at) - MIN(o.sold_at))))::numeric, 3)
        ELSE NULL
    END as sales_per_day,
    AVG(o.gross_sale) as avg_sale_price,
    AVG(o.roi) as avg_roi_percent,
    MIN(o.sold_at) as first_sale,
    MAX(o.sold_at) as last_sale
FROM transactions.orders o
JOIN products.inventory i ON o.inventory_item_id = i.id
JOIN products.products p ON i.product_id = p.id
LEFT JOIN core.brands b ON p.brand_id = b.id
WHERE o.sold_at IS NOT NULL
GROUP BY p.id, p.name, p.sku, b.name
HAVING COUNT(o.id) > 1  -- Only products with multiple sales
ORDER BY sales_per_day DESC NULLS LAST;

-- =============================================================================
-- GRANT PERMISSIONS TO METABASE USER
-- =============================================================================

GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO metabaseuser;
GRANT SELECT ON ALL TABLES IN SCHEMA transactions TO metabaseuser;
GRANT SELECT ON ALL TABLES IN SCHEMA products TO metabaseuser;
GRANT SELECT ON ALL TABLES IN SCHEMA core TO metabaseuser;
GRANT USAGE ON SCHEMA analytics TO metabaseuser;
GRANT USAGE ON SCHEMA transactions TO metabaseuser;
GRANT USAGE ON SCHEMA products TO metabaseuser;
GRANT USAGE ON SCHEMA core TO metabaseuser;

-- =============================================================================
-- CHANGELOG
-- =============================================================================
-- v2.2.6:
-- - Updated all views to use transactions.orders instead of sales.transactions
-- - Added ROI metrics to all relevant views
-- - Added new ROI distribution analysis view
-- - Added purchase vs sale analysis with VAT consideration
-- - Added supplier profitability with sell-through rate
-- - Enhanced executive dashboard with profit tracking
-- - Updated inventory overview with VAT information
-- - All references to MwSt changed to VAT for consistency

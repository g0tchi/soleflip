-- =============================================================================
-- METABASE KPI DASHBOARD VIEWS
-- =============================================================================
-- Create comprehensive views for Metabase business intelligence dashboards
-- Run these in your PostgreSQL database to enable rich KPI tracking

-- =============================================================================
-- 1. REVENUE METRICS VIEWS
-- =============================================================================

-- Daily Revenue Summary
CREATE OR REPLACE VIEW analytics.daily_revenue AS
SELECT 
    DATE(transaction_date) as sale_date,
    COUNT(*) as transactions_count,
    SUM(sale_price) as gross_revenue,
    SUM(platform_fee) as total_fees,
    SUM(shipping_cost) as total_shipping,
    SUM(net_profit) as net_profit,
    AVG(sale_price) as avg_order_value,
    SUM(sale_price) / COUNT(*) as avg_transaction_value
FROM sales.transactions 
GROUP BY DATE(transaction_date)
ORDER BY sale_date DESC;

-- Monthly Revenue Summary
CREATE OR REPLACE VIEW analytics.monthly_revenue AS
SELECT 
    DATE_TRUNC('month', transaction_date) as month,
    COUNT(*) as transactions_count,
    SUM(sale_price) as gross_revenue,
    SUM(platform_fee) as total_fees,
    SUM(shipping_cost) as total_shipping,
    SUM(net_profit) as net_profit,
    AVG(sale_price) as avg_order_value,
    COUNT(DISTINCT DATE(transaction_date)) as active_days
FROM sales.transactions 
GROUP BY DATE_TRUNC('month', transaction_date)
ORDER BY month DESC;

-- Revenue Growth Metrics
CREATE OR REPLACE VIEW analytics.revenue_growth AS
WITH monthly_data AS (
    SELECT 
        DATE_TRUNC('month', transaction_date) as month,
        SUM(sale_price) as revenue,
        COUNT(*) as transactions
    FROM sales.transactions 
    GROUP BY DATE_TRUNC('month', transaction_date)
),
growth_calc AS (
    SELECT 
        month,
        revenue,
        transactions,
        LAG(revenue) OVER (ORDER BY month) as prev_month_revenue,
        LAG(transactions) OVER (ORDER BY month) as prev_month_transactions
    FROM monthly_data
)
SELECT 
    month,
    revenue,
    transactions,
    prev_month_revenue,
    CASE 
        WHEN prev_month_revenue > 0 THEN 
            ROUND(((revenue - prev_month_revenue) / prev_month_revenue * 100)::numeric, 2)
        ELSE NULL 
    END as revenue_growth_percent,
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

-- Top Products by Revenue
CREATE OR REPLACE VIEW analytics.top_products_revenue AS
SELECT 
    p.name as product_name,
    p.sku as product_sku,
    b.name as brand_name,
    COUNT(t.id) as total_sales,
    SUM(t.sale_price) as total_revenue,
    SUM(t.net_profit) as total_profit,
    AVG(t.sale_price) as avg_sale_price,
    MIN(t.transaction_date) as first_sale,
    MAX(t.transaction_date) as last_sale,
    ROUND((SUM(t.net_profit) / NULLIF(SUM(t.sale_price), 0) * 100)::numeric, 2) as profit_margin_percent
FROM sales.transactions t
JOIN products.inventory i ON t.inventory_id = i.id
JOIN products.products p ON i.product_id = p.id
LEFT JOIN core.brands b ON p.brand_id = b.id
GROUP BY p.id, p.name, p.sku, b.name
ORDER BY total_revenue DESC;

-- Brand Performance
CREATE OR REPLACE VIEW analytics.brand_performance AS
SELECT 
    COALESCE(b.name, 'Unknown Brand') as brand_name,
    COUNT(t.id) as total_sales,
    SUM(t.sale_price) as total_revenue,
    SUM(t.net_profit) as total_profit,
    AVG(t.sale_price) as avg_sale_price,
    COUNT(DISTINCT p.id) as unique_products,
    ROUND((SUM(t.net_profit) / NULLIF(SUM(t.sale_price), 0) * 100)::numeric, 2) as profit_margin_percent,
    MIN(t.transaction_date) as first_sale,
    MAX(t.transaction_date) as last_sale
FROM sales.transactions t
JOIN products.inventory i ON t.inventory_id = i.id
JOIN products.products p ON i.product_id = p.id
LEFT JOIN core.brands b ON p.brand_id = b.id
GROUP BY b.name
ORDER BY total_revenue DESC;

-- Product Size Analysis
CREATE OR REPLACE VIEW analytics.product_size_analysis AS
SELECT 
    s.value as size,
    s.region as size_region,
    COUNT(t.id) as total_sales,
    SUM(t.sale_price) as total_revenue,
    AVG(t.sale_price) as avg_sale_price,
    COUNT(DISTINCT p.id) as unique_products
FROM sales.transactions t
JOIN products.inventory i ON t.inventory_id = i.id
JOIN products.products p ON i.product_id = p.id
JOIN core.sizes s ON i.size_id = s.id
GROUP BY s.value, s.region
ORDER BY total_revenue DESC;

-- =============================================================================
-- 3. PLATFORM ANALYSIS VIEWS
-- =============================================================================

-- Platform Performance
CREATE OR REPLACE VIEW analytics.platform_performance AS
SELECT 
    p.name as platform_name,
    p.slug as platform_slug,
    COUNT(t.id) as total_transactions,
    SUM(t.sale_price) as total_revenue,
    SUM(t.platform_fee) as total_fees_paid,
    SUM(t.net_profit) as total_profit,
    AVG(t.sale_price) as avg_transaction_value,
    AVG(t.platform_fee) as avg_fee_amount,
    ROUND((AVG(t.platform_fee) / NULLIF(AVG(t.sale_price), 0) * 100)::numeric, 2) as avg_fee_percentage,
    MIN(t.transaction_date) as first_transaction,
    MAX(t.transaction_date) as last_transaction
FROM sales.transactions t
JOIN core.platforms p ON t.platform_id = p.id
GROUP BY p.id, p.name, p.slug
ORDER BY total_revenue DESC;

-- Platform Monthly Trends
CREATE OR REPLACE VIEW analytics.platform_monthly_trends AS
SELECT 
    DATE_TRUNC('month', t.transaction_date) as month,
    p.name as platform_name,
    COUNT(t.id) as transactions,
    SUM(t.sale_price) as revenue,
    SUM(t.platform_fee) as fees_paid,
    AVG(t.sale_price) as avg_order_value
FROM sales.transactions t
JOIN core.platforms p ON t.platform_id = p.id
GROUP BY DATE_TRUNC('month', t.transaction_date), p.name
ORDER BY month DESC, revenue DESC;

-- =============================================================================
-- 4. GEOGRAPHICAL ANALYSIS VIEWS
-- =============================================================================

-- Sales by Destination Country
CREATE OR REPLACE VIEW analytics.sales_by_country AS
SELECT 
    COALESCE(buyer_destination_country, 'Unknown') as destination_country,
    COUNT(*) as total_sales,
    SUM(sale_price) as total_revenue,
    AVG(sale_price) as avg_order_value,
    SUM(shipping_cost) as total_shipping_costs,
    MIN(transaction_date) as first_sale,
    MAX(transaction_date) as last_sale
FROM sales.transactions
GROUP BY buyer_destination_country
ORDER BY total_revenue DESC;

-- Sales by Destination City
CREATE OR REPLACE VIEW analytics.sales_by_city AS
SELECT 
    COALESCE(buyer_destination_country, 'Unknown') as destination_country,
    COALESCE(buyer_destination_city, 'Unknown') as destination_city,
    COUNT(*) as total_sales,
    SUM(sale_price) as total_revenue,
    AVG(sale_price) as avg_order_value,
    SUM(shipping_cost) as total_shipping_costs
FROM sales.transactions
WHERE buyer_destination_city IS NOT NULL 
GROUP BY buyer_destination_country, buyer_destination_city
ORDER BY total_revenue DESC;

-- =============================================================================
-- 5. TIME-BASED ANALYSIS VIEWS
-- =============================================================================

-- Sales by Day of Week
CREATE OR REPLACE VIEW analytics.sales_by_weekday AS
SELECT 
    EXTRACT(DOW FROM transaction_date) as day_of_week_num,
    TO_CHAR(transaction_date, 'Day') as day_of_week_name,
    COUNT(*) as total_sales,
    SUM(sale_price) as total_revenue,
    AVG(sale_price) as avg_order_value
FROM sales.transactions
GROUP BY EXTRACT(DOW FROM transaction_date), TO_CHAR(transaction_date, 'Day')
ORDER BY day_of_week_num;

-- Sales by Hour of Day
CREATE OR REPLACE VIEW analytics.sales_by_hour AS
SELECT 
    EXTRACT(HOUR FROM transaction_date) as hour_of_day,
    COUNT(*) as total_sales,
    SUM(sale_price) as total_revenue,
    AVG(sale_price) as avg_order_value
FROM sales.transactions
GROUP BY EXTRACT(HOUR FROM transaction_date)
ORDER BY hour_of_day;

-- =============================================================================
-- 6. BUSINESS KPIs DASHBOARD VIEW
-- =============================================================================

-- Executive Dashboard Summary
CREATE OR REPLACE VIEW analytics.executive_dashboard AS
WITH current_month AS (
    SELECT 
        COUNT(*) as current_month_sales,
        SUM(sale_price) as current_month_revenue,
        AVG(sale_price) as current_month_aov
    FROM sales.transactions 
    WHERE DATE_TRUNC('month', transaction_date) = DATE_TRUNC('month', CURRENT_DATE)
),
previous_month AS (
    SELECT 
        COUNT(*) as previous_month_sales,
        SUM(sale_price) as previous_month_revenue,
        AVG(sale_price) as previous_month_aov
    FROM sales.transactions 
    WHERE DATE_TRUNC('month', transaction_date) = DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
),
all_time AS (
    SELECT 
        COUNT(*) as total_transactions,
        SUM(sale_price) as total_revenue,
        AVG(sale_price) as avg_order_value,
        COUNT(DISTINCT DATE(transaction_date)) as active_days,
        MIN(transaction_date) as first_transaction,
        MAX(transaction_date) as last_transaction
    FROM sales.transactions
)
SELECT 
    -- Current Performance
    cm.current_month_sales,
    cm.current_month_revenue,
    cm.current_month_aov,
    
    -- Previous Month Comparison
    pm.previous_month_sales,
    pm.previous_month_revenue,
    pm.previous_month_aov,
    
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
    
    -- All Time Stats
    at.total_transactions,
    at.total_revenue,
    at.avg_order_value,
    at.active_days,
    at.first_transaction,
    at.last_transaction,
    
    -- Calculated Metrics
    ROUND((at.total_revenue / at.active_days)::numeric, 2) as avg_daily_revenue
FROM current_month cm
CROSS JOIN previous_month pm  
CROSS JOIN all_time at;

-- =============================================================================
-- 7. INVENTORY INSIGHTS VIEWS
-- =============================================================================

-- Inventory Status Overview
CREATE OR REPLACE VIEW analytics.inventory_overview AS
SELECT 
    i.status,
    COUNT(*) as items_count,
    COUNT(DISTINCT p.id) as unique_products,
    COUNT(DISTINCT b.name) as unique_brands,
    SUM(i.purchase_price) as total_purchase_value,
    AVG(i.purchase_price) as avg_purchase_price
FROM products.inventory i
JOIN products.products p ON i.product_id = p.id
LEFT JOIN core.brands b ON p.brand_id = b.id
GROUP BY i.status
ORDER BY items_count DESC;

-- Product Velocity (Sales Frequency)
CREATE OR REPLACE VIEW analytics.product_velocity AS
SELECT 
    p.name as product_name,
    p.sku,
    b.name as brand_name,
    COUNT(t.id) as total_sales,
    EXTRACT(DAYS FROM (MAX(t.transaction_date) - MIN(t.transaction_date))) as days_selling,
    CASE 
        WHEN EXTRACT(DAYS FROM (MAX(t.transaction_date) - MIN(t.transaction_date))) > 0 THEN
            ROUND((COUNT(t.id) / EXTRACT(DAYS FROM (MAX(t.transaction_date) - MIN(t.transaction_date))))::numeric, 3)
        ELSE NULL
    END as sales_per_day,
    AVG(t.sale_price) as avg_sale_price,
    MIN(t.transaction_date) as first_sale,
    MAX(t.transaction_date) as last_sale
FROM sales.transactions t
JOIN products.inventory i ON t.inventory_id = i.id
JOIN products.products p ON i.product_id = p.id
LEFT JOIN core.brands b ON p.brand_id = b.id
GROUP BY p.id, p.name, p.sku, b.name
HAVING COUNT(t.id) > 1  -- Only products with multiple sales
ORDER BY sales_per_day DESC NULLS LAST;

-- =============================================================================
-- GRANT PERMISSIONS TO METABASE USER
-- =============================================================================

GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO metabaseuser;
GRANT USAGE ON SCHEMA analytics TO metabaseuser;
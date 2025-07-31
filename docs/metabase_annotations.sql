-- =====================================================
-- Metabase Data Annotations for SoleFlipper Analytics
-- =====================================================
-- This file contains SQL queries and configurations to set up
-- Metabase dashboards and optimize data presentation

-- =====================================================
-- 1. CORE BUSINESS VIEWS FOR METABASE
-- =====================================================

-- Inventory Overview View
CREATE OR REPLACE VIEW analytics.inventory_overview AS
SELECT 
    p.id as product_id,
    p.sku,
    p.name as product_name,
    b.name as brand,
    c.name as category,
    p.retail_price,
    p.release_date,
    COUNT(ii.id) as total_units,
    COUNT(CASE WHEN ii.status = 'in_stock' THEN 1 END) as in_stock_count,
    COUNT(CASE WHEN ii.status = 'sold' THEN 1 END) as sold_count,
    COUNT(CASE WHEN ii.status LIKE 'listed_%' THEN 1 END) as listed_count,
    AVG(ii.purchase_price) as avg_purchase_price,
    SUM(CASE WHEN ii.status = 'in_stock' THEN ii.purchase_price ELSE 0 END) as inventory_value,
    MIN(ii.purchase_date) as first_purchase_date,
    MAX(ii.purchase_date) as last_purchase_date
FROM products.products p
LEFT JOIN core.brands b ON p.brand_id = b.id
LEFT JOIN core.categories c ON p.category_id = c.id
LEFT JOIN products.inventory_items ii ON p.id = ii.product_id
GROUP BY p.id, p.sku, p.name, b.name, c.name, p.retail_price, p.release_date;

-- Sales Performance View
CREATE OR REPLACE VIEW analytics.sales_performance AS
SELECT 
    t.id as transaction_id,
    p.sku,
    p.name as product_name,
    b.name as brand,
    c.name as category,
    s.value as size,
    s.region as size_region,
    pl.name as platform,
    t.transaction_date,
    ii.purchase_price,
    t.sale_price,
    t.platform_fee,
    t.shipping_cost,
    t.net_profit,
    ((t.net_profit / ii.purchase_price) * 100) as profit_margin_percent,
    EXTRACT(MONTH FROM t.transaction_date) as sale_month,
    EXTRACT(YEAR FROM t.transaction_date) as sale_year,
    CASE 
        WHEN t.transaction_date >= CURRENT_DATE - INTERVAL '30 days' THEN 'Last 30 Days'
        WHEN t.transaction_date >= CURRENT_DATE - INTERVAL '90 days' THEN 'Last 90 Days'
        WHEN t.transaction_date >= CURRENT_DATE - INTERVAL '1 year' THEN 'This Year'
        ELSE 'Older'
    END as time_period
FROM sales.transactions t
JOIN products.inventory_items ii ON t.inventory_id = ii.id
JOIN products.products p ON ii.product_id = p.id
JOIN core.brands b ON p.brand_id = b.id
JOIN core.categories c ON p.category_id = c.id
JOIN core.sizes s ON ii.size_id = s.id
JOIN core.platforms pl ON t.platform_id = pl.id
WHERE t.status = 'completed';

-- Import Activity Monitoring
CREATE OR REPLACE VIEW analytics.import_activity AS
SELECT 
    ib.id as batch_id,
    ib.source_type,
    ib.source_file,
    ib.status,
    ib.total_records,
    ib.processed_records,
    ib.error_records,
    ib.created_at,
    ib.started_at,
    ib.completed_at,
    EXTRACT(EPOCH FROM (ib.completed_at - ib.started_at)) * 1000 as processing_time_ms,
    (ib.processed_records::float / NULLIF(ib.total_records, 0)) * 100 as success_rate_percent,
    DATE_TRUNC('day', ib.created_at) as import_date,
    DATE_TRUNC('hour', ib.created_at) as import_hour
FROM integration.import_batches ib
ORDER BY ib.created_at DESC;

-- Monthly Business Summary
CREATE OR REPLACE VIEW analytics.monthly_summary AS
SELECT 
    DATE_TRUNC('month', transaction_date) as month,
    COUNT(*) as total_sales,
    SUM(sale_price) as gross_revenue,
    SUM(net_profit) as net_profit,
    AVG(net_profit) as avg_profit_per_sale,
    SUM(platform_fee) as total_fees,
    COUNT(DISTINCT ii.product_id) as unique_products_sold,
    AVG(((t.net_profit / ii.purchase_price) * 100)) as avg_profit_margin
FROM sales.transactions t
JOIN products.inventory_items ii ON t.inventory_id = ii.id
WHERE t.status = 'completed'
GROUP BY DATE_TRUNC('month', transaction_date)
ORDER BY month DESC;

-- =====================================================
-- 2. METABASE TABLE METADATA
-- =====================================================

-- Add column descriptions for better Metabase display
COMMENT ON TABLE products.products IS 'Master product catalog with brand and category information';
COMMENT ON COLUMN products.products.sku IS 'Unique product identifier (Stock Keeping Unit)';
COMMENT ON COLUMN products.products.name IS 'Human-readable product name';
COMMENT ON COLUMN products.products.retail_price IS 'Official retail price from manufacturer';
COMMENT ON COLUMN products.products.release_date IS 'Official product release date';

COMMENT ON TABLE products.inventory_items IS 'Individual inventory units with purchase details';
COMMENT ON COLUMN products.inventory_items.status IS 'Current inventory status: in_stock, sold, listed_stockx, listed_goat, etc.';
COMMENT ON COLUMN products.inventory_items.purchase_price IS 'Actual purchase price paid for this unit';
COMMENT ON COLUMN products.inventory_items.purchase_date IS 'Date when this unit was acquired';
COMMENT ON COLUMN products.inventory_items.supplier IS 'Where this unit was purchased from';

COMMENT ON TABLE sales.transactions IS 'Completed sales transactions with platform fees and profit calculations';
COMMENT ON COLUMN sales.transactions.sale_price IS 'Final sale price received';
COMMENT ON COLUMN sales.transactions.platform_fee IS 'Fee charged by selling platform';
COMMENT ON COLUMN sales.transactions.net_profit IS 'Profit after all fees and costs';
COMMENT ON COLUMN sales.transactions.external_id IS 'Platform-specific transaction ID (e.g., StockX order number)';

COMMENT ON TABLE integration.import_batches IS 'Import operation tracking for data pipeline monitoring';
COMMENT ON COLUMN integration.import_batches.source_type IS 'Data source: stockx, notion, sales, manual';
COMMENT ON COLUMN integration.import_batches.processing_time_ms IS 'Time taken to process import in milliseconds';

-- =====================================================
-- 3. METABASE DASHBOARD QUERIES
-- =====================================================

-- Key Performance Indicators (KPIs)
-- Total Inventory Value
SELECT SUM(CASE WHEN status = 'in_stock' THEN purchase_price ELSE 0 END) as total_inventory_value
FROM products.inventory_items;

-- Monthly Profit Trend
SELECT 
    DATE_TRUNC('month', transaction_date) as month,
    SUM(net_profit) as monthly_profit
FROM sales.transactions 
WHERE status = 'completed' 
    AND transaction_date >= CURRENT_DATE - INTERVAL '12 months'
GROUP BY month
ORDER BY month;

-- Top Performing Brands
SELECT 
    b.name as brand,
    COUNT(t.id) as total_sales,
    SUM(t.net_profit) as total_profit,
    AVG(((t.net_profit / ii.purchase_price) * 100)) as avg_margin
FROM sales.transactions t
JOIN products.inventory_items ii ON t.inventory_id = ii.id
JOIN products.products p ON ii.product_id = p.id
JOIN core.brands b ON p.brand_id = b.id
WHERE t.status = 'completed'
    AND t.transaction_date >= CURRENT_DATE - INTERVAL '6 months'
GROUP BY b.name
ORDER BY total_profit DESC
LIMIT 10;

-- Size Distribution Analysis
SELECT 
    s.value as size,
    s.region,
    COUNT(ii.id) as inventory_count,
    COUNT(t.id) as sales_count,
    (COUNT(t.id)::float / NULLIF(COUNT(ii.id), 0)) * 100 as sell_through_rate
FROM core.sizes s
LEFT JOIN products.inventory_items ii ON s.id = ii.size_id
LEFT JOIN sales.transactions t ON ii.id = t.inventory_id AND t.status = 'completed'
GROUP BY s.value, s.region
ORDER BY inventory_count DESC;

-- Import Success Rate by Source
SELECT 
    source_type,
    COUNT(*) as total_imports,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful_imports,
    (COUNT(CASE WHEN status = 'completed' THEN 1 END)::float / COUNT(*)) * 100 as success_rate,
    SUM(processed_records) as total_records_processed,
    AVG(processing_time_ms) as avg_processing_time_ms
FROM integration.import_batches
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY source_type;

-- =====================================================
-- 4. METABASE FIELD FORMATTING
-- =====================================================

-- Set up proper field types for Metabase recognition
-- (These would be configured in Metabase UI, but documented here)

/*
Field Type Configurations for Metabase:

products.products.retail_price -> Currency (USD)
products.inventory_items.purchase_price -> Currency (USD)
sales.transactions.sale_price -> Currency (USD)
sales.transactions.platform_fee -> Currency (USD)
sales.transactions.net_profit -> Currency (USD)

products.products.release_date -> Date
products.inventory_items.purchase_date -> Date
sales.transactions.transaction_date -> Date/Time
integration.import_batches.created_at -> Date/Time

integration.import_batches.processing_time_ms -> Duration (milliseconds)

sales_performance.profit_margin_percent -> Percentage (1 decimal place)
*/

-- =====================================================
-- 5. METABASE FILTERS AND SEGMENTS
-- =====================================================

-- Profitable Items Segment
SELECT *
FROM analytics.sales_performance
WHERE profit_margin_percent > 20;

-- Recent Inventory Segment (Added in last 30 days)
SELECT *
FROM analytics.inventory_overview
WHERE last_purchase_date >= CURRENT_DATE - INTERVAL '30 days';

-- High-Value Inventory Segment (>$200 retail)
SELECT *
FROM analytics.inventory_overview
WHERE retail_price > 200;

-- Fast-Moving Items (Sold within 30 days of purchase)
SELECT 
    p.sku,
    p.name,
    ii.purchase_date,
    t.transaction_date,
    t.transaction_date - ii.purchase_date as days_to_sell
FROM sales.transactions t
JOIN products.inventory_items ii ON t.inventory_id = ii.id
JOIN products.products p ON ii.product_id = p.id
WHERE t.status = 'completed'
    AND (t.transaction_date - ii.purchase_date) <= INTERVAL '30 days';

-- =====================================================
-- 6. METABASE QUESTION SUGGESTIONS
-- =====================================================

/*
Dashboard 1: Business Overview
- Total Inventory Value (KPI card)
- Monthly Profit Trend (Line chart)
- Top Brands by Profit (Bar chart)
- Recent Sales Activity (Table)

Dashboard 2: Inventory Management
- Inventory Status Distribution (Pie chart)
- Size Distribution (Bar chart)
- Inventory Age Analysis (Histogram)
- Low Stock Alerts (Table)

Dashboard 3: Import Monitoring
- Import Success Rate by Source (Bar chart)
- Processing Time Trends (Line chart)
- Daily Import Volume (Bar chart)
- Failed Import Details (Table)

Dashboard 4: Profitability Analysis
- Profit Margin Distribution (Histogram)
- Most/Least Profitable Products (Tables)
- Platform Performance Comparison (Bar chart)
- Seasonal Trends (Line chart with date filtering)
*/

-- =====================================================
-- 7. SCHEDULED REFRESH RECOMMENDATIONS
-- =====================================================

/*
Metabase Refresh Schedule Recommendations:

Real-time views (refresh every 5 minutes):
- analytics.import_activity
- Current inventory status

Hourly refresh:
- analytics.inventory_overview
- analytics.sales_performance

Daily refresh:
- analytics.monthly_summary
- Historical trend analysis

Weekly refresh:
- Long-term analytics
- Historical comparisons
*/
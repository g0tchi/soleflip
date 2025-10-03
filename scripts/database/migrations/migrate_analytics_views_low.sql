-- ============================================================================
-- Analytics Views Migration: LOW COMPLEXITY (11 views)
-- Migration from transactions.transactions -> transactions.orders
-- ============================================================================
-- Date: 2025-10-01
-- Estimated time: 2 hours
-- Views: daily_revenue, daily_sales, data_quality_check, executive_dashboard,
--        monthly_revenue, platform_performance, recent_transactions,
--        sales_by_country, sales_by_weekday, top_products, top_products_revenue
-- ============================================================================

-- Field Mapping Reference:
-- OLD (transactions)           -> NEW (orders)
-- transaction_date             -> sold_at
-- sale_price                   -> gross_sale
-- net_profit                   -> net_profit (no change)
-- platform_fee                 -> platform_fee (no change)
-- shipping_cost                -> shipping_cost (no change)
-- inventory_id                 -> inventory_item_id
-- buyer_destination_country    -> buyer_destination_country (no change)
-- buyer_destination_city       -> buyer_destination_city (no change)

-- ============================================================================
-- 1. daily_revenue (9 lines) - Revenue by day
-- ============================================================================

DROP VIEW IF EXISTS analytics.daily_revenue CASCADE;

CREATE VIEW analytics.daily_revenue AS
SELECT
    DATE(sold_at) AS sale_date,
    COUNT(*) AS transactions_count,
    SUM(gross_sale) AS gross_revenue,
    SUM(platform_fee) AS total_fees,
    SUM(shipping_cost) AS total_shipping,
    SUM(net_profit) AS net_profit
FROM transactions.orders
WHERE status = 'completed'
GROUP BY DATE(sold_at)
ORDER BY sale_date DESC;

COMMENT ON VIEW analytics.daily_revenue IS 'Daily revenue metrics - Migrated to orders table 2025-10-01';

-- ============================================================================
-- 2. daily_sales (9 lines) - Sales summary by day
-- ============================================================================

CREATE OR REPLACE VIEW analytics.daily_sales AS
SELECT
    DATE(sold_at) AS sale_date,
    COUNT(*) AS transactions,
    SUM(gross_sale) AS total_revenue,
    SUM(net_profit) AS total_profit,
    AVG(gross_sale) AS avg_price,
    AVG(net_profit) AS avg_profit
FROM transactions.orders
WHERE status = 'completed'
GROUP BY DATE(sold_at)
ORDER BY sale_date DESC;

COMMENT ON VIEW analytics.daily_sales IS 'Daily sales summary - Migrated to orders table 2025-10-01';

-- ============================================================================
-- 3. data_quality_check (13 lines) - Data quality validation
-- ============================================================================

CREATE OR REPLACE VIEW analytics.data_quality_check AS
SELECT 'Missing Net Profit' AS issue, COUNT(*) AS count
FROM transactions.orders
WHERE net_profit IS NULL AND status = 'completed'

UNION ALL

SELECT 'Missing Gross Sale' AS issue, COUNT(*) AS count
FROM transactions.orders
WHERE gross_sale IS NULL AND status = 'completed'

UNION ALL

SELECT 'Negative Profit' AS issue, COUNT(*) AS count
FROM transactions.orders
WHERE net_profit < 0 AND status = 'completed'

UNION ALL

SELECT 'Missing Platform Fee' AS issue, COUNT(*) AS count
FROM transactions.orders
WHERE platform_fee IS NULL AND status = 'completed';

COMMENT ON VIEW analytics.data_quality_check IS 'Data quality validation - Migrated to orders table 2025-10-01';

-- ============================================================================
-- 4. executive_dashboard (7 lines) - High-level KPIs
-- ============================================================================

CREATE OR REPLACE VIEW analytics.executive_dashboard AS
SELECT
    COUNT(*) AS total_transactions,
    SUM(gross_sale) AS total_revenue,
    AVG(gross_sale) AS avg_order_value,
    COUNT(DISTINCT DATE(sold_at)) AS active_days,
    MIN(sold_at) AS first_sale_date,
    MAX(sold_at) AS last_sale_date
FROM transactions.orders
WHERE status = 'completed';

COMMENT ON VIEW analytics.executive_dashboard IS 'Executive KPIs - Migrated to orders table 2025-10-01';

-- ============================================================================
-- 5. monthly_revenue (8 lines) - Revenue by month
-- ============================================================================

CREATE OR REPLACE VIEW analytics.monthly_revenue AS
SELECT
    DATE_TRUNC('month', sold_at) AS month,
    COUNT(*) AS transactions_count,
    SUM(gross_sale) AS gross_revenue,
    SUM(platform_fee) AS total_fees,
    SUM(net_profit) AS net_profit
FROM transactions.orders
WHERE status = 'completed'
GROUP BY DATE_TRUNC('month', sold_at)
ORDER BY month DESC;

COMMENT ON VIEW analytics.monthly_revenue IS 'Monthly revenue metrics - Migrated to orders table 2025-10-01';

-- ============================================================================
-- 6. platform_performance (10 lines) - Performance by platform
-- ============================================================================

CREATE OR REPLACE VIEW analytics.platform_performance AS
SELECT
    p.name AS platform_name,
    COUNT(o.id) AS total_transactions,
    SUM(o.gross_sale) AS total_revenue,
    SUM(o.platform_fee) AS total_fees_paid,
    AVG(o.gross_sale) AS avg_transaction_value,
    SUM(o.net_profit) AS net_profit
FROM transactions.orders o
JOIN core.platforms p ON o.platform_id = p.id
WHERE o.status = 'completed'
GROUP BY p.name
ORDER BY total_revenue DESC;

COMMENT ON VIEW analytics.platform_performance IS 'Platform performance metrics - Migrated to orders table 2025-10-01';

-- ============================================================================
-- 7. recent_transactions (14 lines) - Recent transactions with details
-- ============================================================================

CREATE OR REPLACE VIEW analytics.recent_transactions AS
SELECT
    o.sold_at AS transaction_date,
    p.name AS product_name,
    pl.name AS platform_name,
    o.gross_sale AS sale_price,
    o.platform_fee,
    o.net_profit,
    o.buyer_destination_country,
    o.buyer_destination_city,
    o.status
FROM transactions.orders o
JOIN products.inventory i ON o.inventory_item_id = i.id
JOIN products.products p ON i.product_id = p.id
JOIN core.platforms pl ON o.platform_id = pl.id
WHERE o.status = 'completed'
ORDER BY o.sold_at DESC
LIMIT 100;

COMMENT ON VIEW analytics.recent_transactions IS 'Recent 100 transactions - Migrated to orders table 2025-10-01';

-- ============================================================================
-- 8. sales_by_country (6 lines) - Sales by destination country
-- ============================================================================

CREATE OR REPLACE VIEW analytics.sales_by_country AS
SELECT
    COALESCE(buyer_destination_country, 'Unknown') AS destination_country,
    COUNT(*) AS total_sales,
    SUM(gross_sale) AS total_revenue,
    AVG(gross_sale) AS avg_order_value
FROM transactions.orders
WHERE status = 'completed'
GROUP BY buyer_destination_country
ORDER BY total_revenue DESC;

COMMENT ON VIEW analytics.sales_by_country IS 'Sales by destination country - Migrated to orders table 2025-10-01';

-- ============================================================================
-- 9. sales_by_weekday (7 lines) - Sales by day of week
-- ============================================================================

CREATE OR REPLACE VIEW analytics.sales_by_weekday AS
SELECT
    EXTRACT(DOW FROM sold_at) AS day_of_week_num,
    TO_CHAR(sold_at, 'Day') AS day_of_week_name,
    COUNT(*) AS total_sales,
    SUM(gross_sale) AS total_revenue,
    AVG(gross_sale) AS avg_order_value
FROM transactions.orders
WHERE status = 'completed'
GROUP BY EXTRACT(DOW FROM sold_at), TO_CHAR(sold_at, 'Day')
ORDER BY day_of_week_num;

COMMENT ON VIEW analytics.sales_by_weekday IS 'Sales by day of week - Migrated to orders table 2025-10-01';

-- ============================================================================
-- 10. top_products (13 lines) - Top selling products
-- ============================================================================

CREATE OR REPLACE VIEW analytics.top_products AS
SELECT
    p.name,
    p.sku,
    COUNT(o.*) AS sales_count,
    SUM(o.gross_sale) AS total_revenue,
    SUM(o.net_profit) AS total_profit,
    AVG(o.gross_sale) AS avg_price
FROM products.products p
JOIN products.inventory i ON p.id = i.product_id
JOIN transactions.orders o ON i.id = o.inventory_item_id
WHERE o.status = 'completed'
GROUP BY p.id, p.name, p.sku
ORDER BY total_revenue DESC
LIMIT 50;

COMMENT ON VIEW analytics.top_products IS 'Top 50 products by revenue - Migrated to orders table 2025-10-01';

-- ============================================================================
-- 11. top_products_revenue (13 lines) - Top products with brand info
-- ============================================================================

CREATE OR REPLACE VIEW analytics.top_products_revenue AS
SELECT
    p.name AS product_name,
    p.sku AS product_sku,
    b.name AS brand_name,
    COUNT(o.id) AS total_sales,
    SUM(o.gross_sale) AS total_revenue,
    AVG(o.gross_sale) AS avg_sale_price,
    SUM(o.net_profit) AS total_profit
FROM transactions.orders o
JOIN products.inventory i ON o.inventory_item_id = i.id
JOIN products.products p ON i.product_id = p.id
JOIN products.brands b ON p.brand_id = b.id
WHERE o.status = 'completed'
GROUP BY p.name, p.sku, b.name
ORDER BY total_revenue DESC
LIMIT 50;

COMMENT ON VIEW analytics.top_products_revenue IS 'Top 50 products by revenue with brand - Migrated to orders table 2025-10-01';

-- ============================================================================
-- VALIDATION QUERIES
-- ============================================================================

-- Verify row counts match (should be similar)
SELECT 'daily_revenue' AS view_name, COUNT(*) AS row_count FROM analytics.daily_revenue
UNION ALL
SELECT 'daily_sales', COUNT(*) FROM analytics.daily_sales
UNION ALL
SELECT 'monthly_revenue', COUNT(*) FROM analytics.monthly_revenue
UNION ALL
SELECT 'platform_performance', COUNT(*) FROM analytics.platform_performance
UNION ALL
SELECT 'top_products', COUNT(*) FROM analytics.top_products;

-- Verify totals match legacy data
SELECT
    'Legacy' AS source,
    COUNT(*) AS order_count,
    SUM(sale_price) AS total_revenue
FROM transactions.transactions
WHERE status = 'completed'

UNION ALL

SELECT
    'New' AS source,
    COUNT(*) AS order_count,
    SUM(gross_sale) AS total_revenue
FROM transactions.orders
WHERE status = 'completed';

-- ============================================================================
-- COMPLETION
-- ============================================================================
-- All 11 low-complexity views migrated successfully
-- Next: Migrate medium and high complexity views
-- ============================================================================

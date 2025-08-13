-- ===== ENHANCED BRAND ANALYTICS DASHBOARD QUERIES =====
-- Use these queries in Metabase or your analytics dashboard

-- 1. BRAND OVERVIEW DASHBOARD
-- Top performing brands by revenue
SELECT 
    b.name as brand_name,
    b.segment,
    b.category,
    b.price_tier,
    b.country_origin,
    COUNT(DISTINCT p.id) as total_products,
    COUNT(t.id) as total_sales,
    ROUND(SUM(t.sale_price), 2) as total_revenue,
    ROUND(AVG(t.sale_price), 2) as avg_sale_price,
    ROUND(SUM(t.net_profit), 2) as total_profit,
    ROUND(AVG(t.net_profit / NULLIF(t.sale_price, 0) * 100), 2) as avg_margin_pct
FROM core.brands b
LEFT JOIN products.products p ON p.brand_id = b.id
LEFT JOIN products.inventory i ON i.product_id = p.id
LEFT JOIN sales.transactions t ON t.inventory_id = i.id
GROUP BY b.id, b.name, b.segment, b.category, b.price_tier, b.country_origin
ORDER BY total_revenue DESC;

-- 2. BRAND TREND ANALYSIS (Monthly)
-- Shows brand performance over time
SELECT * FROM analytics.brand_trend_analysis
WHERE month >= CURRENT_DATE - INTERVAL '12 months'
ORDER BY month DESC, revenue DESC;

-- 3. MARKET SHARE ANALYSIS
-- Brand market positioning and competitive analysis
SELECT * FROM analytics.brand_market_position
ORDER BY market_share_pct DESC;

-- 4. BRAND LOYALTY METRICS
-- Customer retention and loyalty analysis
SELECT * FROM analytics.brand_loyalty_analysis
WHERE total_customers >= 5
ORDER BY repeat_rate_pct DESC, total_customers DESC;

-- 5. COLLABORATION PERFORMANCE
-- Analysis of brand collaborations vs main brands
SELECT * FROM analytics.brand_collaboration_performance
ORDER BY total_revenue DESC NULLS LAST;

-- 6. BRAND SEGMENT ANALYSIS
-- Performance comparison across different segments
SELECT 
    segment,
    COUNT(DISTINCT b.id) as brands_count,
    COUNT(DISTINCT p.id) as products_count,
    COUNT(t.id) as total_sales,
    ROUND(SUM(t.sale_price), 2) as total_revenue,
    ROUND(AVG(t.sale_price), 2) as avg_sale_price,
    ROUND(SUM(t.net_profit), 2) as total_profit,
    ROUND(AVG(t.net_profit / NULLIF(t.sale_price, 0) * 100), 2) as avg_margin_pct
FROM core.brands b
LEFT JOIN products.products p ON p.brand_id = b.id
LEFT JOIN products.inventory i ON i.product_id = p.id
LEFT JOIN sales.transactions t ON t.inventory_id = i.id
WHERE b.segment IS NOT NULL
GROUP BY segment
ORDER BY total_revenue DESC;

-- 7. GEOGRAPHIC BRAND PERFORMANCE
-- Brand performance by origin country
SELECT 
    b.country_origin,
    COUNT(DISTINCT b.id) as brands_count,
    COUNT(t.id) as total_sales,
    ROUND(SUM(t.sale_price), 2) as total_revenue,
    ROUND(AVG(t.sale_price), 2) as avg_sale_price
FROM core.brands b
JOIN products.products p ON p.brand_id = b.id
JOIN products.inventory i ON i.product_id = p.id
JOIN sales.transactions t ON t.inventory_id = i.id
WHERE b.country_origin IS NOT NULL
GROUP BY b.country_origin
ORDER BY total_revenue DESC;

-- 8. PRICE TIER ANALYSIS
-- Performance across different price segments
SELECT 
    price_tier,
    COUNT(DISTINCT b.id) as brands_count,
    COUNT(t.id) as total_sales,
    ROUND(SUM(t.sale_price), 2) as total_revenue,
    ROUND(AVG(t.sale_price), 2) as avg_sale_price,
    ROUND(MIN(t.sale_price), 2) as min_price,
    ROUND(MAX(t.sale_price), 2) as max_price
FROM core.brands b
JOIN products.products p ON p.brand_id = b.id
JOIN products.inventory i ON i.product_id = p.id
JOIN sales.transactions t ON t.inventory_id = i.id
WHERE b.price_tier IS NOT NULL
GROUP BY price_tier
ORDER BY avg_sale_price DESC;

-- 9. BRAND GROWTH ANALYSIS
-- Month-over-month growth rates
WITH monthly_brand_revenue AS (
    SELECT 
        b.name as brand_name,
        DATE_TRUNC('month', t.transaction_date) as month,
        SUM(t.sale_price) as monthly_revenue,
        COUNT(t.id) as monthly_sales
    FROM core.brands b
    JOIN products.products p ON p.brand_id = b.id
    JOIN products.inventory i ON i.product_id = p.id
    JOIN sales.transactions t ON t.inventory_id = i.id
    WHERE t.transaction_date >= CURRENT_DATE - INTERVAL '12 months'
    GROUP BY b.name, DATE_TRUNC('month', t.transaction_date)
),
growth_calc AS (
    SELECT 
        brand_name,
        month,
        monthly_revenue,
        monthly_sales,
        LAG(monthly_revenue) OVER (PARTITION BY brand_name ORDER BY month) as prev_month_revenue,
        LAG(monthly_sales) OVER (PARTITION BY brand_name ORDER BY month) as prev_month_sales
    FROM monthly_brand_revenue
)
SELECT 
    brand_name,
    month,
    monthly_revenue,
    monthly_sales,
    CASE 
        WHEN prev_month_revenue > 0 THEN 
            ROUND((monthly_revenue - prev_month_revenue) / prev_month_revenue * 100, 2)
        ELSE NULL
    END as revenue_growth_pct,
    CASE 
        WHEN prev_month_sales > 0 THEN 
            ROUND((monthly_sales - prev_month_sales) / prev_month_sales * 100, 2)
        ELSE NULL
    END as sales_growth_pct
FROM growth_calc
WHERE month >= CURRENT_DATE - INTERVAL '6 months'
ORDER BY brand_name, month DESC;

-- 10. TOP PRODUCTS BY BRAND
-- Best selling products for each major brand
WITH brand_product_performance AS (
    SELECT 
        b.name as brand_name,
        p.name as product_name,
        p.sku,
        COUNT(t.id) as sales_count,
        ROUND(SUM(t.sale_price), 2) as revenue,
        ROUND(AVG(t.sale_price), 2) as avg_price,
        ROW_NUMBER() OVER (PARTITION BY b.name ORDER BY SUM(t.sale_price) DESC) as brand_rank
    FROM core.brands b
    JOIN products.products p ON p.brand_id = b.id
    JOIN products.inventory i ON i.product_id = p.id
    JOIN sales.transactions t ON t.inventory_id = i.id
    GROUP BY b.name, p.name, p.sku
)
SELECT *
FROM brand_product_performance
WHERE brand_rank <= 3  -- Top 3 products per brand
ORDER BY brand_name, brand_rank;

-- 11. SEASONAL BRAND PERFORMANCE
-- Brand performance by season/quarter
SELECT 
    b.name as brand_name,
    EXTRACT(QUARTER FROM t.transaction_date) as quarter,
    EXTRACT(YEAR FROM t.transaction_date) as year,
    COUNT(t.id) as sales_count,
    ROUND(SUM(t.sale_price), 2) as revenue,
    ROUND(AVG(t.sale_price), 2) as avg_price
FROM core.brands b
JOIN products.products p ON p.brand_id = b.id
JOIN products.inventory i ON i.product_id = p.id
JOIN sales.transactions t ON t.inventory_id = i.id
WHERE t.transaction_date >= CURRENT_DATE - INTERVAL '2 years'
GROUP BY b.name, EXTRACT(QUARTER FROM t.transaction_date), EXTRACT(YEAR FROM t.transaction_date)
ORDER BY b.name, year DESC, quarter DESC;

-- 12. BRAND DIVERSITY ANALYSIS
-- How diversified is each brand's product portfolio
SELECT 
    b.name as brand_name,
    COUNT(DISTINCT c.name) as categories_count,
    COUNT(DISTINCT p.id) as products_count,
    COUNT(t.id) as total_sales,
    STRING_AGG(DISTINCT c.name, ', ') as categories,
    ROUND(COUNT(DISTINCT c.name)::decimal / NULLIF(COUNT(DISTINCT p.id), 0) * 100, 2) as category_diversity_pct
FROM core.brands b
JOIN products.products p ON p.brand_id = b.id
LEFT JOIN core.categories c ON c.id = p.category_id
LEFT JOIN products.inventory i ON i.product_id = p.id
LEFT JOIN sales.transactions t ON t.inventory_id = i.id
GROUP BY b.name
HAVING COUNT(t.id) > 0
ORDER BY categories_count DESC, products_count DESC;
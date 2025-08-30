-- Metabase Dashboard: Pricing KPIs
-- SQL queries for key pricing metrics and visualizations

-- 1. Average Margin by Brand (Chart: Bar)
SELECT 
    p.brand,
    ROUND(AVG(ph.margin_percentage), 2) as avg_margin_pct,
    COUNT(*) as price_points,
    ROUND(AVG(ph.price), 2) as avg_price
FROM pricing.price_history ph
JOIN products p ON ph.product_id = p.id
WHERE ph.created_at >= NOW() - INTERVAL '30 days'
GROUP BY p.brand
ORDER BY avg_margin_pct DESC;

-- 2. Price Trends Over Time (Chart: Line)
SELECT 
    DATE_TRUNC('day', ph.created_at) as date,
    p.brand,
    ROUND(AVG(ph.price), 2) as avg_price,
    ROUND(AVG(ph.margin_percentage), 2) as avg_margin
FROM pricing.price_history ph
JOIN products p ON ph.product_id = p.id
WHERE ph.created_at >= NOW() - INTERVAL '90 days'
GROUP BY date, p.brand
ORDER BY date ASC, p.brand;

-- 3. Pricing Strategy Performance (Chart: Pie)
SELECT 
    ph.strategy_used,
    COUNT(*) as usage_count,
    ROUND(AVG(ph.margin_percentage), 2) as avg_margin,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM pricing.price_history ph
WHERE ph.created_at >= NOW() - INTERVAL '30 days'
GROUP BY ph.strategy_used
ORDER BY usage_count DESC;

-- 4. Top Performing Products by Revenue (Table)
SELECT 
    p.sku,
    p.brand,
    p.name,
    ph.price as current_price,
    ph.margin_percentage,
    ph.confidence_score,
    ph.strategy_used,
    ph.updated_at
FROM pricing.price_history ph
JOIN products p ON ph.product_id = p.id
WHERE ph.id IN (
    SELECT DISTINCT ON (product_id) id 
    FROM pricing.price_history 
    ORDER BY product_id, created_at DESC
)
ORDER BY ph.margin_percentage DESC
LIMIT 50;

-- 5. Market Price Comparison (Chart: Scatter)
SELECT 
    p.brand,
    p.sku,
    ph.price as our_price,
    mp.competitor_price,
    ROUND(((ph.price - mp.competitor_price) / mp.competitor_price * 100), 2) as price_difference_pct,
    mp.competitor_name
FROM pricing.price_history ph
JOIN products p ON ph.product_id = p.id
JOIN pricing.market_prices mp ON ph.product_id = mp.product_id
WHERE ph.created_at >= NOW() - INTERVAL '7 days'
    AND mp.updated_at >= NOW() - INTERVAL '7 days'
    AND ph.id IN (
        SELECT DISTINCT ON (product_id) id 
        FROM pricing.price_history 
        ORDER BY product_id, created_at DESC
    );

-- 6. Pricing Rules Effectiveness (Chart: Bar)
SELECT 
    pr.name as rule_name,
    pr.rule_type,
    COUNT(ph.id) as applications,
    ROUND(AVG(ph.margin_percentage), 2) as avg_margin,
    ROUND(AVG(ph.confidence_score), 2) as avg_confidence
FROM pricing.price_rules pr
JOIN pricing.price_history ph ON ph.price_rule_id = pr.id
WHERE pr.is_active = true
    AND ph.created_at >= NOW() - INTERVAL '30 days'
GROUP BY pr.id, pr.name, pr.rule_type
ORDER BY applications DESC;

-- 7. Brand Multiplier Impact (Table)
SELECT 
    bm.brand,
    bm.multiplier,
    bm.reason,
    COUNT(ph.id) as products_affected,
    ROUND(AVG(ph.price), 2) as avg_price,
    ROUND(AVG(ph.margin_percentage), 2) as avg_margin
FROM pricing.brand_multipliers bm
JOIN products p ON p.brand = bm.brand
JOIN pricing.price_history ph ON ph.product_id = p.id
WHERE bm.is_active = true
    AND ph.created_at >= NOW() - INTERVAL '30 days'
GROUP BY bm.id, bm.brand, bm.multiplier, bm.reason
ORDER BY products_affected DESC;

-- 8. Pricing KPIs Summary (Single Value Cards)
-- Total Products Priced Today
SELECT COUNT(DISTINCT product_id) as products_priced_today
FROM pricing.price_history
WHERE DATE(created_at) = CURRENT_DATE;

-- Average Margin Today
SELECT ROUND(AVG(margin_percentage), 2) as avg_margin_today
FROM pricing.price_history
WHERE DATE(created_at) = CURRENT_DATE;

-- Price Changes This Week
SELECT COUNT(*) as price_changes_this_week
FROM pricing.price_history
WHERE created_at >= DATE_TRUNC('week', NOW());

-- Active Pricing Rules
SELECT COUNT(*) as active_pricing_rules
FROM pricing.price_rules
WHERE is_active = true;

-- 9. Competitive Position Analysis (Chart: Bubble)
SELECT 
    p.brand,
    COUNT(*) as product_count,
    ROUND(AVG(ph.price), 2) as avg_our_price,
    ROUND(AVG(mp.competitor_price), 2) as avg_competitor_price,
    ROUND(AVG(((ph.price - mp.competitor_price) / mp.competitor_price * 100)), 2) as avg_price_premium_pct
FROM products p
JOIN pricing.price_history ph ON ph.product_id = p.id
JOIN pricing.market_prices mp ON mp.product_id = p.id
WHERE ph.created_at >= NOW() - INTERVAL '7 days'
    AND mp.updated_at >= NOW() - INTERVAL '7 days'
GROUP BY p.brand
HAVING COUNT(*) >= 5
ORDER BY avg_price_premium_pct DESC;

-- 10. Demand Pattern Insights (Chart: Heatmap)
SELECT 
    EXTRACT(dow FROM dp.date) as day_of_week,
    EXTRACT(hour FROM dp.date) as hour_of_day,
    AVG(dp.demand_score) as avg_demand,
    COUNT(*) as data_points
FROM analytics.demand_patterns dp
WHERE dp.date >= NOW() - INTERVAL '30 days'
GROUP BY day_of_week, hour_of_day
ORDER BY day_of_week, hour_of_day;
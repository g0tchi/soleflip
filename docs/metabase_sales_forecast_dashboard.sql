-- Metabase Dashboard: Sales Forecast
-- SQL queries for sales forecasting metrics and visualizations

-- 1. 30-Day Sales Forecast by Brand (Chart: Line)
SELECT 
    sf.forecast_date,
    p.brand,
    ROUND(SUM(sf.predicted_quantity), 0) as forecasted_units,
    ROUND(SUM(sf.predicted_revenue), 2) as forecasted_revenue,
    ROUND(AVG(sf.confidence_score), 2) as avg_confidence
FROM analytics.sales_forecasts sf
JOIN products p ON sf.product_id = p.id
WHERE sf.forecast_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '30 days'
    AND sf.forecast_type = 'daily'
GROUP BY sf.forecast_date, p.brand
ORDER BY sf.forecast_date ASC, p.brand;

-- 2. Weekly Forecast Accuracy Trend (Chart: Line)
SELECT 
    DATE_TRUNC('week', fa.forecast_date) as week,
    ROUND(AVG(fa.accuracy_percentage), 2) as avg_accuracy,
    COUNT(*) as forecasts_evaluated,
    ROUND(AVG(ABS(fa.predicted_value - fa.actual_value)), 2) as avg_absolute_error
FROM analytics.forecast_accuracy fa
WHERE fa.forecast_date >= NOW() - INTERVAL '90 days'
GROUP BY week
ORDER BY week ASC;

-- 3. Model Performance Comparison (Chart: Bar)
SELECT 
    sf.model_used,
    COUNT(*) as forecast_count,
    ROUND(AVG(sf.confidence_score), 2) as avg_confidence,
    ROUND(AVG(fa.accuracy_percentage), 2) as avg_accuracy,
    ROUND(STDDEV(fa.accuracy_percentage), 2) as accuracy_stddev
FROM analytics.sales_forecasts sf
LEFT JOIN analytics.forecast_accuracy fa ON sf.id = fa.forecast_id
WHERE sf.created_at >= NOW() - INTERVAL '30 days'
GROUP BY sf.model_used
ORDER BY avg_accuracy DESC;

-- 4. Top Products by Forecasted Revenue (Table)
SELECT 
    p.sku,
    p.brand,
    p.name,
    ROUND(SUM(sf.predicted_revenue), 2) as total_forecasted_revenue,
    ROUND(SUM(sf.predicted_quantity), 0) as total_forecasted_units,
    ROUND(AVG(sf.confidence_score), 2) as avg_confidence,
    sf.model_used
FROM analytics.sales_forecasts sf
JOIN products p ON sf.product_id = p.id
WHERE sf.forecast_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '30 days'
GROUP BY p.id, p.sku, p.brand, p.name, sf.model_used
ORDER BY total_forecasted_revenue DESC
LIMIT 20;

-- 5. Seasonal Demand Patterns (Chart: Heatmap)
SELECT 
    EXTRACT(month FROM dp.date) as month,
    EXTRACT(dow FROM dp.date) as day_of_week,
    AVG(dp.demand_score) as avg_demand,
    COUNT(*) as data_points
FROM analytics.demand_patterns dp
WHERE dp.date >= NOW() - INTERVAL '365 days'
GROUP BY month, day_of_week
ORDER BY month, day_of_week;

-- 6. Channel Performance Forecast (Chart: Stacked Bar)
SELECT 
    sf.forecast_date,
    COALESCE(sf.channel, 'All Channels') as channel,
    ROUND(SUM(sf.predicted_revenue), 2) as forecasted_revenue,
    ROUND(SUM(sf.predicted_quantity), 0) as forecasted_units
FROM analytics.sales_forecasts sf
WHERE sf.forecast_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '14 days'
    AND sf.forecast_type = 'daily'
GROUP BY sf.forecast_date, sf.channel
ORDER BY sf.forecast_date ASC, channel;

-- 7. Forecast vs Actual Performance (Chart: Scatter)
SELECT 
    fa.forecast_date,
    fa.predicted_value,
    fa.actual_value,
    fa.accuracy_percentage,
    p.brand,
    sf.model_used
FROM analytics.forecast_accuracy fa
JOIN analytics.sales_forecasts sf ON fa.forecast_id = sf.id
JOIN products p ON sf.product_id = p.id
WHERE fa.forecast_date >= NOW() - INTERVAL '30 days'
    AND fa.actual_value IS NOT NULL
ORDER BY fa.forecast_date DESC;

-- 8. Weekly Revenue Trend Forecast (Chart: Area)
SELECT 
    DATE_TRUNC('week', sf.forecast_date) as week,
    ROUND(SUM(sf.predicted_revenue), 2) as forecasted_revenue,
    ROUND(AVG(sf.confidence_score), 2) as avg_confidence,
    'Forecast' as data_type
FROM analytics.sales_forecasts sf
WHERE sf.forecast_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '12 weeks'
    AND sf.forecast_type IN ('daily', 'weekly')
GROUP BY week

UNION ALL

-- Historical revenue for comparison
SELECT 
    DATE_TRUNC('week', t.created_at) as week,
    ROUND(SUM(t.price), 2) as actual_revenue,
    100.0 as avg_confidence,
    'Historical' as data_type
FROM transactions t
WHERE t.created_at >= NOW() - INTERVAL '12 weeks'
    AND t.status = 'completed'
GROUP BY week

ORDER BY week ASC;

-- 9. Demand Score Distribution (Chart: Histogram)
SELECT 
    CASE 
        WHEN dp.demand_score < 0.2 THEN 'Very Low'
        WHEN dp.demand_score < 0.4 THEN 'Low'
        WHEN dp.demand_score < 0.6 THEN 'Medium'
        WHEN dp.demand_score < 0.8 THEN 'High'
        ELSE 'Very High'
    END as demand_category,
    COUNT(*) as frequency,
    ROUND(AVG(dp.demand_score), 3) as avg_score
FROM analytics.demand_patterns dp
WHERE dp.date >= NOW() - INTERVAL '30 days'
GROUP BY demand_category
ORDER BY avg_score ASC;

-- 10. Forecast Summary KPIs (Single Value Cards)
-- Total Forecasted Revenue (Next 30 Days)
SELECT ROUND(SUM(predicted_revenue), 2) as total_forecasted_revenue_30d
FROM analytics.sales_forecasts
WHERE forecast_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '30 days';

-- Average Forecast Confidence
SELECT ROUND(AVG(confidence_score), 2) as avg_forecast_confidence
FROM analytics.sales_forecasts
WHERE forecast_date >= CURRENT_DATE
    AND forecast_date <= CURRENT_DATE + INTERVAL '30 days';

-- Models in Use
SELECT COUNT(DISTINCT model_used) as active_models
FROM analytics.sales_forecasts
WHERE created_at >= NOW() - INTERVAL '7 days';

-- Last Update Time
SELECT MAX(created_at) as last_forecast_update
FROM analytics.sales_forecasts;

-- 11. Product Variant Forecast Detail (Table)
SELECT 
    p.sku,
    p.brand,
    p.name,
    pv.size,
    pv.condition,
    ROUND(SUM(sf.predicted_quantity), 0) as forecasted_units_7d,
    ROUND(SUM(sf.predicted_revenue), 2) as forecasted_revenue_7d,
    ROUND(AVG(sf.confidence_score), 2) as avg_confidence
FROM analytics.sales_forecasts sf
JOIN products p ON sf.product_id = p.id
LEFT JOIN product_variants pv ON sf.variant_id = pv.id
WHERE sf.forecast_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'
    AND sf.forecast_type = 'daily'
GROUP BY p.id, p.sku, p.brand, p.name, pv.size, pv.condition
HAVING SUM(sf.predicted_revenue) > 0
ORDER BY forecasted_revenue_7d DESC
LIMIT 100;

-- 12. Forecast Error Analysis (Chart: Box Plot Data)
SELECT 
    sf.model_used,
    fa.accuracy_percentage,
    ABS(fa.predicted_value - fa.actual_value) as absolute_error,
    ((fa.predicted_value - fa.actual_value) / fa.actual_value * 100) as percentage_error
FROM analytics.forecast_accuracy fa
JOIN analytics.sales_forecasts sf ON fa.forecast_id = sf.id
WHERE fa.forecast_date >= NOW() - INTERVAL '60 days'
    AND fa.actual_value > 0
ORDER BY sf.model_used, fa.forecast_date DESC;
-- 📊 Budibase Table Configurations for SoleFlipper StockX API App
-- Diese SQL-Queries können in Budibase als Custom Queries verwendet werden

-- =============================================================================
-- DASHBOARD QUERIES
-- =============================================================================

-- 1. QuickFlip Opportunities Summary
CREATE OR REPLACE VIEW budibase_quickflip_summary AS
SELECT
    COUNT(*) as total_opportunities,
    ROUND(AVG(profit_margin), 2) as avg_profit_margin,
    ROUND(AVG(gross_profit), 2) as avg_gross_profit,
    COUNT(DISTINCT source) as active_sources,
    MAX(profit_margin) as best_margin,
    SUM(CASE WHEN profit_margin > 50 THEN 1 ELSE 0 END) as high_profit_count
FROM (
    SELECT DISTINCT ON (mp.product_id, mp.source)
        mp.product_id,
        mp.source,
        mp.buy_price,
        COALESCE(p.current_market_price, p.retail_price * 1.2) as sell_price,
        (COALESCE(p.current_market_price, p.retail_price * 1.2) - mp.buy_price) as gross_profit,
        ROUND(((COALESCE(p.current_market_price, p.retail_price * 1.2) - mp.buy_price) / mp.buy_price * 100), 2) as profit_margin
    FROM integration.market_prices mp
    JOIN products.products p ON mp.product_id = p.id
    WHERE mp.availability = true
    AND mp.buy_price > 0
    AND COALESCE(p.current_market_price, p.retail_price) > mp.buy_price
    ORDER BY mp.product_id, mp.source, mp.last_updated DESC
) opportunities
WHERE profit_margin >= 10;

-- 2. Inventory Summary
CREATE OR REPLACE VIEW budibase_inventory_summary AS
SELECT
    COUNT(*) as total_products,
    COUNT(DISTINCT brand) as total_brands,
    COUNT(DISTINCT category) as total_categories,
    COUNT(CASE WHEN stockx_product_id IS NOT NULL THEN 1 END) as stockx_linked,
    ROUND(AVG(COALESCE(retail_price, 0)), 2) as avg_retail_price,
    COUNT(CASE WHEN created_at >= NOW() - INTERVAL '30 days' THEN 1 END) as new_products_30d
FROM products.products;

-- 3. Market Sources Performance
CREATE OR REPLACE VIEW budibase_source_performance AS
SELECT
    source,
    COUNT(*) as total_prices,
    COUNT(DISTINCT product_id) as unique_products,
    ROUND(AVG(buy_price), 2) as avg_price,
    COUNT(CASE WHEN availability = true THEN 1 END) as available_count,
    MAX(last_updated) as last_update,
    COUNT(CASE WHEN last_updated >= NOW() - INTERVAL '24 hours' THEN 1 END) as recent_updates
FROM integration.market_prices
GROUP BY source
ORDER BY total_prices DESC;

-- =============================================================================
-- QUICKFLIP OPPORTUNITIES QUERIES
-- =============================================================================

-- 4. Main QuickFlip Opportunities Table
CREATE OR REPLACE VIEW budibase_quickflip_opportunities AS
SELECT DISTINCT ON (mp.product_id, mp.source)
    mp.id as market_price_id,
    mp.product_id,
    p.name as product_name,
    p.sku as product_sku,
    p.brand as brand_name,
    p.category,
    mp.source as buy_source,
    mp.supplier_name as buy_supplier,
    mp.external_url as buy_url,
    mp.buy_price,
    mp.stock_quantity as buy_stock_qty,
    COALESCE(p.current_market_price, p.retail_price * 1.2) as sell_price,
    p.stockx_product_id,
    (COALESCE(p.current_market_price, p.retail_price * 1.2) - mp.buy_price) as gross_profit,
    ROUND(((COALESCE(p.current_market_price, p.retail_price * 1.2) - mp.buy_price) / mp.buy_price * 100), 2) as profit_margin,
    ROUND(((COALESCE(p.current_market_price, p.retail_price * 1.2) - mp.buy_price) / mp.buy_price), 4) as roi,
    EXTRACT(DAYS FROM NOW() - p.last_sale_date) as days_since_last_sale,
    p.demand_score as stockx_demand_score,
    mp.availability,
    mp.last_updated,
    mp.created_at
FROM integration.market_prices mp
JOIN products.products p ON mp.product_id = p.id
WHERE mp.availability = true
AND mp.buy_price > 0
AND COALESCE(p.current_market_price, p.retail_price) > mp.buy_price
AND ((COALESCE(p.current_market_price, p.retail_price * 1.2) - mp.buy_price) / mp.buy_price * 100) >= 10
ORDER BY mp.product_id, mp.source, mp.last_updated DESC;

-- 5. Profit Margin Distribution
CREATE OR REPLACE VIEW budibase_profit_distribution AS
SELECT
    CASE
        WHEN profit_margin < 25 THEN '10-25%'
        WHEN profit_margin < 50 THEN '25-50%'
        WHEN profit_margin < 75 THEN '50-75%'
        WHEN profit_margin < 100 THEN '75-100%'
        ELSE '100%+'
    END as profit_range,
    COUNT(*) as opportunity_count,
    ROUND(AVG(gross_profit), 2) as avg_gross_profit
FROM budibase_quickflip_opportunities
GROUP BY
    CASE
        WHEN profit_margin < 25 THEN '10-25%'
        WHEN profit_margin < 50 THEN '25-50%'
        WHEN profit_margin < 75 THEN '50-75%'
        WHEN profit_margin < 100 THEN '75-100%'
        ELSE '100%+'
    END
ORDER BY MIN(profit_margin);

-- =============================================================================
-- PRICE MONITOR QUERIES
-- =============================================================================

-- 6. Recent Price Updates
CREATE OR REPLACE VIEW budibase_recent_price_updates AS
SELECT
    mp.id,
    p.name as product_name,
    p.sku as product_sku,
    p.brand,
    mp.source,
    mp.supplier_name,
    mp.buy_price,
    mp.previous_price,
    CASE
        WHEN mp.previous_price IS NOT NULL AND mp.buy_price > mp.previous_price THEN 'up'
        WHEN mp.previous_price IS NOT NULL AND mp.buy_price < mp.previous_price THEN 'down'
        ELSE 'stable'
    END as price_trend,
    mp.availability,
    mp.stock_quantity,
    mp.last_updated,
    EXTRACT(EPOCH FROM (NOW() - mp.last_updated))/3600 as hours_since_update
FROM integration.market_prices mp
JOIN products.products p ON mp.product_id = p.id
WHERE mp.last_updated >= NOW() - INTERVAL '7 days'
ORDER BY mp.last_updated DESC;

-- 7. Price History for Charts
CREATE OR REPLACE VIEW budibase_price_history AS
SELECT
    p.name as product_name,
    mp.source,
    mp.buy_price,
    DATE(mp.last_updated) as price_date,
    ROW_NUMBER() OVER (PARTITION BY mp.product_id, mp.source, DATE(mp.last_updated) ORDER BY mp.last_updated DESC) as rn
FROM integration.market_prices mp
JOIN products.products p ON mp.product_id = p.id
WHERE mp.last_updated >= NOW() - INTERVAL '30 days';

-- 8. Source Reliability Metrics
CREATE OR REPLACE VIEW budibase_source_reliability AS
SELECT
    source,
    COUNT(*) as total_updates,
    COUNT(CASE WHEN last_updated >= NOW() - INTERVAL '24 hours' THEN 1 END) as updates_24h,
    COUNT(CASE WHEN last_updated >= NOW() - INTERVAL '7 days' THEN 1 END) as updates_7d,
    ROUND(
        COUNT(CASE WHEN last_updated >= NOW() - INTERVAL '24 hours' THEN 1 END)::DECIMAL /
        GREATEST(COUNT(*), 1) * 100, 2
    ) as freshness_score,
    COUNT(CASE WHEN availability = true THEN 1 END) as available_products,
    ROUND(AVG(stock_quantity), 0) as avg_stock_level,
    MIN(last_updated) as first_update,
    MAX(last_updated) as latest_update
FROM integration.market_prices
GROUP BY source
ORDER BY freshness_score DESC;

-- =============================================================================
-- PRODUCT SEARCH & INVENTORY QUERIES
-- =============================================================================

-- 9. Product Search with Market Data
CREATE OR REPLACE VIEW budibase_product_search AS
SELECT
    p.id,
    p.name,
    p.sku,
    p.brand,
    p.category,
    p.color,
    p.size_range,
    p.gender,
    p.retail_price,
    p.current_market_price,
    p.stockx_product_id,
    p.last_sale_date,
    p.last_sale_price,
    p.demand_score,
    COUNT(mp.id) as market_price_sources,
    MIN(mp.buy_price) as min_market_price,
    MAX(mp.buy_price) as max_market_price,
    ROUND(AVG(mp.buy_price), 2) as avg_market_price,
    COUNT(CASE WHEN mp.availability = true THEN 1 END) as available_sources,
    p.created_at,
    p.updated_at
FROM products.products p
LEFT JOIN integration.market_prices mp ON p.id = mp.product_id
GROUP BY p.id, p.name, p.sku, p.brand, p.category, p.color, p.size_range,
         p.gender, p.retail_price, p.current_market_price, p.stockx_product_id,
         p.last_sale_date, p.last_sale_price, p.demand_score, p.created_at, p.updated_at
ORDER BY p.created_at DESC;

-- 10. Category Performance
CREATE OR REPLACE VIEW budibase_category_performance AS
SELECT
    category,
    COUNT(*) as product_count,
    COUNT(CASE WHEN stockx_product_id IS NOT NULL THEN 1 END) as stockx_linked_count,
    ROUND(AVG(retail_price), 2) as avg_retail_price,
    ROUND(AVG(current_market_price), 2) as avg_market_price,
    COUNT(CASE WHEN last_sale_date >= NOW() - INTERVAL '30 days' THEN 1 END) as recent_sales,
    ROUND(AVG(demand_score), 2) as avg_demand_score
FROM products.products
WHERE category IS NOT NULL
GROUP BY category
ORDER BY product_count DESC;

-- =============================================================================
-- BUDIBASE CONFIGURATION HELPERS
-- =============================================================================

-- 11. Environment Check Query
SELECT
    'Database Connection' as check_type,
    'OK' as status,
    VERSION() as details,
    NOW() as checked_at
UNION ALL
SELECT
    'Tables Available' as check_type,
    CASE WHEN COUNT(*) = 4 THEN 'OK' ELSE 'MISSING TABLES' END as status,
    STRING_AGG(table_name, ', ') as details,
    NOW() as checked_at
FROM information_schema.tables
WHERE table_schema IN ('products', 'integration', 'sales', 'inventory')
AND table_name IN ('products', 'market_prices', 'transactions', 'stock_levels')
UNION ALL
SELECT
    'Data Availability' as check_type,
    CASE
        WHEN (SELECT COUNT(*) FROM products.products) > 0 THEN 'OK'
        ELSE 'NO DATA'
    END as status,
    CONCAT(
        (SELECT COUNT(*) FROM products.products), ' products, ',
        (SELECT COUNT(*) FROM integration.market_prices), ' market prices'
    ) as details,
    NOW() as checked_at;

-- =============================================================================
-- BUDIBASE CUSTOM FUNCTIONS
-- =============================================================================

-- 12. Function to calculate opportunity score
CREATE OR REPLACE FUNCTION calculate_opportunity_score(
    profit_margin DECIMAL,
    gross_profit DECIMAL,
    demand_score DECIMAL DEFAULT NULL,
    days_since_sale INTEGER DEFAULT NULL
) RETURNS INTEGER AS $$
BEGIN
    RETURN GREATEST(0, LEAST(100,
        ROUND(
            (profit_margin * 0.4) +  -- 40% weight on margin
            (LEAST(gross_profit, 100) * 0.3) +  -- 30% weight on gross profit (capped at 100€)
            (COALESCE(demand_score, 50) * 0.2) +  -- 20% weight on demand
            (CASE
                WHEN days_since_sale IS NULL THEN 0
                WHEN days_since_sale <= 7 THEN 10
                WHEN days_since_sale <= 30 THEN 5
                ELSE 0
            END)  -- 10% weight on recency
        )
    ));
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- BUDIBASE TABLE REFRESH PROCEDURES
-- =============================================================================

-- 13. Procedure to refresh all materialized views (if using them)
CREATE OR REPLACE FUNCTION refresh_budibase_views() RETURNS VOID AS $$
BEGIN
    -- This would refresh materialized views if we convert the above views
    -- For now, these are regular views that auto-update

    -- Example for materialized views:
    -- REFRESH MATERIALIZED VIEW budibase_quickflip_summary;
    -- REFRESH MATERIALIZED VIEW budibase_inventory_summary;

    RAISE NOTICE 'Budibase views refreshed at %', NOW();
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- INDEXES FOR PERFORMANCE
-- =============================================================================

-- Optimize queries for Budibase
CREATE INDEX IF NOT EXISTS idx_market_prices_budibase_quickflip
ON integration.market_prices (product_id, source, availability, last_updated DESC);

CREATE INDEX IF NOT EXISTS idx_products_budibase_search
ON products.products (name, brand, category, stockx_product_id);

CREATE INDEX IF NOT EXISTS idx_market_prices_recent_updates
ON integration.market_prices (last_updated DESC)
WHERE last_updated >= NOW() - INTERVAL '7 days';

-- =============================================================================
-- USAGE EXAMPLES FOR BUDIBASE
-- =============================================================================

/*
-- Example Budibase Data Provider Configurations:

1. Dashboard KPI Cards:
   Query: SELECT * FROM budibase_quickflip_summary;

2. QuickFlip Opportunities Table:
   Query: SELECT * FROM budibase_quickflip_opportunities
          WHERE profit_margin >= {{ min_margin }}
          ORDER BY profit_margin DESC
          LIMIT {{ limit }};

3. Price Monitor Table:
   Query: SELECT * FROM budibase_recent_price_updates
          WHERE source = COALESCE(NULLIF('{{ source_filter }}', 'all'), source)
          ORDER BY last_updated DESC;

4. Product Search:
   Query: SELECT * FROM budibase_product_search
          WHERE name ILIKE '%{{ search_term }}%'
          OR brand ILIKE '%{{ search_term }}%'
          OR sku ILIKE '%{{ search_term }}%'
          ORDER BY name;

5. Performance Charts:
   Query: SELECT * FROM budibase_profit_distribution;
   Query: SELECT * FROM budibase_source_performance;
*/
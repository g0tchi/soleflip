-- BRAND INTELLIGENCE DASHBOARD SQL QUERIES
-- SoleFlipper Brand Deep Dive Analytics
-- Erstellt: 2025-08-07

-- =============================================================================
-- 1. EXECUTIVE BRAND OVERVIEW QUERIES
-- =============================================================================

-- Executive KPI Cards
-- Top Performing Brands (Revenue-basiert)
WITH brand_sales AS (
    SELECT 
        t.brand,
        COUNT(*) as transactions_count,
        SUM(t.sale_price_eur) as total_revenue_eur,
        AVG(t.sale_price_eur) as avg_sale_price,
        AVG(t.margin_eur) as avg_margin
    FROM sales.transactions t
    WHERE t.sale_date >= CURRENT_DATE - INTERVAL '12 months'
    GROUP BY t.brand
)
SELECT 
    bs.brand,
    bs.total_revenue_eur,
    bs.transactions_count,
    bs.avg_sale_price,
    bs.avg_margin,
    b.annual_revenue_usd / 1000000000.0 as global_revenue_billions,
    b.founded_year,
    EXTRACT(YEAR FROM CURRENT_DATE) - b.founded_year as brand_age,
    b.sustainability_score
FROM brand_sales bs
LEFT JOIN core.brands b ON bs.brand = b.name
ORDER BY bs.total_revenue_eur DESC
LIMIT 10;

-- Brand Size Distribution
SELECT 
    CASE 
        WHEN annual_revenue_usd > 50000000000 THEN 'Titan ($50B+)'
        WHEN annual_revenue_usd > 10000000000 THEN 'Mega Brand ($10B+)'
        WHEN annual_revenue_usd > 1000000000 THEN 'Large Brand ($1B+)'
        WHEN annual_revenue_usd > 100000000 THEN 'Medium Brand ($100M+)'
        ELSE 'Emerging Brand'
    END as brand_tier,
    COUNT(*) as brand_count,
    AVG(sustainability_score) as avg_sustainability,
    AVG(EXTRACT(YEAR FROM CURRENT_DATE) - founded_year) as avg_age
FROM core.brands
WHERE annual_revenue_usd IS NOT NULL
GROUP BY brand_tier
ORDER BY AVG(annual_revenue_usd) DESC;

-- =============================================================================
-- 2. BRAND HISTORY & TIMELINE QUERIES  
-- =============================================================================

-- Interactive Timeline Visualization
SELECT 
    brand_name,
    event_date,
    event_title,
    event_description,
    event_type,
    impact_level,
    years_ago,
    timeline_position,
    CASE event_type
        WHEN 'founded' THEN '#1f77b4'      -- Blue
        WHEN 'milestone' THEN '#ff7f0e'    -- Orange
        WHEN 'collaboration' THEN '#2ca02c' -- Green
        WHEN 'ipo' THEN '#d62728'          -- Red
        WHEN 'acquired' THEN '#9467bd'     -- Purple
        ELSE '#8c564b'                     -- Brown
    END as color_code,
    CASE impact_level
        WHEN 'critical' THEN 20
        WHEN 'high' THEN 15
        WHEN 'medium' THEN 10
        ELSE 5
    END as marker_size
FROM analytics.brand_timeline
WHERE impact_level IN ('high', 'critical')
ORDER BY event_date DESC;

-- Innovation Timeline
SELECT 
    brand_name,
    innovation_year,
    event_title,
    event_description,
    key_technologies,
    innovation_focus,
    innovation_sequence
FROM analytics.brand_innovation_timeline
ORDER BY innovation_year DESC, brand_name;

-- Brand Generation Analysis
SELECT 
    name as brand,
    founded_year,
    founder_name,
    headquarters_city || ', ' || headquarters_country as headquarters,
    EXTRACT(YEAR FROM CURRENT_DATE) - founded_year as brand_age,
    annual_revenue_usd,
    CASE 
        WHEN founded_year < 1950 THEN 'Legacy Brands (Pre-1950)'
        WHEN founded_year < 1980 THEN 'Established Brands (1950-1979)'
        WHEN founded_year < 2000 THEN 'Modern Brands (1980-1999)'
        ELSE 'New Age Brands (2000+)'
    END as brand_generation,
    sustainability_score
FROM core.brands
WHERE founded_year IS NOT NULL
ORDER BY founded_year;

-- =============================================================================
-- 3. COLLABORATION & PARTNERSHIPS QUERIES
-- =============================================================================

-- Collaboration Success Matrix
SELECT 
    primary_brand,
    collaborator_brand,
    collaboration_name,
    collaboration_type,
    launch_date,
    success_level,
    hype_score,
    estimated_revenue_usd,
    resale_multiplier,
    CASE success_level
        WHEN 'legendary' THEN 4
        WHEN 'high' THEN 3
        WHEN 'medium' THEN 2
        ELSE 1
    END as success_score,
    collaboration_era,
    days_since_launch
FROM analytics.brand_collaboration_network
ORDER BY hype_score DESC, estimated_revenue_usd DESC;

-- Hype Score Analysis
WITH hype_analysis AS (
    SELECT 
        primary_brand,
        COUNT(*) as collaboration_count,
        AVG(hype_score) as avg_hype,
        MAX(hype_score) as max_hype,
        MIN(hype_score) as min_hype,
        SUM(estimated_revenue_usd) as total_collab_revenue,
        AVG(resale_multiplier) as avg_resale_multiplier
    FROM core.brand_collaborations
    GROUP BY primary_brand
)
SELECT 
    ha.*,
    b.cultural_influence_tier,
    b.cultural_impact_score
FROM hype_analysis ha
LEFT JOIN analytics.brand_cultural_impact b ON ha.primary_brand = b.brand_name
ORDER BY ha.avg_hype DESC;

-- Collaboration Timeline
SELECT 
    launch_date,
    primary_brand || ' x ' || collaborator_brand as partnership,
    collaboration_name,
    success_level,
    estimated_revenue_usd,
    hype_score,
    resale_multiplier,
    collaboration_era,
    EXTRACT(MONTH FROM launch_date) as launch_month,
    EXTRACT(YEAR FROM launch_date) as launch_year
FROM analytics.brand_collaboration_network
ORDER BY launch_date DESC;

-- =============================================================================
-- 4. BRAND PERSONALITY & CULTURE QUERIES
-- =============================================================================

-- Cultural Impact Leaderboard
SELECT 
    brand_name,
    cultural_influence_tier,
    cultural_impact_score,
    brand_age,
    collaboration_count,
    critical_moments,
    major_milestones,
    avg_hype_score,
    total_collaboration_revenue,
    RANK() OVER (ORDER BY cultural_impact_score DESC) as impact_rank
FROM analytics.brand_cultural_impact
ORDER BY cultural_impact_score DESC;

-- Brand Personality Matrix
SELECT 
    brand_name,
    category,
    segment,
    target_demographic,
    personality_traits,
    style_attributes,
    quality_attributes,
    brand_values,
    sustainability_tier,
    attribute_diversity,
    avg_confidence_score
FROM analytics.brand_personality_analysis
WHERE personality_traits IS NOT NULL
ORDER BY avg_confidence_score DESC;

-- Sustainability Performance Dashboard
SELECT 
    name as brand,
    sustainability_score,
    CASE 
        WHEN sustainability_score >= 8 THEN 'Sustainability Leader'
        WHEN sustainability_score >= 6 THEN 'Good Performance'
        WHEN sustainability_score >= 4 THEN 'Average Performance'
        ELSE 'Needs Improvement'
    END as sustainability_tier,
    brand_values,
    innovation_focus,
    annual_revenue_usd,
    founded_year,
    EXTRACT(YEAR FROM CURRENT_DATE) - founded_year as brand_age
FROM core.brands
WHERE sustainability_score IS NOT NULL
ORDER BY sustainability_score DESC;

-- Values Analysis
WITH values_analysis AS (
    SELECT 
        name,
        brand_values,
        UNNEST(brand_values) as individual_value,
        ARRAY_LENGTH(brand_values, 1) as values_count
    FROM core.brands
    WHERE brand_values IS NOT NULL
)
SELECT 
    individual_value as brand_value,
    COUNT(*) as brands_with_value,
    ARRAY_AGG(name) as brands_list
FROM values_analysis
GROUP BY individual_value
ORDER BY COUNT(*) DESC;

-- =============================================================================
-- 5. FINANCIAL PERFORMANCE QUERIES
-- =============================================================================

-- Multi-Year Revenue Evolution
SELECT 
    brand_name,
    fiscal_year,
    revenue_usd,
    profit_usd,
    profit_margin_percentage,
    growth_rate_percentage,
    calculated_growth_rate,
    revenue_tier,
    market_cap_usd,
    employee_count,
    online_sales_percentage
FROM analytics.brand_financial_evolution
ORDER BY brand_name, fiscal_year DESC;

-- Current Year Profitability Champions
WITH current_financials AS (
    SELECT *
    FROM analytics.brand_financial_evolution
    WHERE fiscal_year = (SELECT MAX(fiscal_year) FROM analytics.brand_financial_evolution)
)
SELECT 
    brand_name,
    revenue_usd,
    profit_margin_percentage,
    growth_rate_percentage,
    revenue_tier,
    employee_count,
    CASE 
        WHEN profit_margin_percentage > 25 THEN 'Excellent (>25%)'
        WHEN profit_margin_percentage > 15 THEN 'Good (15-25%)'
        WHEN profit_margin_percentage > 5 THEN 'Average (5-15%)'
        WHEN profit_margin_percentage > 0 THEN 'Poor (0-5%)'
        ELSE 'Loss Making'
    END as profitability_tier,
    RANK() OVER (ORDER BY profit_margin_percentage DESC) as profit_rank
FROM current_financials
WHERE profit_margin_percentage IS NOT NULL
ORDER BY profit_margin_percentage DESC;

-- Growth Rate Analysis
SELECT 
    brand_name,
    revenue_usd as current_revenue,
    prev_year_revenue,
    growth_rate_percentage,
    calculated_growth_rate,
    market_cap_usd,
    CASE 
        WHEN growth_rate_percentage > 15 THEN 'High Growth (>15%)'
        WHEN growth_rate_percentage > 5 THEN 'Moderate Growth (5-15%)'
        WHEN growth_rate_percentage > 0 THEN 'Slow Growth (0-5%)'
        ELSE 'Declining'
    END as growth_category,
    RANK() OVER (ORDER BY growth_rate_percentage DESC) as growth_rank
FROM analytics.brand_financial_evolution
WHERE fiscal_year = (SELECT MAX(fiscal_year) FROM analytics.brand_financial_evolution)
    AND growth_rate_percentage IS NOT NULL
ORDER BY growth_rate_percentage DESC;

-- Financial Efficiency Analysis
SELECT 
    brand_name,
    fiscal_year,
    revenue_usd,
    employee_count,
    CASE 
        WHEN employee_count > 0 THEN revenue_usd / employee_count
        ELSE NULL
    END as revenue_per_employee,
    rd_spending_usd,
    marketing_spend_usd,
    CASE 
        WHEN revenue_usd > 0 THEN (rd_spending_usd / revenue_usd * 100)
        ELSE NULL
    END as rd_percentage,
    CASE 
        WHEN revenue_usd > 0 THEN (marketing_spend_usd / revenue_usd * 100) 
        ELSE NULL
    END as marketing_percentage
FROM core.brand_financials
WHERE fiscal_year = (SELECT MAX(fiscal_year) FROM core.brand_financials)
ORDER BY revenue_per_employee DESC;

-- =============================================================================
-- 6. BRAND PERFORMANCE vs SALES CORRELATION QUERIES
-- =============================================================================

-- Brand Intelligence vs Sales Performance
WITH sales_performance AS (
    SELECT 
        t.brand,
        COUNT(*) as transaction_count,
        SUM(t.sale_price_eur) as total_revenue_eur,
        AVG(t.sale_price_eur) as avg_sale_price,
        AVG(t.margin_eur) as avg_margin,
        AVG(t.margin_percentage) as avg_margin_percentage
    FROM sales.transactions t
    WHERE t.sale_date >= CURRENT_DATE - INTERVAL '12 months'
    GROUP BY t.brand
)
SELECT 
    sp.brand,
    sp.transaction_count,
    sp.total_revenue_eur,
    sp.avg_sale_price,
    sp.avg_margin,
    sp.avg_margin_percentage,
    b.founded_year,
    EXTRACT(YEAR FROM CURRENT_DATE) - b.founded_year as brand_age,
    b.sustainability_score,
    b.annual_revenue_usd,
    b.brand_mission,
    b.key_technologies,
    COALESCE(ci.cultural_impact_score, 0) as cultural_impact_score,
    COALESCE(ci.cultural_influence_tier, 'Unknown') as cultural_tier
FROM sales_performance sp
LEFT JOIN core.brands b ON sp.brand = b.name
LEFT JOIN analytics.brand_cultural_impact ci ON b.name = ci.brand_name
ORDER BY sp.total_revenue_eur DESC;

-- Hype Score Impact on Sales
WITH brand_hype AS (
    SELECT 
        primary_brand,
        AVG(hype_score) as avg_hype_score,
        MAX(hype_score) as max_hype_score,
        COUNT(*) as collaboration_count,
        SUM(estimated_revenue_usd) as total_collab_revenue
    FROM core.brand_collaborations
    GROUP BY primary_brand
),
recent_sales AS (
    SELECT 
        brand,
        COUNT(*) as recent_sales_count,
        AVG(sale_price_eur) as avg_resale_price,
        SUM(sale_price_eur) as total_resale_revenue
    FROM sales.transactions
    WHERE sale_date >= CURRENT_DATE - INTERVAL '6 months'
    GROUP BY brand
)
SELECT 
    bh.primary_brand as brand,
    bh.avg_hype_score,
    bh.max_hype_score,
    bh.collaboration_count,
    bh.total_collab_revenue,
    COALESCE(rs.recent_sales_count, 0) as recent_sales,
    COALESCE(rs.avg_resale_price, 0) as avg_resale_price,
    COALESCE(rs.total_resale_revenue, 0) as total_resale_revenue,
    CASE 
        WHEN rs.recent_sales_count > 0 THEN 'Active in Resale'
        ELSE 'No Recent Sales'
    END as resale_activity
FROM brand_hype bh
LEFT JOIN recent_sales rs ON bh.primary_brand = rs.brand
ORDER BY bh.avg_hype_score DESC;

-- =============================================================================
-- 7. ADVANCED ANALYTICS QUERIES
-- =============================================================================

-- Brand Age vs Performance Correlation
WITH correlation_data AS (
    SELECT 
        name,
        EXTRACT(YEAR FROM CURRENT_DATE) - founded_year as brand_age,
        annual_revenue_usd,
        sustainability_score,
        COALESCE(ci.cultural_impact_score, 0) as cultural_impact
    FROM core.brands b
    LEFT JOIN analytics.brand_cultural_impact ci ON b.name = ci.brand_name
    WHERE founded_year IS NOT NULL 
    AND annual_revenue_usd IS NOT NULL
)
SELECT 
    CORR(brand_age, annual_revenue_usd) as age_revenue_correlation,
    CORR(sustainability_score, annual_revenue_usd) as sustainability_revenue_correlation,
    CORR(cultural_impact, annual_revenue_usd) as culture_revenue_correlation,
    CORR(brand_age, sustainability_score) as age_sustainability_correlation
FROM correlation_data;

-- Growth Trajectory Prediction
WITH growth_analysis AS (
    SELECT 
        brand_name,
        fiscal_year,
        revenue_usd,
        growth_rate_percentage,
        AVG(growth_rate_percentage) OVER (
            PARTITION BY brand_name 
            ORDER BY fiscal_year 
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) as rolling_3yr_growth,
        COUNT(*) OVER (PARTITION BY brand_name) as years_of_data
    FROM core.brand_financials
    WHERE growth_rate_percentage IS NOT NULL
)
SELECT 
    brand_name,
    rolling_3yr_growth as avg_growth_3yr,
    years_of_data,
    CASE 
        WHEN rolling_3yr_growth > 15 THEN 'High Growth Trajectory'
        WHEN rolling_3yr_growth > 5 THEN 'Moderate Growth Trajectory'
        WHEN rolling_3yr_growth > 0 THEN 'Slow Growth Trajectory'
        ELSE 'Declining Trajectory'
    END as growth_trajectory,
    CASE 
        WHEN years_of_data >= 3 THEN 'Reliable Data'
        ELSE 'Limited Data'
    END as data_quality
FROM growth_analysis
WHERE fiscal_year = (SELECT MAX(fiscal_year) FROM growth_analysis)
    AND years_of_data >= 2
ORDER BY rolling_3yr_growth DESC;

-- Market Position Matrix
SELECT 
    b.name as brand,
    b.annual_revenue_usd,
    b.sustainability_score,
    EXTRACT(YEAR FROM CURRENT_DATE) - b.founded_year as brand_age,
    COALESCE(ci.cultural_impact_score, 0) as cultural_impact,
    COALESCE(avg_hype.avg_hype, 0) as avg_collaboration_hype,
    CASE 
        WHEN b.annual_revenue_usd > 10000000000 AND COALESCE(ci.cultural_impact_score, 0) > 50 
        THEN 'Market Leader'
        WHEN b.annual_revenue_usd > 1000000000 AND COALESCE(ci.cultural_impact_score, 0) > 30 
        THEN 'Strong Player'
        WHEN b.annual_revenue_usd > 100000000 OR COALESCE(ci.cultural_impact_score, 0) > 20 
        THEN 'Emerging Brand'
        ELSE 'Niche Player'
    END as market_position
FROM core.brands b
LEFT JOIN analytics.brand_cultural_impact ci ON b.name = ci.brand_name
LEFT JOIN (
    SELECT primary_brand, AVG(hype_score) as avg_hype
    FROM core.brand_collaborations
    GROUP BY primary_brand
) avg_hype ON b.name = avg_hype.primary_brand
WHERE b.annual_revenue_usd IS NOT NULL
ORDER BY b.annual_revenue_usd DESC, ci.cultural_impact_score DESC;

-- =============================================================================
-- 8. METABASE DASHBOARD HELPER QUERIES
-- =============================================================================

-- Date Range Helper for Filters
SELECT 
    MIN(event_date) as earliest_brand_event,
    MAX(event_date) as latest_brand_event,
    MIN(launch_date) as earliest_collaboration,
    MAX(launch_date) as latest_collaboration
FROM core.brand_history
CROSS JOIN core.brand_collaborations;

-- Brand List for Multi-Select Filters
SELECT DISTINCT 
    name as brand_name,
    CASE 
        WHEN annual_revenue_usd > 10000000000 THEN 'Mega'
        WHEN annual_revenue_usd > 1000000000 THEN 'Large' 
        WHEN annual_revenue_usd > 100000000 THEN 'Medium'
        ELSE 'Small'
    END as size_category
FROM core.brands
WHERE name IS NOT NULL
ORDER BY annual_revenue_usd DESC NULLS LAST;

-- Summary Statistics for KPI Cards
SELECT 
    COUNT(DISTINCT b.name) as total_brands,
    COUNT(DISTINCT CASE WHEN b.founder_name IS NOT NULL THEN b.name END) as enriched_brands,
    COUNT(DISTINCT bh.id) as total_historical_events,
    COUNT(DISTINCT bc.id) as total_collaborations,
    AVG(b.sustainability_score) as avg_sustainability,
    SUM(b.annual_revenue_usd) as total_global_revenue
FROM core.brands b
LEFT JOIN core.brand_history bh ON b.id = bh.brand_id
LEFT JOIN core.brand_collaborations bc ON b.id = bc.primary_brand_id;
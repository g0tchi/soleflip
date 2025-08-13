-- =============================================================================
-- METABASE DASHBOARD SQL QUERIES
-- Copy-paste ready queries für schnelle Dashboard-Erstellung
-- =============================================================================

-- =============================================================================
-- 📊 EXECUTIVE DASHBOARD QUERIES
-- =============================================================================

-- KPI 1: Gesamt-Umsatz
SELECT ROUND(total_revenue::numeric, 2) as "Gesamt-Umsatz €"
FROM analytics.executive_dashboard;

-- KPI 2: Anzahl Transaktionen  
SELECT total_transactions as "Transaktionen"
FROM analytics.executive_dashboard;

-- KPI 3: Durchschnittlicher Bestellwert
SELECT ROUND(avg_order_value::numeric, 2) as "Ø Bestellwert €"
FROM analytics.executive_dashboard;

-- KPI 4: Täglicher Durchschnittsumsatz
SELECT ROUND(avg_daily_revenue::numeric, 2) as "Ø Täglicher Umsatz €"
FROM analytics.executive_dashboard;

-- Chart 1: Monatlicher Umsatz-Trend (Line Chart)
SELECT 
  month as "Monat",
  gross_revenue as "Umsatz €",
  transactions_count as "Transaktionen"
FROM analytics.monthly_revenue 
ORDER BY month;

-- Chart 2: Umsatzwachstum % (Bar Chart)  
SELECT 
  TO_CHAR(month, 'YYYY-MM') as "Monat",
  revenue_growth_percent as "Wachstum %"
FROM analytics.revenue_growth 
WHERE revenue_growth_percent IS NOT NULL
ORDER BY month DESC 
LIMIT 12;

-- Table 1: Letzte Transaktionen
SELECT 
  transaction_date as "Datum",
  product_name as "Produkt",
  platform_name as "Plattform", 
  sale_price as "Preis €",
  buyer_destination_country as "Land"
FROM analytics.recent_transactions 
LIMIT 15;

-- =============================================================================
-- 🎯 PRODUCT PERFORMANCE QUERIES
-- =============================================================================

-- Table 1: Top Produkte nach Umsatz
SELECT 
  product_name as "Produkt",
  brand_name as "Marke",
  total_sales as "Verkäufe",
  ROUND(total_revenue::numeric, 2) as "Umsatz €",
  ROUND(avg_sale_price::numeric, 2) as "Ø Preis €",
  first_sale::date as "Erster Verkauf",
  last_sale::date as "Letzter Verkauf"
FROM analytics.top_products_revenue 
LIMIT 25;

-- Chart 1: Umsatz nach Marke (Pie Chart)
SELECT 
  brand_name as "Marke",
  total_revenue as "Umsatz €"
FROM analytics.brand_performance 
WHERE brand_name IS NOT NULL
ORDER BY total_revenue DESC 
LIMIT 10;

-- Chart 2: Verkäufe nach Marke (Bar Chart)
SELECT 
  brand_name as "Marke",
  total_sales as "Verkäufe"
FROM analytics.brand_performance 
WHERE brand_name IS NOT NULL
ORDER BY total_sales DESC 
LIMIT 10;

-- Chart 3: Durchschnittspreise nach Marke (Bar Chart)
SELECT 
  brand_name as "Marke",
  ROUND(avg_sale_price::numeric, 2) as "Ø Preis €"
FROM analytics.brand_performance 
WHERE brand_name IS NOT NULL
ORDER BY avg_sale_price DESC 
LIMIT 10;

-- =============================================================================
-- 🏷️ BRAND DEEP DIVE QUERIES
-- =============================================================================

-- Chart 1: Brand Marktanteil (Donut Chart)
SELECT 
  extracted_brand as "Marke",
  total_revenue as "Umsatz €",
  ROUND((total_revenue / (SELECT SUM(total_revenue) FROM analytics.brand_deep_dive_overview) * 100)::numeric, 1) as "Marktanteil %"
FROM analytics.brand_deep_dive_overview 
ORDER BY total_revenue DESC;

-- Table 1: Brand Performance Übersicht
SELECT 
  extracted_brand as "Marke",
  total_transactions as "Transaktionen",
  unique_products as "Produkte",
  ROUND(total_revenue::numeric, 2) as "Umsatz €",
  ROUND(avg_sale_price::numeric, 2) as "Ø Preis €",
  first_sale::date as "Erster Verkauf",
  last_sale::date as "Letzter Verkauf"
FROM analytics.brand_deep_dive_overview 
ORDER BY total_revenue DESC;

-- Chart 2: Brand Monatstrends (Line Chart)
SELECT 
  month as "Monat",
  extracted_brand as "Marke",
  revenue as "Umsatz €",
  transactions as "Transaktionen"
FROM analytics.brand_monthly_performance 
WHERE month >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '12 months')
  AND extracted_brand IN ('Nike', 'Nike Jordan', 'Adidas', 'Mattel', 'Off-White', 'ASICS')
ORDER BY month;

-- Table 2: Nike Produktlinien Performance
SELECT 
  nike_line as "Nike Linie",
  total_sales as "Verkäufe",
  ROUND(total_revenue::numeric, 2) as "Umsatz €",
  ROUND(avg_price::numeric, 2) as "Ø Preis €",
  unique_products as "Produkte",
  first_sale::date as "Erster Verkauf",
  last_sale::date as "Letzter Verkauf"
FROM analytics.nike_product_breakdown 
ORDER BY total_revenue DESC;

-- Chart 3: Nike Line Performance (Bar Chart)
SELECT 
  nike_line as "Nike Linie",
  total_revenue as "Umsatz €"
FROM analytics.nike_product_breakdown 
ORDER BY total_revenue DESC;

-- =============================================================================
-- 🏪 PLATFORM ANALYTICS QUERIES  
-- =============================================================================

-- KPI 1: StockX Gesamt-Umsatz
SELECT ROUND(total_revenue::numeric, 2) as "StockX Umsatz €"
FROM analytics.platform_performance 
WHERE LOWER(platform_name) = 'stockx';

-- KPI 2: StockX Transaktionen
SELECT total_transactions as "StockX Transaktionen"
FROM analytics.platform_performance 
WHERE LOWER(platform_name) = 'stockx';

-- KPI 3: StockX Ø Transaktionswert
SELECT ROUND(avg_transaction_value::numeric, 2) as "Ø Transaktionswert €"
FROM analytics.platform_performance 
WHERE LOWER(platform_name) = 'stockx';

-- KPI 4: StockX Gebühren bezahlt
SELECT ROUND(total_fees_paid::numeric, 2) as "Gebühren bezahlt €"
FROM analytics.platform_performance 
WHERE LOWER(platform_name) = 'stockx';

-- Table 1: Platform Performance Übersicht
SELECT 
  platform_name as "Plattform",
  total_transactions as "Transaktionen",
  ROUND(total_revenue::numeric, 2) as "Umsatz €",
  ROUND(avg_transaction_value::numeric, 2) as "Ø Wert €",
  ROUND(total_fees_paid::numeric, 2) as "Gebühren €"
FROM analytics.platform_performance 
ORDER BY total_revenue DESC;

-- Chart 1: Platform Umsatzverteilung (Donut Chart)
SELECT 
  platform_name as "Plattform",
  total_revenue as "Umsatz €"
FROM analytics.platform_performance 
ORDER BY total_revenue DESC;

-- =============================================================================
-- 🌍 GEOGRAPHIC ANALYTICS QUERIES
-- =============================================================================

-- Table 1: Top Zielländer
SELECT 
  destination_country as "Land",
  total_sales as "Verkäufe",
  ROUND(total_revenue::numeric, 2) as "Umsatz €",
  ROUND(avg_order_value::numeric, 2) as "Ø Bestellwert €"
FROM analytics.sales_by_country 
WHERE destination_country != 'Unknown' AND destination_country IS NOT NULL
ORDER BY total_revenue DESC 
LIMIT 20;

-- Chart 1: Revenue nach Land (Bar Chart)
SELECT 
  destination_country as "Land",
  total_revenue as "Umsatz €"
FROM analytics.sales_by_country 
WHERE destination_country != 'Unknown' AND destination_country IS NOT NULL
ORDER BY total_revenue DESC 
LIMIT 15;

-- Chart 2: Verkäufe nach Land (Bar Chart)  
SELECT 
  destination_country as "Land",
  total_sales as "Verkäufe"
FROM analytics.sales_by_country 
WHERE destination_country != 'Unknown' AND destination_country IS NOT NULL
ORDER BY total_sales DESC 
LIMIT 15;

-- =============================================================================
-- ⏰ TIME ANALYTICS QUERIES
-- =============================================================================

-- Chart 1: Täglicher Umsatz - Letzte 30 Tage (Line Chart)
SELECT 
  sale_date as "Datum",
  gross_revenue as "Umsatz €",
  transactions_count as "Transaktionen",
  avg_order_value as "Ø Bestellwert €"
FROM analytics.daily_revenue 
WHERE sale_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY sale_date;

-- Chart 2: Täglicher Umsatz - Letzte 90 Tage (Line Chart)
SELECT 
  sale_date as "Datum",
  gross_revenue as "Umsatz €"
FROM analytics.daily_revenue 
WHERE sale_date >= CURRENT_DATE - INTERVAL '90 days'
ORDER BY sale_date;

-- Chart 3: Umsatz nach Wochentag (Bar Chart)
SELECT 
  day_of_week_name as "Wochentag",
  ROUND(total_revenue::numeric, 2) as "Umsatz €",
  total_sales as "Transaktionen"
FROM analytics.sales_by_weekday 
ORDER BY day_of_week_num;

-- Chart 4: Transaktionen nach Wochentag (Bar Chart)
SELECT 
  day_of_week_name as "Wochentag",
  total_sales as "Transaktionen"
FROM analytics.sales_by_weekday 
ORDER BY day_of_week_num;

-- Table 1: Tägliche Performance Übersicht
SELECT 
  sale_date as "Datum",
  transactions_count as "Transaktionen",
  ROUND(gross_revenue::numeric, 2) as "Umsatz €",
  ROUND(avg_order_value::numeric, 2) as "Ø Bestellwert €"
FROM analytics.daily_revenue 
ORDER BY sale_date DESC 
LIMIT 30;

-- =============================================================================
-- 🔍 ADVANCED ANALYTICS QUERIES
-- =============================================================================

-- Query 1: Top Performing Produkt-Brand Kombinationen
SELECT 
  p.product_name as "Produkt",
  b.extracted_brand as "Marke", 
  COUNT(t.id) as "Verkäufe",
  ROUND(SUM(t.sale_price)::numeric, 2) as "Umsatz €",
  ROUND(AVG(t.sale_price)::numeric, 2) as "Ø Preis €"
FROM sales.transactions t
JOIN products.inventory i ON t.inventory_id = i.id
JOIN products.products p ON i.product_id = p.id
JOIN analytics.brand_deep_dive_overview b ON b.extracted_brand != 'Other/Unknown'
WHERE p.name ILIKE '%' || SPLIT_PART(b.extracted_brand, ' ', 1) || '%'
GROUP BY p.product_name, b.extracted_brand
HAVING COUNT(t.id) >= 5
ORDER BY SUM(t.sale_price) DESC
LIMIT 20;

-- Query 2: Saisonale Trends (Quartal)
SELECT 
  EXTRACT(YEAR FROM transaction_date) as "Jahr",
  EXTRACT(QUARTER FROM transaction_date) as "Quartal",
  COUNT(*) as "Transaktionen",
  ROUND(SUM(sale_price)::numeric, 2) as "Umsatz €",
  ROUND(AVG(sale_price)::numeric, 2) as "Ø Preis €"
FROM sales.transactions
GROUP BY EXTRACT(YEAR FROM transaction_date), EXTRACT(QUARTER FROM transaction_date)
ORDER BY "Jahr" DESC, "Quartal" DESC;

-- Query 3: Preis-Performance Analyse
SELECT 
  CASE 
    WHEN sale_price < 50 THEN '€0-49'
    WHEN sale_price < 100 THEN '€50-99'
    WHEN sale_price < 150 THEN '€100-149'
    WHEN sale_price < 200 THEN '€150-199'
    ELSE '€200+'
  END as "Preisbereich",
  COUNT(*) as "Transaktionen",
  ROUND(SUM(sale_price)::numeric, 2) as "Umsatz €",
  ROUND(AVG(sale_price)::numeric, 2) as "Ø Preis €"
FROM sales.transactions
GROUP BY 1
ORDER BY 
  CASE 
    WHEN sale_price < 50 THEN 1
    WHEN sale_price < 100 THEN 2
    WHEN sale_price < 150 THEN 3
    WHEN sale_price < 200 THEN 4
    ELSE 5
  END;

-- Query 4: Monatliche Growth Rate Details
WITH monthly_stats AS (
  SELECT 
    DATE_TRUNC('month', transaction_date) as month,
    COUNT(*) as transactions,
    SUM(sale_price) as revenue,
    AVG(sale_price) as avg_price
  FROM sales.transactions
  GROUP BY DATE_TRUNC('month', transaction_date)
),
growth_rates AS (
  SELECT 
    month,
    transactions,
    revenue,
    avg_price,
    LAG(revenue) OVER (ORDER BY month) as prev_revenue,
    LAG(transactions) OVER (ORDER BY month) as prev_transactions,
    LAG(avg_price) OVER (ORDER BY month) as prev_avg_price
  FROM monthly_stats
)
SELECT 
  TO_CHAR(month, 'YYYY-MM') as "Monat",
  transactions as "Transaktionen",
  ROUND(revenue::numeric, 2) as "Umsatz €",
  ROUND(avg_price::numeric, 2) as "Ø Preis €",
  CASE 
    WHEN prev_revenue > 0 THEN 
      ROUND(((revenue - prev_revenue) / prev_revenue * 100)::numeric, 1)
    ELSE NULL 
  END as "Umsatz Wachstum %",
  CASE 
    WHEN prev_transactions > 0 THEN 
      ROUND(((transactions - prev_transactions) / prev_transactions::numeric * 100)::numeric, 1)
    ELSE NULL 
  END as "Transaktions Wachstum %"
FROM growth_rates
ORDER BY month DESC;

-- =============================================================================
-- 💡 UTILITY QUERIES FÜR DEBUGGING
-- =============================================================================

-- Check verfügbare Views
SELECT 
  schemaname,
  viewname,
  definition
FROM pg_views 
WHERE schemaname = 'analytics'
ORDER BY viewname;

-- Check Datenqualität
SELECT 
  'Transaktionen ohne Produkt' as check_type,
  COUNT(*) as count
FROM sales.transactions t
LEFT JOIN products.inventory i ON t.inventory_id = i.id
WHERE i.id IS NULL

UNION ALL

SELECT 
  'Transaktionen ohne Platform' as check_type,
  COUNT(*) as count
FROM sales.transactions t
LEFT JOIN core.platforms p ON t.platform_id = p.id
WHERE p.id IS NULL

UNION ALL

SELECT 
  'Produkte ohne Brand' as check_type,
  COUNT(*) as count
FROM products.products p
LEFT JOIN core.brands b ON p.brand_id = b.id
WHERE b.id IS NULL;

-- Performance Check
SELECT 
  viewname as "View Name",
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||viewname)) as "Size"
FROM pg_views 
WHERE schemaname = 'analytics'
ORDER BY pg_total_relation_size(schemaname||'.'||viewname) DESC;
-- ================================
-- SoleFlipper Quick Database Improvements  
-- Sofort umsetzbare Performance & Feature Upgrades
-- ================================

-- 1. PERFORMANCE INDIZES (Sofort ausführbar)
-- ================================

-- Transaktions-Performance verbessern
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_date_platform 
ON sales.transactions(transaction_date DESC, platform_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_profit 
ON sales.transactions(net_profit DESC) WHERE net_profit IS NOT NULL;

-- Product Search Optimization
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_name_search 
ON products.products USING gin(name gin_trgm_ops);

-- Inventory Queries beschleunigen
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inventory_status_updated 
ON products.inventory(status, updated_at DESC);

-- External ID Lookups (für n8n/API)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_external_id 
ON sales.transactions USING gin(external_id gin_trgm_ops);

-- 2. BUYER MANAGEMENT (Einfache Erweiterung)
-- ================================

CREATE TABLE IF NOT EXISTS sales.buyers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Basic Info
    email VARCHAR(255),
    name VARCHAR(200),
    phone VARCHAR(50),
    
    -- Location (aus bestehenden Transaction-Daten)
    country VARCHAR(100),
    city VARCHAR(100),
    
    -- Auto-calculated Stats
    total_purchases INTEGER DEFAULT 0,
    lifetime_value NUMERIC(12,2) DEFAULT 0,
    first_purchase_date DATE,
    last_purchase_date DATE,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Buyer zu Transactions verknüpfen
ALTER TABLE sales.transactions 
ADD COLUMN IF NOT EXISTS buyer_id UUID REFERENCES sales.buyers(id);

-- Index für Buyer Lookups
CREATE INDEX IF NOT EXISTS idx_buyers_email ON sales.buyers(email);

-- 3. EXPENSE TRACKING (Profit verbessern)
-- ================================

CREATE SCHEMA IF NOT EXISTS finance;

CREATE TABLE IF NOT EXISTS finance.expenses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Basic Info
    description TEXT NOT NULL,
    amount NUMERIC(10,2) NOT NULL,
    expense_date DATE NOT NULL DEFAULT CURRENT_DATE,
    
    -- Categorization
    category VARCHAR(50) DEFAULT 'other', -- 'shipping', 'storage', 'marketing', 'tools'
    
    -- Business Logic
    is_business_expense BOOLEAN DEFAULT true,
    
    -- Optional Linking
    transaction_id UUID REFERENCES sales.transactions(id),
    
    -- Metadata
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_expenses_date_category 
ON finance.expenses(expense_date DESC, category);

-- 4. AUDIT TRAIL (Sicherheit für n8n)
-- ================================

CREATE SCHEMA IF NOT EXISTS audit;

CREATE TABLE IF NOT EXISTS audit.change_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- What Changed
    table_name VARCHAR(100) NOT NULL,
    record_id UUID NOT NULL,
    operation VARCHAR(20) NOT NULL, -- INSERT, UPDATE, DELETE
    
    -- Changes
    old_values JSONB,
    new_values JSONB,
    
    -- Context
    changed_by VARCHAR(255) DEFAULT current_user,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(100) DEFAULT 'unknown', -- 'api', 'n8n', 'manual'
    
    -- Metadata
    user_agent TEXT,
    ip_address INET
);

CREATE INDEX IF NOT EXISTS idx_audit_table_date 
ON audit.change_log(table_name, changed_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_record 
ON audit.change_log(record_id, changed_at DESC);

-- 5. QUICK ANALYTICS VIEWS
-- ================================

CREATE SCHEMA IF NOT EXISTS analytics;

-- Daily Sales Summary
CREATE OR REPLACE VIEW analytics.daily_sales AS
SELECT 
    DATE(transaction_date) as sale_date,
    COUNT(*) as transactions,
    SUM(sale_price) as total_revenue,
    SUM(net_profit) as total_profit,
    AVG(sale_price) as avg_price,
    AVG(net_profit) as avg_profit
FROM sales.transactions 
WHERE status = 'completed'
  AND transaction_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(transaction_date)
ORDER BY sale_date DESC;

-- Top Products by Profit
CREATE OR REPLACE VIEW analytics.top_products AS
SELECT 
    p.name,
    p.sku,
    COUNT(t.*) as sales_count,
    SUM(t.sale_price) as total_revenue,
    SUM(t.net_profit) as total_profit,
    AVG(t.sale_price) as avg_price
FROM products.products p
JOIN products.inventory i ON p.id = i.product_id
JOIN sales.transactions t ON i.id = t.inventory_id
WHERE t.status = 'completed'
  AND t.transaction_date >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY p.id, p.name, p.sku
HAVING COUNT(t.*) > 0
ORDER BY total_profit DESC
LIMIT 20;

-- 6. UTILITY FUNCTIONS
-- ================================

-- Function: Auto-create buyer from transaction
CREATE OR REPLACE FUNCTION create_buyer_from_transaction(trans_id UUID)
RETURNS UUID AS $$
DECLARE
    buyer_id UUID;
    trans_rec RECORD;
BEGIN
    -- Get transaction data
    SELECT 
        buyer_destination_country,
        buyer_destination_city,
        transaction_date
    INTO trans_rec
    FROM sales.transactions 
    WHERE id = trans_id;
    
    -- Create or find buyer
    INSERT INTO sales.buyers (
        country, 
        city, 
        first_purchase_date,
        total_purchases,
        lifetime_value
    ) VALUES (
        trans_rec.buyer_destination_country,
        trans_rec.buyer_destination_city,
        DATE(trans_rec.transaction_date),
        1,
        (SELECT sale_price FROM sales.transactions WHERE id = trans_id)
    )
    ON CONFLICT DO NOTHING
    RETURNING id INTO buyer_id;
    
    -- Update transaction
    UPDATE sales.transactions 
    SET buyer_id = buyer_id 
    WHERE id = trans_id;
    
    RETURN buyer_id;
END;
$$ LANGUAGE plpgsql;

-- 7. MONTHLY SUMMARY MATERIALIZED VIEW  
-- ================================

CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.monthly_summary AS
SELECT 
    DATE_TRUNC('month', transaction_date) as month,
    COUNT(*) as transactions,
    SUM(sale_price) as revenue,
    SUM(net_profit) as profit,
    AVG(sale_price) as avg_sale_price,
    COUNT(DISTINCT inventory_id) as unique_products_sold
FROM sales.transactions 
WHERE status = 'completed'
GROUP BY DATE_TRUNC('month', transaction_date)
ORDER BY month DESC;

-- Index für Monthly View
CREATE INDEX IF NOT EXISTS idx_monthly_summary_month 
ON analytics.monthly_summary(month DESC);

-- Auto-refresh function
CREATE OR REPLACE FUNCTION refresh_monthly_summary()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.monthly_summary;
END;
$$ LANGUAGE plpgsql;

-- 8. QUICK DATA QUALITY CHECKS
-- ================================

-- View: Data Quality Issues
CREATE OR REPLACE VIEW analytics.data_quality_check AS
SELECT 
    'Missing Net Profit' as issue,
    COUNT(*) as count
FROM sales.transactions 
WHERE net_profit IS NULL AND status = 'completed'

UNION ALL

SELECT 
    'Products without SKU' as issue,
    COUNT(*) as count
FROM products.products 
WHERE sku IS NULL OR sku = ''

UNION ALL

SELECT 
    'Inventory without Size' as issue,
    COUNT(*) as count
FROM products.inventory 
WHERE size_id IS NULL

UNION ALL

SELECT 
    'Recent Transactions without Buyer Info' as issue,
    COUNT(*) as count
FROM sales.transactions 
WHERE buyer_destination_country IS NULL 
  AND transaction_date >= CURRENT_DATE - INTERVAL '30 days';

-- ================================
-- INSTALLATION COMPLETED!
-- 
-- Next Steps:
-- 1. Run this script: psql -f quick_db_improvements.sql
-- 2. Test performance with existing queries
-- 3. Update n8n workflows to use new buyer/expense tables
-- 4. Setup regular refresh: SELECT refresh_monthly_summary();
-- ================================
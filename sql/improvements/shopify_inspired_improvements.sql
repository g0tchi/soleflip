-- ================================
-- SoleFlipper: Shopify-Inspired Product Management 
-- Erweiterte Produktverwaltung nach Shopify-Vorbild
-- ================================

-- 1. ERWEITERTE PRODUCT-TABELLE (Shopify-Style)
-- ================================

-- Add missing Shopify-style columns to existing products table
ALTER TABLE products.products 
ADD COLUMN IF NOT EXISTS handle VARCHAR(255) UNIQUE, -- URL-friendly identifier
ADD COLUMN IF NOT EXISTS vendor VARCHAR(255), -- Brand or Manufacturer 
ADD COLUMN IF NOT EXISTS product_type VARCHAR(255), -- "Sneakers", "Apparel", etc.
ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active', -- active, archived, draft
ADD COLUMN IF NOT EXISTS tags TEXT, -- Searchable tags
ADD COLUMN IF NOT EXISTS seo_title VARCHAR(255),
ADD COLUMN IF NOT EXISTS seo_description TEXT,
ADD COLUMN IF NOT EXISTS published_at TIMESTAMP;

-- Generate handles for existing products
UPDATE products.products 
SET handle = LOWER(REGEXP_REPLACE(REGEXP_REPLACE(name, '[^a-zA-Z0-9\s-]', '', 'g'), '\s+', '-', 'g'))
WHERE handle IS NULL;

-- Set vendor from brand relationship
UPDATE products.products p
SET vendor = b.name
FROM core.brands b
WHERE p.brand_id = b.id AND p.vendor IS NULL;

-- 2. PRODUCT VARIANTS TABELLE (Shopify-Herzstück)
-- ================================

CREATE TABLE IF NOT EXISTS products.product_variants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products.products(id) ON DELETE CASCADE,
    
    -- Variant Identity (Shopify-style)
    title VARCHAR(255), -- "Size 10", "Size 42 EU"
    option1 VARCHAR(255), -- Primary option (usually Size)
    option2 VARCHAR(255), -- Secondary option (Color, if applicable)  
    option3 VARCHAR(255), -- Tertiary option (Material, etc.)
    sku VARCHAR(255),
    barcode VARCHAR(255),
    
    -- Pricing (Shopify-style)
    price NUMERIC(10,2), -- Current selling price
    compare_at_price NUMERIC(10,2), -- MSRP / Crossed-out price
    cost_price NUMERIC(10,2), -- Purchase/wholesale price
    
    -- Physical Properties
    weight_grams INTEGER,
    requires_shipping BOOLEAN DEFAULT true,
    taxable BOOLEAN DEFAULT true,
    
    -- Inventory Management
    inventory_policy VARCHAR(20) DEFAULT 'deny', -- deny, continue
    inventory_management VARCHAR(50) DEFAULT 'soleflip', -- soleflip, manual, none
    track_quantity BOOLEAN DEFAULT true,
    
    -- Availability
    available BOOLEAN DEFAULT true,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_variants_product_id ON products.product_variants(product_id);
CREATE INDEX IF NOT EXISTS idx_variants_sku ON products.product_variants(sku);
CREATE UNIQUE INDEX IF NOT EXISTS idx_variants_sku_unique ON products.product_variants(sku) WHERE sku IS NOT NULL;

-- 3. PRODUCT OPTIONS TABELLE
-- ================================

CREATE TABLE IF NOT EXISTS products.product_options (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products.products(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL, -- "Size", "Color", "Material"
    position INTEGER DEFAULT 1, -- Display order
    values JSONB, -- ["7", "7.5", "8", "8.5"] or ["Red", "Blue"]
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_options_product_id ON products.product_options(product_id);

-- 4. LOCATIONS (Multi-Warehouse Support)  
-- ================================

CREATE TABLE IF NOT EXISTS inventory.locations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    
    -- Address
    address1 VARCHAR(255),
    address2 VARCHAR(255), 
    city VARCHAR(100),
    province VARCHAR(100),
    country VARCHAR(100),
    zip VARCHAR(20),
    
    -- Location Type
    location_type VARCHAR(50) DEFAULT 'warehouse', -- warehouse, store, dropship
    
    -- Settings
    active BOOLEAN DEFAULT true,
    legacy BOOLEAN DEFAULT false,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create default location
INSERT INTO inventory.locations (name, city, country, location_type)
VALUES ('Main Warehouse', 'Your City', 'Germany', 'warehouse')
ON CONFLICT DO NOTHING;

-- 5. INVENTORY LEVELS (Location-based Stock)
-- ================================

CREATE TABLE IF NOT EXISTS inventory.inventory_levels (
    inventory_item_id UUID REFERENCES products.inventory(id) ON DELETE CASCADE,
    location_id UUID REFERENCES inventory.locations(id) ON DELETE CASCADE,
    
    -- Stock Levels (Shopify-style)
    available INTEGER DEFAULT 0, -- Available for sale
    reserved INTEGER DEFAULT 0,  -- Reserved for pending orders
    committed INTEGER DEFAULT 0, -- Allocated to confirmed orders
    damaged INTEGER DEFAULT 0,   -- Damaged stock
    
    -- Reorder Management
    reorder_point INTEGER DEFAULT 0,
    reorder_quantity INTEGER DEFAULT 0,
    
    -- Metadata
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (inventory_item_id, location_id)
);

-- 6. MIGRATE EXISTING DATA TO NEW STRUCTURE
-- ================================

-- Create default product options for existing products
INSERT INTO products.product_options (product_id, name, values)
SELECT DISTINCT 
    p.id,
    'Size',
    json_agg(DISTINCT s.value ORDER BY s.value) 
FROM products.products p
JOIN products.inventory i ON p.id = i.product_id
JOIN core.sizes s ON i.size_id = s.id
GROUP BY p.id
ON CONFLICT DO NOTHING;

-- Create variants from existing inventory
INSERT INTO products.product_variants (
    product_id, 
    title, 
    option1, 
    sku,
    price,
    cost_price,
    available
)
SELECT DISTINCT
    i.product_id,
    'Size ' || s.value,
    s.value,
    p.sku || '-' || s.value, -- Create unique variant SKU
    COALESCE(i.purchase_price, 0.00),
    i.purchase_price,
    CASE WHEN i.status = 'available' THEN true ELSE false END
FROM products.inventory i
JOIN products.products p ON i.product_id = p.id
JOIN core.sizes s ON i.size_id = s.id
ON CONFLICT DO NOTHING;

-- 7. SHOPIFY-STYLE PRODUCT VIEWS
-- ================================

-- Product with Variants Overview
CREATE OR REPLACE VIEW products.products_with_variants AS
SELECT 
    p.id,
    p.name,
    p.handle,
    p.vendor,
    p.product_type,
    p.status,
    COUNT(pv.id) as variant_count,
    MIN(pv.price) as price_min,
    MAX(pv.price) as price_max,
    SUM(CASE WHEN pv.available THEN 1 ELSE 0 END) as available_variants,
    array_agg(DISTINCT pv.option1 ORDER BY pv.option1) as available_sizes
FROM products.products p
LEFT JOIN products.product_variants pv ON p.id = pv.product_id
GROUP BY p.id, p.name, p.handle, p.vendor, p.product_type, p.status;

-- Inventory Summary per Location
CREATE OR REPLACE VIEW inventory.stock_summary AS
SELECT 
    l.name as location_name,
    p.name as product_name,
    pv.title as variant_title,
    pv.sku,
    il.available,
    il.reserved,
    il.committed,
    (il.available + il.reserved + il.committed) as total_stock
FROM inventory.inventory_levels il
JOIN inventory.locations l ON il.location_id = l.id
JOIN products.inventory i ON il.inventory_item_id = i.id
JOIN products.products p ON i.product_id = p.id
LEFT JOIN products.product_variants pv ON p.id = pv.product_id;

-- Low Stock Alert (Shopify-style)
CREATE OR REPLACE VIEW inventory.low_stock_alerts AS
SELECT 
    p.name as product_name,
    pv.title as variant_title,
    l.name as location_name,
    il.available as current_stock,
    il.reorder_point,
    il.reorder_quantity,
    CASE 
        WHEN il.available <= il.reorder_point THEN 'REORDER_NOW'
        WHEN il.available <= il.reorder_point * 1.2 THEN 'LOW_STOCK'
        ELSE 'OK'
    END as alert_level
FROM inventory.inventory_levels il
JOIN inventory.locations l ON il.location_id = l.id
JOIN products.inventory i ON il.inventory_item_id = i.id
JOIN products.products p ON i.product_id = p.id
LEFT JOIN products.product_variants pv ON p.id = pv.product_id
WHERE il.available <= il.reorder_point * 1.5;

-- 8. SHOPIFY-STYLE SEARCH & FILTERING
-- ================================

-- Enhanced product search with handle and tags
CREATE INDEX IF NOT EXISTS idx_products_handle_search ON products.products USING gin(handle gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_products_tags_search ON products.products USING gin(tags gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_products_vendor ON products.products(vendor);
CREATE INDEX IF NOT EXISTS idx_products_type ON products.products(product_type);
CREATE INDEX IF NOT EXISTS idx_products_status ON products.products(status);

-- Full-text search function (Shopify-style)
CREATE OR REPLACE FUNCTION products.search_products(search_term TEXT)
RETURNS TABLE (
    id UUID,
    name VARCHAR,
    handle VARCHAR,
    vendor VARCHAR,
    product_type VARCHAR,
    match_score REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id,
        p.name,
        p.handle,
        p.vendor,
        p.product_type,
        (
            CASE WHEN p.name ILIKE '%' || search_term || '%' THEN 100 ELSE 0 END +
            CASE WHEN p.handle ILIKE '%' || search_term || '%' THEN 80 ELSE 0 END +
            CASE WHEN p.vendor ILIKE '%' || search_term || '%' THEN 60 ELSE 0 END +
            CASE WHEN p.tags ILIKE '%' || search_term || '%' THEN 40 ELSE 0 END +
            CASE WHEN p.description ILIKE '%' || search_term || '%' THEN 20 ELSE 0 END
        )::REAL as match_score
    FROM products.products p
    WHERE 
        p.status = 'active'
        AND (
            p.name ILIKE '%' || search_term || '%'
            OR p.handle ILIKE '%' || search_term || '%'
            OR p.vendor ILIKE '%' || search_term || '%'
            OR p.tags ILIKE '%' || search_term || '%'
            OR p.description ILIKE '%' || search_term || '%'
        )
    ORDER BY match_score DESC, p.name;
END;
$$ LANGUAGE plpgsql;

-- 9. ANALYTICS IMPROVEMENTS (Shopify-inspired)
-- ================================

-- Product Performance (Shopify-style)
CREATE OR REPLACE VIEW analytics.product_performance_shopify AS
SELECT 
    p.name as product_name,
    p.handle,
    p.vendor,
    p.product_type,
    COUNT(DISTINCT pv.id) as total_variants,
    COUNT(DISTINCT t.id) as total_sales,
    SUM(t.sale_price) as total_revenue,
    AVG(t.sale_price) as avg_sale_price,
    SUM(t.net_profit) as total_profit,
    AVG(t.net_profit) as avg_profit,
    (SUM(t.net_profit) / NULLIF(SUM(t.sale_price), 0) * 100) as profit_margin_pct
FROM products.products p
LEFT JOIN products.product_variants pv ON p.id = pv.product_id
LEFT JOIN products.inventory i ON p.id = i.product_id
LEFT JOIN sales.transactions t ON i.id = t.inventory_id
WHERE t.status = 'completed' OR t.id IS NULL
GROUP BY p.id, p.name, p.handle, p.vendor, p.product_type
ORDER BY total_revenue DESC NULLS LAST;

-- ================================
-- INSTALLATION COMPLETED!
-- 
-- Your SoleFlipper database now has Shopify-style:
-- • Product Variants with Options
-- • Multi-location Inventory Management  
-- • Enhanced Product Search & SEO
-- • Advanced Analytics Views
-- • Stock Level Tracking
-- 
-- Next Steps:
-- 1. Update your API to use variants instead of individual products
-- 2. Migrate existing inventory to location-based levels
-- 3. Set up reorder points for automated stock management  
-- 4. Use new search functions for better product discovery
-- ================================
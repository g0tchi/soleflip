"""
Supplier Normalization Design
============================

Current State:
- inventory_items.supplier = String(100) (free text)

Proposed State:
- core.suppliers table with normalized data
- inventory_items.supplier_id = UUID FK

Benefits:
- Better analytics and reporting
- Data consistency and validation
- Supplier performance tracking  
- Extended supplier information
"""

supplier_table_design = """
CREATE TABLE core.suppliers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    
    -- Contact Information
    contact_person VARCHAR(100),
    email VARCHAR(100),
    phone VARCHAR(50),
    website VARCHAR(200),
    
    -- Address
    address_line1 VARCHAR(200),
    address_line2 VARCHAR(200),
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(50),
    
    -- Business Information
    supplier_type VARCHAR(50), -- 'retail', 'reseller', 'private', 'wholesale', 'online'
    tax_id VARCHAR(50),
    business_registration VARCHAR(100),
    
    -- Performance & Status
    rating DECIMAL(3,2), -- 1.00 to 5.00
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'inactive', 'blocked'
    preferred BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    notes TEXT,
    tags VARCHAR(500), -- JSON array of tags
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_suppliers_name ON core.suppliers(name);
CREATE INDEX idx_suppliers_slug ON core.suppliers(slug);
CREATE INDEX idx_suppliers_type ON core.suppliers(supplier_type);
CREATE INDEX idx_suppliers_status ON core.suppliers(status);
"""

migration_steps = """
Migration Steps:
================

1. Create core.suppliers table
2. Extract unique suppliers from inventory_items.supplier
3. Create supplier records with proper normalization
4. Add supplier_id column to inventory_items
5. Update inventory_items with supplier_id references
6. Update application code to use supplier_id
7. Drop old supplier column (optional, keep for backup initially)

Data Analysis Query:
SELECT 
    supplier,
    COUNT(*) as inventory_count,
    COUNT(DISTINCT product_id) as unique_products,
    AVG(purchase_price) as avg_purchase_price,
    MIN(purchase_date) as first_purchase,
    MAX(purchase_date) as last_purchase
FROM products.inventory_items 
WHERE supplier IS NOT NULL AND supplier != ''
GROUP BY supplier
ORDER BY inventory_count DESC;
"""

analytics_benefits = """
Analytics Benefits:
==================

New Metabase Views Possible:
- supplier_performance_overview
- supplier_purchase_volume  
- supplier_geographic_analysis
- supplier_product_diversity
- supplier_profitability_analysis

Example Queries:
- Which suppliers provide the highest margin products?
- What's the purchase distribution across supplier types?
- Which suppliers have the most product diversity?
- Geographic heat map of supplier locations
- Supplier performance over time trends
"""

if __name__ == "__main__":
    print("Supplier Normalization Design")
    print("="*50)
    print(supplier_table_design)
    print(migration_steps)
    print(analytics_benefits)
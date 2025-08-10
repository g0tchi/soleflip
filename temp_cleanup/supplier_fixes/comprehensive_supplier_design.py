"""
Comprehensive Supplier Normalization Design
==========================================

Key Considerations:
- Suppliers can also be Brands (Nike Store, Adidas Official, etc.)
- Contact information and return policies are crucial
- Need to handle both B2B and individual sellers
- Return periods and policies vary by supplier type

Design Philosophy:
- Suppliers and Brands are separate entities (normalized)
- Many-to-Many relationship: Supplier can sell multiple Brands
- Brands can be sold by multiple Suppliers
- Some Suppliers ARE the Brand (Nike Store -> Nike Brand)
"""

supplier_table_sql = """
-- Create comprehensive Suppliers table
CREATE TABLE core.suppliers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Basic Information
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(150), -- "Nike Store München" vs internal "nike-store-muenchen"
    
    -- Business Classification
    supplier_type VARCHAR(50) NOT NULL, -- 'brand_official', 'authorized_retailer', 'reseller', 'private_seller', 'marketplace', 'outlet'
    business_size VARCHAR(30), -- 'enterprise', 'small_business', 'individual'
    
    -- Contact Information (very important for business)
    contact_person VARCHAR(100),
    email VARCHAR(100),
    phone VARCHAR(50),
    website VARCHAR(200),
    
    -- Address Information
    address_line1 VARCHAR(200),
    address_line2 VARCHAR(200),
    city VARCHAR(100),
    state_province VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(50) DEFAULT 'Germany',
    
    -- Business Details
    tax_id VARCHAR(50),
    vat_number VARCHAR(50),
    business_registration VARCHAR(100),
    
    -- Return Policy & Terms (crucial for reselling business!)
    return_policy_days INTEGER, -- How many days for returns
    return_policy_text TEXT, -- Detailed return policy description
    return_conditions VARCHAR(500), -- "Original packaging required, tags attached, etc."
    accepts_exchanges BOOLEAN DEFAULT TRUE,
    restocking_fee_percent DECIMAL(5,2), -- 0.00 to 100.00
    
    -- Payment & Trading Terms
    payment_terms VARCHAR(100), -- "Net 30", "Payment on delivery", "Prepayment", etc.
    credit_limit DECIMAL(12,2), -- For B2B suppliers
    discount_percent DECIMAL(5,2), -- Regular discount we get
    minimum_order_amount DECIMAL(10,2),
    
    -- Performance & Status
    rating DECIMAL(3,2), -- 1.00 to 5.00 (our internal rating)
    reliability_score INTEGER, -- 1-10 (delivery reliability)
    quality_score INTEGER, -- 1-10 (product quality)
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'inactive', 'blocked', 'pending'
    preferred BOOLEAN DEFAULT FALSE,
    verified BOOLEAN DEFAULT FALSE, -- For authentication/trust
    
    -- Operational Information
    average_processing_days INTEGER, -- How long until they ship
    ships_internationally BOOLEAN DEFAULT FALSE,
    accepts_returns_by_mail BOOLEAN DEFAULT TRUE,
    provides_authenticity_guarantee BOOLEAN DEFAULT FALSE,
    
    -- Integration & Technical
    has_api BOOLEAN DEFAULT FALSE,
    api_endpoint VARCHAR(200),
    api_key_encrypted TEXT, -- For automated ordering/tracking
    
    -- Financial Tracking
    total_orders_count INTEGER DEFAULT 0,
    total_order_value DECIMAL(12,2) DEFAULT 0.00,
    average_order_value DECIMAL(10,2),
    last_order_date TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    notes TEXT,
    internal_notes TEXT, -- Private notes not shown to staff
    tags JSONB, -- Flexible tagging: ["fast-shipping", "authentic-guarantee", "expensive"]
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_rating CHECK (rating >= 1.0 AND rating <= 5.0),
    CONSTRAINT chk_reliability_score CHECK (reliability_score >= 1 AND reliability_score <= 10),
    CONSTRAINT chk_quality_score CHECK (quality_score >= 1 AND quality_score <= 10),
    CONSTRAINT chk_return_days CHECK (return_policy_days >= 0 AND return_policy_days <= 365)
);

-- Supplier-Brand Relationship Table (Many-to-Many)
CREATE TABLE core.supplier_brands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_id UUID NOT NULL REFERENCES core.suppliers(id) ON DELETE CASCADE,
    brand_id UUID NOT NULL REFERENCES core.brands(id) ON DELETE CASCADE,
    
    -- Relationship specifics
    is_authorized_dealer BOOLEAN DEFAULT FALSE, -- Official dealer vs reseller
    is_brand_owned BOOLEAN DEFAULT FALSE, -- Nike Store -> Nike (brand owns supplier)
    primary_supplier_for_brand BOOLEAN DEFAULT FALSE, -- Our main supplier for this brand
    
    -- Performance for this specific brand
    brand_specific_discount DECIMAL(5,2),
    exclusive_access BOOLEAN DEFAULT FALSE, -- Limited editions, early access
    
    -- Status
    relationship_status VARCHAR(30) DEFAULT 'active', -- 'active', 'terminated', 'suspended'
    relationship_start_date DATE,
    relationship_end_date DATE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint
    UNIQUE(supplier_id, brand_id)
);

-- Indexes for performance
CREATE INDEX idx_suppliers_name ON core.suppliers(name);
CREATE INDEX idx_suppliers_slug ON core.suppliers(slug);
CREATE INDEX idx_suppliers_type ON core.suppliers(supplier_type);
CREATE INDEX idx_suppliers_status ON core.suppliers(status);
CREATE INDEX idx_suppliers_country ON core.suppliers(country);
CREATE INDEX idx_suppliers_preferred ON core.suppliers(preferred);
CREATE INDEX idx_suppliers_rating ON core.suppliers(rating);
CREATE INDEX idx_suppliers_tags ON core.suppliers USING GIN(tags);

CREATE INDEX idx_supplier_brands_supplier ON core.supplier_brands(supplier_id);
CREATE INDEX idx_supplier_brands_brand ON core.supplier_brands(brand_id);
CREATE INDEX idx_supplier_brands_authorized ON core.supplier_brands(is_authorized_dealer);
CREATE INDEX idx_supplier_brands_primary ON core.supplier_brands(primary_supplier_for_brand);
"""

example_data = """
-- Example Supplier Data
INSERT INTO core.suppliers (name, slug, display_name, supplier_type, business_size, contact_person, email, phone, website, city, country, return_policy_days, return_policy_text, accepts_exchanges, rating, preferred, verified) VALUES

-- Brand Official Stores
('nike-store-munich', 'nike-store-munich', 'Nike Store München', 'brand_official', 'enterprise', 'Store Manager', 'muenchen@nike.com', '+49 89 123456', 'https://nike.com/stores/munich', 'München', 'Germany', 30, 'Full refund within 30 days with original receipt', TRUE, 4.8, TRUE, TRUE),

-- Authorized Retailers  
('footlocker-germany', 'footlocker-germany', 'Foot Locker Deutschland', 'authorized_retailer', 'enterprise', 'B2B Sales', 'b2b@footlocker.de', '+49 30 987654', 'https://footlocker.de', 'Berlin', 'Germany', 14, '14 days return policy, original packaging required', TRUE, 4.5, TRUE, TRUE),

-- Resellers
('sneaker-district', 'sneaker-district', 'Sneaker District', 'reseller', 'small_business', 'Max Müller', 'info@sneakerdistrict.de', '+49 40 555123', 'https://sneakerdistrict.de', 'Hamburg', 'Germany', 7, 'No returns on limited editions, 7 days for regular items', FALSE, 4.2, FALSE, TRUE),

-- Private Sellers
('private-seller-001', 'private-seller-001', 'Hans Schmidt (Privat)', 'private_seller', 'individual', 'Hans Schmidt', 'hans.schmidt@email.com', '+49 171 1234567', NULL, 'Berlin', 'Germany', 3, 'Private sale - limited return options', FALSE, 3.8, FALSE, FALSE),

-- Marketplaces
('stockx-marketplace', 'stockx-marketplace', 'StockX Marketplace', 'marketplace', 'enterprise', 'Support Team', 'support@stockx.com', NULL, 'https://stockx.com', 'Detroit', 'USA', 3, 'Authentication service, 3 days for issues after delivery', FALSE, 4.7, TRUE, TRUE);

-- Example Supplier-Brand Relationships
INSERT INTO core.supplier_brands (supplier_id, brand_id, is_authorized_dealer, is_brand_owned, primary_supplier_for_brand, brand_specific_discount, exclusive_access) 
SELECT 
    s.id, 
    b.id,
    CASE s.supplier_type 
        WHEN 'brand_official' THEN TRUE 
        WHEN 'authorized_retailer' THEN TRUE 
        ELSE FALSE 
    END,
    CASE s.supplier_type 
        WHEN 'brand_official' THEN TRUE 
        ELSE FALSE 
    END,
    s.preferred,
    CASE s.supplier_type 
        WHEN 'brand_official' THEN 15.00 
        WHEN 'authorized_retailer' THEN 10.00 
        ELSE 0.00 
    END,
    s.supplier_type IN ('brand_official', 'authorized_retailer')
FROM core.suppliers s
CROSS JOIN core.brands b
WHERE 
    (s.slug = 'nike-store-munich' AND b.name = 'Nike') OR
    (s.slug = 'footlocker-germany' AND b.name IN ('Nike', 'Adidas', 'New Balance')) OR
    (s.slug = 'sneaker-district' AND b.name IN ('Nike', 'Adidas')) OR
    (s.slug = 'stockx-marketplace' AND b.name != 'Unknown');
"""

migration_benefits = """
Migration Benefits:
==================

1. Business Intelligence:
   - Return policy analysis by supplier type
   - Supplier performance dashboards
   - Brand-supplier relationship mapping
   - Geographic supplier distribution

2. Operational Efficiency:  
   - Quick access to supplier contact info
   - Return policy lookup for customer service
   - Supplier preference and rating system
   - Payment terms and credit management

3. Risk Management:
   - Supplier reliability tracking
   - Return policy compliance
   - Quality score monitoring
   - Verification status management

4. Growth Enablement:
   - Supplier discovery and onboarding
   - Brand partnership opportunities
   - Exclusive access tracking
   - API integration readiness

5. Customer Service:
   - Clear return policies per item
   - Authenticity guarantee information
   - Processing time expectations
   - Exchange possibility lookup
"""

print("Comprehensive Supplier Design with Brand Relationships")
print("="*60)
print(supplier_table_sql)
print("\n" + "="*60)
print("Example Data:")
print(example_data)
print("\n" + "="*60) 
print(migration_benefits)
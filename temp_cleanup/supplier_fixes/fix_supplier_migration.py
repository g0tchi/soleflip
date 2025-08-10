import asyncio
import asyncpg

async def fix_supplier_migration():
    """Fix supplier migration - manually create tables if needed"""
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        # Check if suppliers table exists
        table_exists = await conn.fetchval(
            """SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'core' 
                AND table_name = 'suppliers'
            )"""
        )
        
        if not table_exists:
            print("Creating suppliers table...")
            
            # Create suppliers table manually
            await conn.execute("""
                CREATE TABLE core.suppliers (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    
                    -- Basic Information
                    name VARCHAR(100) NOT NULL,
                    slug VARCHAR(100) NOT NULL UNIQUE,
                    display_name VARCHAR(150),
                    
                    -- Business Classification
                    supplier_type VARCHAR(50) NOT NULL,
                    business_size VARCHAR(30),
                    
                    -- Contact Information
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
                    
                    -- Return Policy & Terms
                    return_policy_days INTEGER,
                    return_policy_text TEXT,
                    return_conditions VARCHAR(500),
                    accepts_exchanges BOOLEAN DEFAULT TRUE,
                    restocking_fee_percent DECIMAL(5, 2),
                    
                    -- Payment & Trading Terms
                    payment_terms VARCHAR(100),
                    credit_limit DECIMAL(12, 2),
                    discount_percent DECIMAL(5, 2),
                    minimum_order_amount DECIMAL(10, 2),
                    
                    -- Performance & Status
                    rating DECIMAL(3, 2),
                    reliability_score INTEGER,
                    quality_score INTEGER,
                    status VARCHAR(20) NOT NULL DEFAULT 'active',
                    preferred BOOLEAN NOT NULL DEFAULT FALSE,
                    verified BOOLEAN NOT NULL DEFAULT FALSE,
                    
                    -- Operational Information
                    average_processing_days INTEGER,
                    ships_internationally BOOLEAN NOT NULL DEFAULT FALSE,
                    accepts_returns_by_mail BOOLEAN NOT NULL DEFAULT TRUE,
                    provides_authenticity_guarantee BOOLEAN NOT NULL DEFAULT FALSE,
                    
                    -- Integration & Technical
                    has_api BOOLEAN NOT NULL DEFAULT FALSE,
                    api_endpoint VARCHAR(200),
                    api_key_encrypted TEXT,
                    
                    -- Financial Tracking
                    total_orders_count INTEGER NOT NULL DEFAULT 0,
                    total_order_value DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
                    average_order_value DECIMAL(10, 2),
                    last_order_date TIMESTAMP WITH TIME ZONE,
                    
                    -- Metadata
                    notes TEXT,
                    internal_notes TEXT,
                    tags JSONB,
                    
                    -- Timestamps
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    
                    -- Constraints
                    CONSTRAINT chk_suppliers_rating CHECK (rating >= 1.0 AND rating <= 5.0),
                    CONSTRAINT chk_suppliers_reliability_score CHECK (reliability_score >= 1 AND reliability_score <= 10),
                    CONSTRAINT chk_suppliers_quality_score CHECK (quality_score >= 1 AND quality_score <= 10),
                    CONSTRAINT chk_suppliers_return_days CHECK (return_policy_days >= 0 AND return_policy_days <= 365)
                )
            """)
            
            # Create supplier_brands table
            await conn.execute("""
                CREATE TABLE core.supplier_brands (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    supplier_id UUID NOT NULL REFERENCES core.suppliers(id) ON DELETE CASCADE,
                    brand_id UUID NOT NULL REFERENCES core.brands(id) ON DELETE CASCADE,
                    
                    -- Relationship specifics
                    is_authorized_dealer BOOLEAN NOT NULL DEFAULT FALSE,
                    is_brand_owned BOOLEAN NOT NULL DEFAULT FALSE,
                    primary_supplier_for_brand BOOLEAN NOT NULL DEFAULT FALSE,
                    
                    -- Performance for this specific brand
                    brand_specific_discount DECIMAL(5, 2),
                    exclusive_access BOOLEAN NOT NULL DEFAULT FALSE,
                    
                    -- Status
                    relationship_status VARCHAR(30) NOT NULL DEFAULT 'active',
                    relationship_start_date DATE,
                    relationship_end_date DATE,
                    
                    -- Timestamps
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    
                    UNIQUE(supplier_id, brand_id)
                )
            """)
            
            # Create indexes
            await conn.execute("CREATE INDEX idx_suppliers_name ON core.suppliers(name)")
            await conn.execute("CREATE INDEX idx_suppliers_slug ON core.suppliers(slug)")
            await conn.execute("CREATE INDEX idx_suppliers_type ON core.suppliers(supplier_type)")
            await conn.execute("CREATE INDEX idx_suppliers_status ON core.suppliers(status)")
            await conn.execute("CREATE INDEX idx_suppliers_preferred ON core.suppliers(preferred)")
            await conn.execute("CREATE INDEX idx_suppliers_rating ON core.suppliers(rating)")
            
            await conn.execute("CREATE INDEX idx_supplier_brands_supplier ON core.supplier_brands(supplier_id)")
            await conn.execute("CREATE INDEX idx_supplier_brands_brand ON core.supplier_brands(brand_id)")
            
            # Add supplier_id column to inventory
            inventory_column_exists = await conn.fetchval(
                """SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_schema = 'products' 
                    AND table_name = 'inventory'
                    AND column_name = 'supplier_id'
                )"""
            )
            
            if not inventory_column_exists:
                await conn.execute(
                    "ALTER TABLE products.inventory ADD COLUMN supplier_id UUID REFERENCES core.suppliers(id)"
                )
                await conn.execute("CREATE INDEX idx_inventory_supplier ON products.inventory(supplier_id)")
            
            print("[SUCCESS] Supplier tables created successfully!")
        else:
            print("[INFO] Supplier tables already exist")
            
        # Verify table structure
        suppliers_count = await conn.fetchval("SELECT COUNT(*) FROM core.suppliers")
        print(f"Current suppliers in database: {suppliers_count}")
        
    except Exception as e:
        print(f"[ERROR] Failed to fix migration: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(fix_supplier_migration())
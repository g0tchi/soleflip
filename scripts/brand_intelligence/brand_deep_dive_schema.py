import asyncio
import asyncpg

async def create_brand_deep_dive_schema():
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    print("=== CREATING BRAND DEEP DIVE SCHEMA ===")
    
    # 1. Extend brands table with comprehensive information
    print("1. Extending brands table with deep dive fields...")
    
    await conn.execute("""
        ALTER TABLE core.brands 
        ADD COLUMN IF NOT EXISTS founder_name VARCHAR(200),
        ADD COLUMN IF NOT EXISTS headquarters_city VARCHAR(100),
        ADD COLUMN IF NOT EXISTS headquarters_country VARCHAR(50),
        ADD COLUMN IF NOT EXISTS parent_company VARCHAR(200),
        ADD COLUMN IF NOT EXISTS parent_company_id UUID,
        ADD COLUMN IF NOT EXISTS acquired_date DATE,
        ADD COLUMN IF NOT EXISTS acquired_by VARCHAR(200),
        ADD COLUMN IF NOT EXISTS market_cap_usd BIGINT,
        ADD COLUMN IF NOT EXISTS annual_revenue_usd BIGINT,
        ADD COLUMN IF NOT EXISTS employee_count INTEGER,
        ADD COLUMN IF NOT EXISTS website_url VARCHAR(300),
        ADD COLUMN IF NOT EXISTS instagram_handle VARCHAR(100),
        ADD COLUMN IF NOT EXISTS logo_url VARCHAR(500),
        ADD COLUMN IF NOT EXISTS brand_story TEXT,
        ADD COLUMN IF NOT EXISTS brand_mission TEXT,
        ADD COLUMN IF NOT EXISTS brand_values TEXT[],
        ADD COLUMN IF NOT EXISTS sustainability_score INTEGER CHECK (sustainability_score BETWEEN 1 AND 10),
        ADD COLUMN IF NOT EXISTS innovation_focus TEXT[],
        ADD COLUMN IF NOT EXISTS key_technologies TEXT[],
        ADD COLUMN IF NOT EXISTS brand_status VARCHAR(50) DEFAULT 'active', -- active, discontinued, acquired, merged
        ADD COLUMN IF NOT EXISTS authenticity_level VARCHAR(20) DEFAULT 'verified' -- verified, suspected, replica
    """)
    print("OK Extended brands table with deep dive fields")
    
    # 2. Create brand history/timeline table
    print("2. Creating brand history table...")
    
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS core.brand_history (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            brand_id UUID REFERENCES core.brands(id) ON DELETE CASCADE,
            event_date DATE NOT NULL,
            event_type VARCHAR(50) NOT NULL, -- founded, acquired, merged, ipo, collaboration, milestone, controversy
            event_title VARCHAR(200) NOT NULL,
            event_description TEXT,
            impact_level VARCHAR(20) DEFAULT 'medium', -- low, medium, high, critical
            source_url VARCHAR(500),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_brand_history_brand_date 
        ON core.brand_history(brand_id, event_date)
    """)
    print("OK Created brand_history table")
    
    # 3. Create brand relationships table (for complex ownership structures)
    print("3. Creating brand relationships table...")
    
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS core.brand_relationships (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            parent_brand_id UUID REFERENCES core.brands(id),
            child_brand_id UUID REFERENCES core.brands(id),
            relationship_type VARCHAR(50) NOT NULL, -- owns, subsidiary, joint_venture, licensing, collaboration
            ownership_percentage DECIMAL(5,2), -- 0.00 to 100.00
            relationship_start_date DATE,
            relationship_end_date DATE,
            status VARCHAR(20) DEFAULT 'active', -- active, inactive, terminated
            notes TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(parent_brand_id, child_brand_id, relationship_type)
        )
    """)
    print("OK Created brand_relationships table")
    
    # 4. Create brand collaborations table
    print("4. Creating brand collaborations table...")
    
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS core.brand_collaborations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            primary_brand_id UUID REFERENCES core.brands(id),
            collaborator_brand_id UUID REFERENCES core.brands(id),
            collaboration_name VARCHAR(200) NOT NULL,
            collaboration_type VARCHAR(50), -- limited_edition, ongoing, seasonal, one_off
            launch_date DATE,
            end_date DATE,
            description TEXT,
            success_level VARCHAR(20), -- low, medium, high, legendary
            estimated_revenue_usd BIGINT,
            limited_quantity INTEGER,
            resale_multiplier DECIMAL(4,2), -- how much resale vs retail
            hype_score INTEGER CHECK (hype_score BETWEEN 1 AND 10),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    print("OK Created brand_collaborations table")
    
    # 5. Create brand personalities/attributes table
    print("5. Creating brand attributes table...")
    
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS core.brand_attributes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            brand_id UUID REFERENCES core.brands(id) ON DELETE CASCADE,
            attribute_category VARCHAR(50) NOT NULL, -- personality, target_audience, style, quality, price_perception
            attribute_name VARCHAR(100) NOT NULL,
            attribute_value VARCHAR(200),
            confidence_score DECIMAL(3,2) CHECK (confidence_score BETWEEN 0 AND 1), -- 0.00 to 1.00
            data_source VARCHAR(100), -- manual, survey, ai_analysis, market_research
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(brand_id, attribute_category, attribute_name)
        )
    """)
    print("OK Created brand_attributes table")
    
    # 6. Create brand financial data table
    print("6. Creating brand financial history...")
    
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS core.brand_financials (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            brand_id UUID REFERENCES core.brands(id) ON DELETE CASCADE,
            fiscal_year INTEGER NOT NULL,
            revenue_usd BIGINT,
            profit_usd BIGINT,
            market_cap_usd BIGINT,
            rd_spending_usd BIGINT,
            marketing_spend_usd BIGINT,
            employee_count INTEGER,
            stores_count INTEGER,
            online_sales_percentage DECIMAL(5,2),
            growth_rate_percentage DECIMAL(6,2),
            data_source VARCHAR(100),
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(brand_id, fiscal_year)
        )
    """)
    print("OK Created brand_financials table")
    
    # 7. Create indexes for performance
    print("7. Creating performance indexes...")
    
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_brands_founder ON core.brands(founder_name)",
        "CREATE INDEX IF NOT EXISTS idx_brands_parent_company ON core.brands(parent_company)",
        "CREATE INDEX IF NOT EXISTS idx_brands_country ON core.brands(country_origin)",
        "CREATE INDEX IF NOT EXISTS idx_brands_status ON core.brands(brand_status)",
        "CREATE INDEX IF NOT EXISTS idx_brand_attributes_category ON core.brand_attributes(attribute_category)",
        "CREATE INDEX IF NOT EXISTS idx_collaborations_date ON core.brand_collaborations(launch_date)",
    ]
    
    for idx_query in indexes:
        await conn.execute(idx_query)
    
    print("OK Created performance indexes")
    
    print("\n=== BRAND DEEP DIVE SCHEMA CREATED ===")
    print("New capabilities:")
    print("- Complete brand histories and timelines")
    print("- Complex ownership and relationship mapping")
    print("- Collaboration tracking and analysis") 
    print("- Brand personality and attribute profiling")
    print("- Financial performance history")
    print("- Sustainability and innovation tracking")
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(create_brand_deep_dive_schema())
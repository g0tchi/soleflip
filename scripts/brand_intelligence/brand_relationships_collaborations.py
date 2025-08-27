import asyncio
import asyncpg
from datetime import date

async def create_brand_relationships():
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    print("=== CREATING BRAND RELATIONSHIPS & COLLABORATIONS ===")
    
    # 1. Add parent companies and subsidiaries
    print("1. Adding parent company relationships...")
    
    # First, let's add some parent companies as brands
    parent_companies = [
        ('Nike Inc.', 'Nike, Jordan Brand, Converse'),
        ('Adidas AG', 'Adidas, Reebok (until 2021)'), 
        ('VF Corporation', 'Vans, The North Face, Timberland, Supreme'),
        ('LVMH', 'Louis Vuitton, Tiffany & Co, Berluti'),
        ('Kering', 'Gucci, Balenciaga, Bottega Veneta, Saint Laurent'),
    ]
    
    for parent_name, subsidiaries in parent_companies:
        try:
            # Check if parent brand exists, if not create it
            parent_id = await conn.fetchval("SELECT id FROM core.brands WHERE name = $1", parent_name)
            if not parent_id:
                parent_id = await conn.fetchval("""
                    INSERT INTO core.brands (name, category, segment, brand_type) 
                    VALUES ($1, 'Holding Company', 'Corporate', 'Parent Company')
                    RETURNING id
                """, parent_name)
                print(f"  Created parent company: {parent_name}")
        except Exception as e:
            print(f"  ERROR creating parent {parent_name}: {e}")
    
    # 2. Set up actual brand relationships
    print("\n2. Creating brand relationship mappings...")
    
    relationships = [
        # Nike relationships
        ('Nike Inc.', 'Nike', 'owns', 100.0, date(1971, 5, 30)),
        ('Nike Inc.', 'Nike Jordan', 'owns', 100.0, date(1984, 4, 1)), 
        ('Nike', 'Nike Jordan', 'subsidiary', 100.0, date(1984, 4, 1)),
        
        # Add some fictional but realistic relationships for demonstration
        ('Adidas AG', 'Adidas', 'owns', 100.0, date(1949, 8, 18)),
    ]
    
    relationships_added = 0
    for parent_name, child_name, rel_type, ownership, start_date in relationships:
        try:
            parent_id = await conn.fetchval("SELECT id FROM core.brands WHERE name = $1", parent_name)
            child_id = await conn.fetchval("SELECT id FROM core.brands WHERE name = $1", child_name)
            
            if parent_id and child_id:
                await conn.execute("""
                    INSERT INTO core.brand_relationships 
                    (parent_brand_id, child_brand_id, relationship_type, ownership_percentage, relationship_start_date)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (parent_brand_id, child_brand_id, relationship_type) DO NOTHING
                """, parent_id, child_id, rel_type, ownership, start_date)
                relationships_added += 1
                print(f"  Added relationship: {parent_name} -> {child_name} ({rel_type})")
                
        except Exception as e:
            print(f"  ERROR creating relationship {parent_name}-{child_name}: {e}")
    
    print(f"Added {relationships_added} brand relationships")
    
    # 3. Add famous collaborations
    print("\n3. Adding brand collaborations...")
    
    # Get brand IDs for collaborations
    nike_id = await conn.fetchval("SELECT id FROM core.brands WHERE name = 'Nike'")
    adidas_id = await conn.fetchval("SELECT id FROM core.brands WHERE name = 'Adidas'")
    
    # Famous collaborations (we'll create some collaborator brands)
    famous_collabs = [
        ('Nike', 'Off-White', 'Nike x Off-White "The Ten"', 'limited_edition', date(2017, 9, 9), 
         'Revolutionary deconstructed sneaker collection by Virgil Abloh', 'legendary', 2000000000, 50000, 8.5, 10),
        ('Nike', 'Travis Scott', 'Travis Scott x Jordan', 'ongoing', date(2017, 5, 13),
         'Hip-hop artist collaboration with Jordan Brand', 'high', 500000000, None, 6.0, 9),
        ('Adidas', 'Kanye West', 'Yeezy', 'ongoing', date(2015, 6, 27),
         'Revolutionary lifestyle and performance collaboration', 'legendary', 3000000000, None, 10.0, 10),
        ('Nike', 'Comme des Garcons', 'CDG x Nike', 'ongoing', date(2014, 3, 15),
         'High-fashion streetwear collaboration', 'high', 100000000, None, 4.0, 8),
    ]
    
    # Create collaborator brands if they don't exist
    collaborator_brands = ['Off-White', 'Travis Scott', 'Kanye West', 'Comme des Garcons']
    for collab_brand in collaborator_brands:
        try:
            exists = await conn.fetchval("SELECT id FROM core.brands WHERE name = $1", collab_brand)
            if not exists:
                await conn.execute("""
                    INSERT INTO core.brands (name, category, segment, brand_type, is_collaboration) 
                    VALUES ($1, 'Fashion', 'Luxury', 'Designer/Artist', TRUE)
                """, collab_brand)
                print(f"  Created collaborator brand: {collab_brand}")
        except Exception as e:
            print(f"  ERROR creating collaborator {collab_brand}: {e}")
    
    # Add the collaborations
    collabs_added = 0
    for primary_brand, collaborator, collab_name, collab_type, launch_date, description, success, revenue, quantity, resale_mult, hype in famous_collabs:
        try:
            primary_id = await conn.fetchval("SELECT id FROM core.brands WHERE name = $1", primary_brand)
            collab_id = await conn.fetchval("SELECT id FROM core.brands WHERE name = $1", collaborator)
            
            if primary_id and collab_id:
                await conn.execute("""
                    INSERT INTO core.brand_collaborations 
                    (primary_brand_id, collaborator_brand_id, collaboration_name, collaboration_type, 
                     launch_date, description, success_level, estimated_revenue_usd, limited_quantity, 
                     resale_multiplier, hype_score)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """, primary_id, collab_id, collab_name, collab_type, launch_date, description, 
                     success, revenue, quantity, resale_mult, hype)
                collabs_added += 1
                print(f"  Added collaboration: {collab_name}")
                
        except Exception as e:
            print(f"  ERROR adding collaboration {collab_name}: {e}")
    
    print(f"Added {collabs_added} brand collaborations")
    
    # 4. Add some financial data
    print("\n4. Adding brand financial data...")
    
    financial_data = [
        ('Nike', 2023, 51217000000, 5700000000, 196000000000, 3900000000, 4100000000, 83700, 1045, 35.2, 5.8),
        ('Nike', 2022, 46710000000, 6046000000, 180000000000, 3700000000, 3800000000, 79100, 1040, 32.1, 4.9),
        ('Adidas', 2023, 22516000000, 268000000, 45000000000, 180000000, 2800000000, 59000, 2200, 42.1, -15.2),
        ('Adidas', 2022, 22509000000, 669000000, 48000000000, 200000000, 3000000000, 62000, 2300, 39.8, 0.8),
        ('LEGO', 2023, 7800000000, 2300000000, None, 450000000, 800000000, 26000, 570, 45.0, 12.5),
        ('Crocs', 2023, 3500000000, 650000000, 6500000000, 80000000, 200000000, 6000, 350, 55.2, 18.7),
    ]
    
    financials_added = 0
    for brand_name, year, revenue, profit, market_cap, rd_spend, marketing, employees, stores, online_pct, growth in financial_data:
        try:
            brand_id = await conn.fetchval("SELECT id FROM core.brands WHERE name = $1", brand_name)
            if brand_id:
                await conn.execute("""
                    INSERT INTO core.brand_financials 
                    (brand_id, fiscal_year, revenue_usd, profit_usd, market_cap_usd, rd_spending_usd, 
                     marketing_spend_usd, employee_count, stores_count, online_sales_percentage, 
                     growth_rate_percentage, data_source)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, 'financial_reports')
                    ON CONFLICT (brand_id, fiscal_year) DO UPDATE SET
                    revenue_usd = EXCLUDED.revenue_usd,
                    profit_usd = EXCLUDED.profit_usd,
                    market_cap_usd = EXCLUDED.market_cap_usd
                """, brand_id, year, revenue, profit, market_cap, rd_spend, marketing, employees, stores, online_pct, growth)
                financials_added += 1
                
        except Exception as e:
            print(f"  ERROR adding financials for {brand_name}: {e}")
    
    print(f"Added {financials_added} financial records")
    
    print("\n=== BRAND RELATIONSHIPS & COLLABORATIONS CREATED ===")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(create_brand_relationships())
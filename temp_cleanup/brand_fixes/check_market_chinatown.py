import asyncio
import asyncpg

async def check_market_chinatown():
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        # Check if Market or Chinatown Market brand exists
        market_brands = await conn.fetch("""
            SELECT id, name FROM core.brands 
            WHERE name ILIKE '%market%' OR name ILIKE '%chinatown%'
            ORDER BY name
        """)
        
        print("Existing Market/Chinatown brands:")
        for brand in market_brands:
            print(f"  - {brand['name']} (ID: {brand['id']})")
        
        if not market_brands:
            print("  No Market/Chinatown brands found")
        
        # Find products that should be Market/Chinatown Market
        market_products = await conn.fetch("""
            SELECT p.id, p.name, p.brand_id, b.name as current_brand
            FROM products.products p
            LEFT JOIN core.brands b ON p.brand_id = b.id
            WHERE (p.name ILIKE '%market%' OR p.name ILIKE '%chinatown market%')
            AND p.name NOT ILIKE '%marketplace%'
            AND p.name NOT ILIKE '%stockx%'
            ORDER BY p.name
            LIMIT 20
        """)
        
        print(f"\nProducts with 'Market' or 'Chinatown Market' patterns ({len(market_products)}):")
        wrong_assignments = 0
        
        for prod in market_products:
            current_brand = prod['current_brand'] if prod['current_brand'] else 'NULL'
            
            # Check if it should be assigned to an existing Market brand
            should_be_market = False
            if market_brands:
                for brand in market_brands:
                    if brand['name'].lower() in prod['name'].lower():
                        if prod['brand_id'] != brand['id']:
                            should_be_market = True
                        break
            else:
                # No Market brand exists, but product contains Market/Chinatown
                if ('market' in prod['name'].lower() or 'chinatown' in prod['name'].lower()) and prod['brand_id'] is None:
                    should_be_market = True
            
            if should_be_market or prod['brand_id'] is None:
                print(f"  *** {prod['name']} | Current Brand: {current_brand} (NEEDS ASSIGNMENT)")
                wrong_assignments += 1
            else:
                print(f"  - {prod['name']} | Current Brand: {current_brand}")
        
        # Look specifically for "Chinatown Market" (the old name)
        chinatown_products = await conn.fetch("""
            SELECT p.id, p.name, p.brand_id, b.name as current_brand
            FROM products.products p
            LEFT JOIN core.brands b ON p.brand_id = b.id
            WHERE p.name ILIKE '%chinatown market%'
            ORDER BY p.name
        """)
        
        if chinatown_products:
            print(f"\nSpecific 'Chinatown Market' products ({len(chinatown_products)}):")
            for prod in chinatown_products:
                current_brand = prod['current_brand'] if prod['current_brand'] else 'NULL'
                print(f"  - {prod['name']} | Current Brand: {current_brand}")
        
        # Look for just "Market" brand products (the new name)
        just_market_products = await conn.fetch("""
            SELECT p.id, p.name, p.brand_id, b.name as current_brand
            FROM products.products p
            LEFT JOIN core.brands b ON p.brand_id = b.id
            WHERE (p.name ILIKE 'market %' OR p.name ILIKE '% market %' OR p.name ILIKE '% market')
            AND p.name NOT ILIKE '%marketplace%'
            AND p.name NOT ILIKE '%chinatown%'
            AND p.name NOT ILIKE '%stockx%'
            ORDER BY p.name
            LIMIT 10
        """)
        
        if just_market_products:
            print(f"\nJust 'Market' brand products ({len(just_market_products)}):")
            for prod in just_market_products:
                current_brand = prod['current_brand'] if prod['current_brand'] else 'NULL'
                print(f"  - {prod['name']} | Current Brand: {current_brand}")
        
        if wrong_assignments > 0:
            print(f"\nFound {wrong_assignments} products with wrong Market brand assignment!")
            
            if not market_brands:
                print("Need to create Market brand first!")
        else:
            print(f"\nAll Market products correctly assigned!")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_market_chinatown())
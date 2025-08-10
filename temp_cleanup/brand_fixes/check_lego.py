import asyncio
import asyncpg

async def check_lego():
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        # Check if Lego brand exists
        lego_brand = await conn.fetchrow("SELECT id, name FROM core.brands WHERE name ILIKE '%lego%'")
        
        if lego_brand:
            print(f"Lego brand found: {lego_brand['name']} (ID: {lego_brand['id']})")
        else:
            print("Lego brand NOT found - need to create it")
        
        # Find products that should be Lego
        lego_products = await conn.fetch("""
            SELECT p.id, p.name, p.brand_id, b.name as current_brand
            FROM products.products p
            LEFT JOIN core.brands b ON p.brand_id = b.id
            WHERE p.name ILIKE '%lego%'
            ORDER BY p.name
            LIMIT 20
        """)
        
        print(f"\nProducts with 'Lego' in name ({len(lego_products)}):")
        wrong_assignments = 0
        for prod in lego_products:
            current_brand = prod['current_brand'] if prod['current_brand'] else 'NULL'
            if lego_brand and prod['brand_id'] != lego_brand['id']:
                print(f"  *** {prod['name']} | Current Brand: {current_brand} (WRONG)")
                wrong_assignments += 1
            elif not lego_brand and prod['brand_id'] is None:
                print(f"  *** {prod['name']} | Current Brand: {current_brand} (NO BRAND)")
                wrong_assignments += 1
            else:
                print(f"  - {prod['name']} | Current Brand: {current_brand}")
        
        if wrong_assignments > 0:
            print(f"\nFound {wrong_assignments} products with wrong Lego brand assignment!")
        else:
            print(f"\nAll Lego products correctly assigned!")
            
        # Check if we need to create Lego brand
        if not lego_brand and lego_products:
            print(f"\nNeed to create Lego brand for {len(lego_products)} products")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_lego())
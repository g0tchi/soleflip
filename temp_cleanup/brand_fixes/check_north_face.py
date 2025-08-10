import asyncio
import asyncpg

async def check_north_face():
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        # Check if The North Face brand exists
        tnf_brand = await conn.fetchrow("SELECT id, name FROM core.brands WHERE name ILIKE '%north face%'")
        
        if tnf_brand:
            print(f"The North Face brand found: {tnf_brand['name']} (ID: {tnf_brand['id']})")
        else:
            print("The North Face brand NOT found - need to create it")
        
        # Find products that should be The North Face
        tnf_products = await conn.fetch("""
            SELECT p.id, p.name, p.brand_id, b.name as current_brand
            FROM products.products p
            LEFT JOIN core.brands b ON p.brand_id = b.id
            WHERE (p.name ILIKE '%north face%' OR p.name ILIKE '%northface%' OR p.name ILIKE '%tnf%')
            ORDER BY p.name
            LIMIT 20
        """)
        
        print(f"\nProducts with 'North Face' patterns ({len(tnf_products)}):")
        wrong_assignments = 0
        for prod in tnf_products:
            current_brand = prod['current_brand'] if prod['current_brand'] else 'NULL'
            if tnf_brand and prod['brand_id'] != tnf_brand['id']:
                print(f"  *** {prod['name']} | Current Brand: {current_brand} (WRONG)")
                wrong_assignments += 1
            elif not tnf_brand and prod['brand_id'] is None:
                print(f"  *** {prod['name']} | Current Brand: {current_brand} (NO BRAND)")
                wrong_assignments += 1
            else:
                print(f"  - {prod['name']} | Current Brand: {current_brand}")
        
        if wrong_assignments > 0:
            print(f"\nFound {wrong_assignments} products with wrong The North Face brand assignment!")
        else:
            print(f"\nAll The North Face products correctly assigned!")
            
        # Check if we need to create The North Face brand
        if not tnf_brand and tnf_products:
            print(f"\nNeed to create The North Face brand for {len(tnf_products)} products")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_north_face())
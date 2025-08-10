import asyncio
import asyncpg

async def fix_salomon_products():
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        # Get Salomon brand ID
        salomon_brand = await conn.fetchrow("SELECT id, name FROM core.brands WHERE name = 'Salomon'")
        print(f"Salomon brand: {salomon_brand['name']} (ID: {salomon_brand['id']})")
        
        # Find products that should be Salomon but aren't
        wrong_products = await conn.fetch("""
            SELECT p.id, p.name, p.brand_id, b.name as current_brand
            FROM products.products p
            LEFT JOIN core.brands b ON p.brand_id = b.id
            WHERE p.name ILIKE '%salomon%'
            AND (p.brand_id IS NULL OR p.brand_id != $1)
            ORDER BY p.name
            LIMIT 20
        """, salomon_brand['id'])
        
        print(f"\nProducts mit 'Salomon' im Namen aber falscher Brand-Zuordnung ({len(wrong_products)}):")
        for prod in wrong_products:
            current_brand = prod['current_brand'] if prod['current_brand'] else 'NULL'
            print(f"  - {prod['name']} | Current Brand: {current_brand}")
        
        if wrong_products:
            print(f"\nFixing {len(wrong_products)} products...")
            
            # Fix the brand assignment
            product_ids = [prod['id'] for prod in wrong_products]
            await conn.execute("""
                UPDATE products.products 
                SET brand_id = $1, updated_at = NOW()
                WHERE id = ANY($2)
            """, salomon_brand['id'], product_ids)
            
            print(f"Fixed {len(wrong_products)} Salomon products!")
            
            # Verify the fix
            verified = await conn.fetchval("""
                SELECT COUNT(*) 
                FROM products.products 
                WHERE brand_id = $1 AND name ILIKE '%salomon%'
            """, salomon_brand['id'])
            
            print(f"Total Salomon products now: {verified}")
        else:
            print("All Salomon products are correctly assigned!")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(fix_salomon_products())
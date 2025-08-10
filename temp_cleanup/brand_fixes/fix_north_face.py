import asyncio
import asyncpg

async def fix_north_face():
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        # Get The North Face brand
        tnf_brand = await conn.fetchrow("SELECT id, name FROM core.brands WHERE name ILIKE '%north face%'")
        print(f"The North Face brand: {tnf_brand['name']} (ID: {tnf_brand['id']})")
        
        # Find products that should be The North Face but aren't
        wrong_products = await conn.fetch("""
            SELECT p.id, p.name, p.brand_id, b.name as current_brand
            FROM products.products p
            LEFT JOIN core.brands b ON p.brand_id = b.id
            WHERE (p.name ILIKE '%north face%' OR p.name ILIKE '%northface%' OR p.name ILIKE '%tnf%')
            AND (p.brand_id IS NULL OR p.brand_id != $1)
            ORDER BY p.name
        """, tnf_brand['id'])
        
        print(f"\nProducts with wrong The North Face brand assignment ({len(wrong_products)}):")
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
            """, tnf_brand['id'], product_ids)
            
            print(f"Fixed {len(wrong_products)} The North Face products!")
            
            # Verify the fix
            verified = await conn.fetchval("""
                SELECT COUNT(*) 
                FROM products.products 
                WHERE brand_id = $1 AND (name ILIKE '%north face%' OR name ILIKE '%northface%' OR name ILIKE '%tnf%')
            """, tnf_brand['id'])
            
            print(f"Total The North Face products now: {verified}")
        else:
            print("All The North Face products are correctly assigned!")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(fix_north_face())
import asyncio
import asyncpg

async def fix_yeezy_gap_collab():
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        # Get GAP brand ID
        gap_brand = await conn.fetchrow("SELECT id, name FROM core.brands WHERE name = 'GAP'")
        print(f"GAP brand: {gap_brand['name']} (ID: {gap_brand['id']})")
        
        # Get Adidas brand ID for reference
        adidas_brand = await conn.fetchrow("SELECT id, name FROM core.brands WHERE name = 'Adidas'")
        print(f"Adidas brand: {adidas_brand['name']} (ID: {adidas_brand['id']})")
        
        # Find all Yeezy Gap products
        yeezy_gap_products = await conn.fetch("""
            SELECT p.id, p.name, p.brand_id, b.name as current_brand
            FROM products.products p
            LEFT JOIN core.brands b ON p.brand_id = b.id
            WHERE p.name ILIKE '%yeezy gap%'
            ORDER BY p.name
        """)
        
        print(f"\nFound {len(yeezy_gap_products)} Yeezy Gap products:")
        products_to_move = []
        
        for prod in yeezy_gap_products:
            current_brand = prod['current_brand'] if prod['current_brand'] else 'NULL'
            print(f"  - {prod['name']}")
            print(f"    Current Brand: {current_brand}")
            
            # Check if it needs to be moved to GAP
            if prod['brand_id'] != gap_brand['id']:
                products_to_move.append(prod)
                print(f"    -> SHOULD BE: GAP (Collab)")
            else:
                print(f"    -> Already correct")
            print()
        
        # Move products to GAP brand
        if products_to_move:
            print(f"Moving {len(products_to_move)} Yeezy Gap products to GAP brand...")
            
            product_ids = [prod['id'] for prod in products_to_move]
            
            await conn.execute("""
                UPDATE products.products 
                SET brand_id = $1, updated_at = NOW()
                WHERE id = ANY($2)
            """, gap_brand['id'], product_ids)
            
            print(f"Moved {len(products_to_move)} products from other brands to GAP")
            
            # Show what was moved
            for prod in products_to_move:
                print(f"  - {prod['name']} | {prod['current_brand']} -> GAP")
        
        # Verify final state
        final_gap_products = await conn.fetch("""
            SELECT p.name, p.sku
            FROM products.products p
            WHERE p.brand_id = $1 AND p.name ILIKE '%yeezy gap%'
            ORDER BY p.name
        """, gap_brand['id'])
        
        print(f"\nFinal verification - Yeezy Gap products under GAP brand:")
        for prod in final_gap_products:
            print(f"  - {prod['name']} | SKU: {prod['sku']}")
        
        # Total GAP brand products
        total_gap_products = await conn.fetchval("""
            SELECT COUNT(*) FROM products.products WHERE brand_id = $1
        """, gap_brand['id'])
        
        print(f"\nTotal GAP brand products: {total_gap_products}")
        print(f"Yeezy Gap collaboration products correctly assigned to GAP!")
        
    except Exception as e:
        print(f"Error fixing Yeezy Gap collab: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(fix_yeezy_gap_collab())
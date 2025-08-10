import asyncio
import asyncpg

async def fix_palace_amiibo_saucony():
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        # Handle Palace (existing brand)
        print("=== Fixing Palace ===")
        palace_brand = await conn.fetchrow("SELECT id, name FROM core.brands WHERE name = 'Palace'")
        print(f"Palace brand: {palace_brand['name']} (ID: {palace_brand['id']})")
        
        # Find Palace products that need reassignment
        palace_products = await conn.fetch("""
            SELECT p.id, p.name, p.brand_id, b.name as current_brand
            FROM products.products p
            LEFT JOIN core.brands b ON p.brand_id = b.id
            WHERE p.name ILIKE '%palace%'
            AND (p.brand_id IS NULL OR p.brand_id != $1)
        """, palace_brand['id'])
        
        print(f"Found {len(palace_products)} Palace products to reassign:")
        for prod in palace_products:
            current_brand = prod['current_brand'] if prod['current_brand'] else 'NULL'
            print(f"  - {prod['name']} | Current: {current_brand}")
        
        if palace_products:
            product_ids = [prod['id'] for prod in palace_products]
            await conn.execute("""
                UPDATE products.products 
                SET brand_id = $1, updated_at = NOW()
                WHERE id = ANY($2)
            """, palace_brand['id'], product_ids)
            print(f"Reassigned {len(palace_products)} products to Palace")
        
        # Handle Amiibo (create new brand)
        print(f"\n=== Fixing Amiibo ===")
        print("Creating Amiibo brand...")
        amiibo_brand_id = await conn.fetchval("""
            INSERT INTO core.brands (id, name, slug)
            VALUES (gen_random_uuid(), 'Amiibo', 'amiibo')
            RETURNING id
        """)
        print(f"Created Amiibo brand: {amiibo_brand_id}")
        
        # Find Amiibo products
        amiibo_products = await conn.fetch("""
            SELECT id, name, brand_id
            FROM products.products
            WHERE name ILIKE '%amiibo%'
            AND brand_id IS NULL
        """)
        
        print(f"Found {len(amiibo_products)} Amiibo products to assign:")
        for prod in amiibo_products:
            print(f"  - {prod['name']}")
        
        if amiibo_products:
            product_ids = [prod['id'] for prod in amiibo_products]
            await conn.execute("""
                UPDATE products.products 
                SET brand_id = $1, updated_at = NOW()
                WHERE id = ANY($2)
            """, amiibo_brand_id, product_ids)
            print(f"Assigned {len(amiibo_products)} products to Amiibo")
        
        # Handle Saucony (create new brand)
        print(f"\n=== Fixing Saucony ===")
        print("Creating Saucony brand...")
        saucony_brand_id = await conn.fetchval("""
            INSERT INTO core.brands (id, name, slug)
            VALUES (gen_random_uuid(), 'Saucony', 'saucony')
            RETURNING id
        """)
        print(f"Created Saucony brand: {saucony_brand_id}")
        
        # Find Saucony products
        saucony_products = await conn.fetch("""
            SELECT id, name, brand_id
            FROM products.products
            WHERE name ILIKE '%saucony%'
            AND brand_id IS NULL
        """)
        
        print(f"Found {len(saucony_products)} Saucony products to assign:")
        for prod in saucony_products:
            print(f"  - {prod['name']}")
        
        if saucony_products:
            product_ids = [prod['id'] for prod in saucony_products]
            await conn.execute("""
                UPDATE products.products 
                SET brand_id = $1, updated_at = NOW()
                WHERE id = ANY($2)
            """, saucony_brand_id, product_ids)
            print(f"Assigned {len(saucony_products)} products to Saucony")
        
        # Final verification
        print(f"\n=== Final Verification ===")
        
        brand_summary = await conn.fetch("""
            SELECT b.name, COUNT(p.id) as product_count
            FROM core.brands b
            LEFT JOIN products.products p ON b.id = p.brand_id
            WHERE b.name IN ('Palace', 'Amiibo', 'Saucony')
            GROUP BY b.name
            ORDER BY b.name
        """)
        
        print("Final brand summary:")
        for brand in brand_summary:
            print(f"  - {brand['name']}: {brand['product_count']} products")
        
        # Show all products with SKUs
        all_products = await conn.fetch("""
            SELECT b.name as brand_name, p.name as product_name, p.sku
            FROM core.brands b
            JOIN products.products p ON b.id = p.brand_id
            WHERE b.name IN ('Palace', 'Amiibo', 'Saucony')
            ORDER BY b.name, p.name
        """)
        
        current_brand = None
        for prod in all_products:
            if prod['brand_name'] != current_brand:
                print(f"\n{prod['brand_name']} products:")
                current_brand = prod['brand_name']
            print(f"  - {prod['product_name']} | SKU: {prod['sku']}")
        
        print(f"\nPalace, Amiibo, and Saucony brands successfully fixed!")
        
    except Exception as e:
        print(f"Error fixing Palace, Amiibo, and Saucony: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(fix_palace_amiibo_saucony())
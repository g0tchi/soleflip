import asyncio
import asyncpg

async def fix_telfar_timex():
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        # Handle Telfar (existing brand)
        print("=== Fixing Telfar ===")
        telfar_brand = await conn.fetchrow("SELECT id, name FROM core.brands WHERE name = 'Telfar'")
        print(f"Telfar brand: {telfar_brand['name']} (ID: {telfar_brand['id']})")
        
        # Find all Telfar products that need reassignment
        telfar_products = await conn.fetch("""
            SELECT p.id, p.name, p.brand_id, b.name as current_brand, p.sku
            FROM products.products p
            LEFT JOIN core.brands b ON p.brand_id = b.id
            WHERE p.name ILIKE '%telfar%'
            AND (p.brand_id IS NULL OR p.brand_id != $1)
            ORDER BY p.name
        """, telfar_brand['id'])
        
        print(f"Found {len(telfar_products)} Telfar products to reassign:")
        
        # Check for potential duplicates
        name_counts = {}
        for prod in telfar_products:
            name = prod['name']
            if name not in name_counts:
                name_counts[name] = []
            name_counts[name].append(prod)
        
        duplicates_found = False
        for name, products in name_counts.items():
            if len(products) > 1:
                duplicates_found = True
                print(f"  DUPLICATE: '{name}' appears {len(products)} times:")
                for prod in products:
                    current_brand = prod['current_brand'] if prod['current_brand'] else 'NULL'
                    print(f"    - ID: {prod['id']} | Brand: {current_brand} | SKU: {prod['sku']}")
            else:
                prod = products[0]
                current_brand = prod['current_brand'] if prod['current_brand'] else 'NULL'
                print(f"  - {prod['name']} | Current: {current_brand}")
        
        if duplicates_found:
            print(f"\nWARNING: Duplicates found! Manual review may be needed.")
            print(f"For now, reassigning all products to Telfar brand...")
        
        # Reassign all products to Telfar
        if telfar_products:
            product_ids = [prod['id'] for prod in telfar_products]
            await conn.execute("""
                UPDATE products.products 
                SET brand_id = $1, updated_at = NOW()
                WHERE id = ANY($2)
            """, telfar_brand['id'], product_ids)
            print(f"Reassigned {len(telfar_products)} products to Telfar")
        
        # Handle Timex (create new brand)
        print(f"\n=== Fixing Timex ===")
        print("Creating Timex brand...")
        timex_brand_id = await conn.fetchval("""
            INSERT INTO core.brands (id, name, slug)
            VALUES (gen_random_uuid(), 'Timex', 'timex')
            RETURNING id
        """)
        print(f"Created Timex brand: {timex_brand_id}")
        
        # Find Timex products
        timex_products = await conn.fetch("""
            SELECT id, name, brand_id
            FROM products.products
            WHERE name ILIKE '%timex%'
            AND brand_id IS NULL
        """)
        
        print(f"Found {len(timex_products)} Timex products to assign:")
        for prod in timex_products:
            print(f"  - {prod['name']}")
        
        if timex_products:
            product_ids = [prod['id'] for prod in timex_products]
            await conn.execute("""
                UPDATE products.products 
                SET brand_id = $1, updated_at = NOW()
                WHERE id = ANY($2)
            """, timex_brand_id, product_ids)
            print(f"Assigned {len(timex_products)} products to Timex")
        
        # Final verification
        print(f"\n=== Final Verification ===")
        
        brand_summary = await conn.fetch("""
            SELECT b.name, COUNT(p.id) as product_count
            FROM core.brands b
            LEFT JOIN products.products p ON b.id = p.brand_id
            WHERE b.name IN ('Telfar', 'Timex')
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
            WHERE b.name IN ('Telfar', 'Timex')
            ORDER BY b.name, p.name
        """)
        
        current_brand = None
        for prod in all_products:
            if prod['brand_name'] != current_brand:
                print(f"\n{prod['brand_name']} products:")
                current_brand = prod['brand_name']
            print(f"  - {prod['product_name']} | SKU: {prod['sku']}")
        
        print(f"\nTelfar and Timex brands successfully fixed!")
        if duplicates_found:
            print(f"NOTE: Some Telfar products may be duplicates and need manual cleanup.")
        
    except Exception as e:
        print(f"Error fixing Telfar and Timex: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(fix_telfar_timex())
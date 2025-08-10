import asyncio
import asyncpg

async def fix_moon_boot_uniqlo():
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        brands_to_fix = [
            {
                'name': 'Moon Boot',
                'slug': 'moon-boot',
                'search_patterns': ['%moon boot%', '%moonboot%']
            },
            {
                'name': 'Uniqlo',
                'slug': 'uniqlo', 
                'search_patterns': ['%uniqlo%']
            }
        ]
        
        for brand_info in brands_to_fix:
            print(f"\n=== Fixing {brand_info['name']} ===")
            
            # Create brand
            print(f"Creating {brand_info['name']} brand...")
            brand_id = await conn.fetchval("""
                INSERT INTO core.brands (id, name, slug)
                VALUES (gen_random_uuid(), $1, $2)
                RETURNING id
            """, brand_info['name'], brand_info['slug'])
            print(f"Created {brand_info['name']} brand: {brand_id}")
            
            # Find all products for this brand
            all_products = []
            for pattern in brand_info['search_patterns']:
                products = await conn.fetch("""
                    SELECT id, name, brand_id
                    FROM products.products
                    WHERE name ILIKE $1
                    AND brand_id IS NULL
                """, pattern)
                all_products.extend(products)
            
            # Remove duplicates
            unique_products = []
            seen_ids = set()
            for prod in all_products:
                if prod['id'] not in seen_ids:
                    unique_products.append(prod)
                    seen_ids.add(prod['id'])
            
            print(f"Found {len(unique_products)} {brand_info['name']} products to assign:")
            for prod in unique_products:
                print(f"  - {prod['name']}")
            
            # Assign products to brand
            if unique_products:
                product_ids = [prod['id'] for prod in unique_products]
                
                await conn.execute("""
                    UPDATE products.products 
                    SET brand_id = $1, updated_at = NOW()
                    WHERE id = ANY($2)
                """, brand_id, product_ids)
                
                print(f"Assigned {len(unique_products)} products to {brand_info['name']} brand")
            
            # Verify
            total_products = await conn.fetchval("""
                SELECT COUNT(*)
                FROM products.products
                WHERE brand_id = $1
            """, brand_id)
            
            print(f"Total {brand_info['name']} products: {total_products}")
            
            # Show all assigned products with SKUs
            assigned_products = await conn.fetch("""
                SELECT name, sku
                FROM products.products
                WHERE brand_id = $1
                ORDER BY name
            """, brand_id)
            
            print(f"All {brand_info['name']} products:")
            for prod in assigned_products:
                print(f"  - {prod['name']} | SKU: {prod['sku']}")
        
        print(f"\n=== Final Summary ===")
        
        # Show final brand counts
        brand_summary = await conn.fetch("""
            SELECT b.name, COUNT(p.id) as product_count
            FROM core.brands b
            LEFT JOIN products.products p ON b.id = p.brand_id
            WHERE b.name IN ('Moon Boot', 'Uniqlo')
            GROUP BY b.name
            ORDER BY b.name
        """)
        
        print("New brands created:")
        for brand in brand_summary:
            print(f"  - {brand['name']}: {brand['product_count']} products")
        
        print(f"\nMoon Boot and Uniqlo brands successfully created and assigned!")
        
    except Exception as e:
        print(f"Error fixing Moon Boot and Uniqlo brands: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(fix_moon_boot_uniqlo())
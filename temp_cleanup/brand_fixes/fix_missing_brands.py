import asyncio
import asyncpg

async def fix_missing_brands():
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        brands_to_fix = [
            {
                'name': 'Diadora',
                'slug': 'diadora',
                'search_pattern': '%diadora%',
                'create_brand': True
            },
            {
                'name': 'Dr. Martens',
                'slug': 'dr-martens', 
                'search_pattern': '%dr%martens%',
                'create_brand': False  # Already exists
            },
            {
                'name': 'GAP',
                'slug': 'gap',
                'search_pattern': 'gap %',  # Only "Gap " at start, not "Yeezy Gap"
                'create_brand': True
            },
            {
                'name': 'Funko',
                'slug': 'funko',
                'search_pattern': '%funko%',
                'create_brand': True
            }
        ]
        
        for brand_info in brands_to_fix:
            print(f"\n=== Fixing {brand_info['name']} ===")
            
            # Get or create brand
            if brand_info['create_brand']:
                print(f"Creating {brand_info['name']} brand...")
                brand_id = await conn.fetchval("""
                    INSERT INTO core.brands (id, name, slug)
                    VALUES (gen_random_uuid(), $1, $2)
                    RETURNING id
                """, brand_info['name'], brand_info['slug'])
                print(f"Created {brand_info['name']} brand: {brand_id}")
            else:
                # Get existing brand
                existing_brand = await conn.fetchrow(
                    "SELECT id, name FROM core.brands WHERE name ILIKE $1", 
                    f"%{brand_info['name']}%"
                )
                brand_id = existing_brand['id']
                print(f"Using existing {brand_info['name']} brand: {brand_id}")
            
            # Find products to assign
            products = await conn.fetch("""
                SELECT id, name, brand_id
                FROM products.products
                WHERE name ILIKE $1
                AND (brand_id IS NULL OR brand_id != $2)
            """, brand_info['search_pattern'], brand_id)
            
            # Filter out Yeezy Gap products for GAP brand
            if brand_info['name'] == 'GAP':
                products = [p for p in products if not p['name'].lower().startswith('yeezy')]
            
            print(f"Found {len(products)} {brand_info['name']} products to assign:")
            for prod in products:
                print(f"  - {prod['name']}")
            
            # Assign products to brand
            if products:
                product_ids = [prod['id'] for prod in products]
                
                await conn.execute("""
                    UPDATE products.products 
                    SET brand_id = $1, updated_at = NOW()
                    WHERE id = ANY($2)
                """, brand_id, product_ids)
                
                print(f"Assigned {len(products)} products to {brand_info['name']} brand")
            
            # Verify
            total_products = await conn.fetchval("""
                SELECT COUNT(*)
                FROM products.products
                WHERE brand_id = $1
            """, brand_id)
            
            print(f"Total {brand_info['name']} products: {total_products}")
        
        print(f"\n=== Final Verification ===")
        
        # Show all fixed brands and their products
        all_brands = await conn.fetch("""
            SELECT b.name, COUNT(p.id) as product_count
            FROM core.brands b
            LEFT JOIN products.products p ON b.id = p.brand_id
            WHERE b.name IN ('Diadora', 'Dr. Martens', 'GAP', 'Funko')
            GROUP BY b.name
            ORDER BY b.name
        """)
        
        print("Brand summary:")
        for brand in all_brands:
            print(f"  - {brand['name']}: {brand['product_count']} products")
        
        print(f"\nMissing brands fix completed!")
        
    except Exception as e:
        print(f"Error fixing missing brands: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(fix_missing_brands())
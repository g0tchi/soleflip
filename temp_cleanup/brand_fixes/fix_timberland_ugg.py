import asyncio
import asyncpg

async def fix_timberland_ugg():
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        # Check what brands we need to create
        brands_to_check = ['Timberland', 'UGG']
        
        for brand_name in brands_to_check:
            print(f"\n=== Checking {brand_name} ===")
            
            # Check if brand exists
            existing_brand = await conn.fetchrow(
                "SELECT id, name FROM core.brands WHERE name ILIKE $1", 
                f'%{brand_name}%'
            )
            
            if existing_brand:
                print(f"{brand_name} brand already exists: {existing_brand['name']} (ID: {existing_brand['id']})")
                brand_id = existing_brand['id']
            else:
                # Create the brand
                print(f"Creating {brand_name} brand...")
                brand_id = await conn.fetchval("""
                    INSERT INTO core.brands (id, name, slug)
                    VALUES (gen_random_uuid(), $1, $2)
                    RETURNING id
                """, brand_name, brand_name.lower())
                print(f"Created {brand_name} brand: {brand_id}")
            
            # Find products that should belong to this brand
            products = await conn.fetch("""
                SELECT id, name, brand_id
                FROM products.products
                WHERE name ILIKE $1
                AND (brand_id IS NULL OR brand_id != $2)
            """, f'%{brand_name}%', brand_id)
            
            print(f"Found {len(products)} {brand_name} products to assign:")
            for prod in products[:5]:  # Show first 5
                print(f"  - {prod['name']}")
            if len(products) > 5:
                print(f"  ... and {len(products) - 5} more")
            
            # Assign products to brand
            if products:
                product_ids = [prod['id'] for prod in products]
                
                await conn.execute("""
                    UPDATE products.products 
                    SET brand_id = $1, updated_at = NOW()
                    WHERE id = ANY($2)
                """, brand_id, product_ids)
                
                print(f"Assigned {len(products)} products to {brand_name} brand")
            
            # Verify
            total_products = await conn.fetchval("""
                SELECT COUNT(*)
                FROM products.products
                WHERE brand_id = $1
            """, brand_id)
            
            print(f"Total {brand_name} products: {total_products}")
        
        print(f"\n=== Summary ===")
        print("Timberland and UGG brands have been processed!")
        
    except Exception as e:
        print(f"Error fixing brands: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(fix_timberland_ugg())
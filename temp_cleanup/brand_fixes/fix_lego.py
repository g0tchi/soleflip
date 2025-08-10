import asyncio
import asyncpg

async def fix_lego():
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        # Step 1: Create LEGO brand
        print("Creating LEGO brand...")
        lego_brand_id = await conn.fetchval("""
            INSERT INTO core.brands (id, name, slug)
            VALUES (gen_random_uuid(), 'LEGO', 'lego')
            RETURNING id
        """)
        print(f"Created LEGO brand: {lego_brand_id}")
        
        # Step 2: Find all LEGO products
        lego_products = await conn.fetch("""
            SELECT id, name
            FROM products.products
            WHERE name ILIKE '%lego%'
            AND brand_id IS NULL
        """)
        
        print(f"Found {len(lego_products)} LEGO products to assign")
        
        # Step 3: Assign all LEGO products to LEGO brand
        if lego_products:
            product_ids = [prod['id'] for prod in lego_products]
            
            await conn.execute("""
                UPDATE products.products 
                SET brand_id = $1, updated_at = NOW()
                WHERE id = ANY($2)
            """, lego_brand_id, product_ids)
            
            print(f"Assigned {len(lego_products)} products to LEGO brand")
            
            # Show assigned products
            print("\nAssigned products:")
            for prod in lego_products[:10]:  # Show first 10
                print(f"  - {prod['name']}")
            if len(lego_products) > 10:
                print(f"  ... and {len(lego_products) - 10} more")
        
        # Step 4: Verify the fix
        total_lego = await conn.fetchval("""
            SELECT COUNT(*)
            FROM products.products
            WHERE brand_id = $1
        """, lego_brand_id)
        
        print(f"\nVerification: {total_lego} products now assigned to LEGO brand")
        print("LEGO brand fix completed!")
        
    except Exception as e:
        print(f"Error fixing LEGO: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(fix_lego())
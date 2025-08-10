import asyncio
import asyncpg

async def fix_market_brand():
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        # Step 1: Create Market brand
        print("Creating Market brand...")
        market_brand_id = await conn.fetchval("""
            INSERT INTO core.brands (id, name, slug)
            VALUES (gen_random_uuid(), 'Market', 'market')
            RETURNING id
        """)
        print(f"Created Market brand: {market_brand_id}")
        
        # Step 2: Find all Market/Chinatown Market products
        market_products = await conn.fetch("""
            SELECT id, name
            FROM products.products
            WHERE (name ILIKE '%market%' OR name ILIKE '%chinatown market%')
            AND name NOT ILIKE '%marketplace%'
            AND name NOT ILIKE '%stockx%'
            AND brand_id IS NULL
        """)
        
        print(f"Found {len(market_products)} Market products to assign:")
        for prod in market_products:
            print(f"  - {prod['name']}")
        
        # Step 3: Assign all Market products to Market brand
        if market_products:
            product_ids = [prod['id'] for prod in market_products]
            
            await conn.execute("""
                UPDATE products.products 
                SET brand_id = $1, updated_at = NOW()
                WHERE id = ANY($2)
            """, market_brand_id, product_ids)
            
            print(f"\nAssigned {len(market_products)} products to Market brand")
        
        # Step 4: Verify the fix
        total_market = await conn.fetchval("""
            SELECT COUNT(*)
            FROM products.products
            WHERE brand_id = $1
        """, market_brand_id)
        
        print(f"\nVerification: {total_market} products now assigned to Market brand")
        
        # Show all assigned products
        assigned_products = await conn.fetch("""
            SELECT name, sku
            FROM products.products
            WHERE brand_id = $1
            ORDER BY name
        """, market_brand_id)
        
        print(f"\nAll Market brand products:")
        for prod in assigned_products:
            print(f"  - {prod['name']} | SKU: {prod['sku']}")
        
        print(f"\nMarket brand fix completed!")
        print(f"Note: This includes both 'Chinatown Market' (old name) and 'Market' (new name) products")
        
    except Exception as e:
        print(f"Error fixing Market brand: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(fix_market_brand())
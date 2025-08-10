import asyncio
import asyncpg
import re

async def extract_lego_skus():
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        # Check if products table has SKU field
        columns = await conn.fetch("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'products' AND table_name = 'products'
            AND column_name IN ('sku', 'model_number', 'article_number')
            ORDER BY column_name
        """)
        
        print("Available SKU-related columns in products table:")
        for col in columns:
            print(f"  - {col['column_name']}: {col['data_type']}")
        
        # Get LEGO brand ID
        lego_brand = await conn.fetchrow("SELECT id, name FROM core.brands WHERE name = 'LEGO'")
        print(f"\nLEGO brand: {lego_brand['name']} (ID: {lego_brand['id']})")
        
        # Get all LEGO products
        lego_products = await conn.fetch("""
            SELECT id, name, sku
            FROM products.products
            WHERE brand_id = $1
            ORDER BY name
        """, lego_brand['id'])
        
        print(f"\nFound {len(lego_products)} LEGO products:")
        
        # Extract set numbers from names
        extracted_skus = []
        for prod in lego_products:
            # Look for LEGO set numbers (typically 4-5 digits at the end)
            # Pattern: "Set XXXXX" or "XXXXX" at end of string
            matches = re.findall(r'Set (\d{4,5})|(\d{4,5})$', prod['name'])
            
            if matches:
                # Get the first non-empty match
                set_number = next((match for match_group in matches for match in match_group if match), None)
                if set_number:
                    current_sku = prod['sku'] if prod['sku'] else 'NULL'
                    print(f"  - {prod['name']}")
                    print(f"    Current SKU: {current_sku} -> New SKU: {set_number}")
                    extracted_skus.append({
                        'id': prod['id'],
                        'name': prod['name'],
                        'current_sku': prod['sku'],
                        'new_sku': set_number
                    })
                else:
                    print(f"  - {prod['name']} | No set number found")
            else:
                print(f"  - {prod['name']} | No set number pattern found")
        
        print(f"\nCan extract SKUs for {len(extracted_skus)} LEGO products")
        
        # Update SKUs if we found any
        if extracted_skus:
            print(f"\nUpdating SKUs...")
            updated_count = 0
            
            for item in extracted_skus:
                # Only update if current SKU is different
                if item['current_sku'] != item['new_sku']:
                    await conn.execute("""
                        UPDATE products.products 
                        SET sku = $1, updated_at = NOW()
                        WHERE id = $2
                    """, item['new_sku'], item['id'])
                    updated_count += 1
            
            print(f"Updated {updated_count} LEGO product SKUs")
            
            # Show verification
            print(f"\nVerification - LEGO products with SKUs:")
            verified_products = await conn.fetch("""
                SELECT name, sku
                FROM products.products
                WHERE brand_id = $1 AND sku IS NOT NULL
                ORDER BY name
                LIMIT 10
            """, lego_brand['id'])
            
            for prod in verified_products:
                print(f"  - {prod['name']} | SKU: {prod['sku']}")
                
            if len(verified_products) > 10:
                total_with_sku = await conn.fetchval("""
                    SELECT COUNT(*) FROM products.products 
                    WHERE brand_id = $1 AND sku IS NOT NULL
                """, lego_brand['id'])
                print(f"  ... and {total_with_sku - 10} more")
        
        print(f"\nLEGO SKU extraction completed!")
        
    except Exception as e:
        print(f"Error extracting LEGO SKUs: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(extract_lego_skus())
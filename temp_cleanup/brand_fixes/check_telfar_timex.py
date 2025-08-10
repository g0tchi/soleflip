import asyncio
import asyncpg

async def check_telfar_timex():
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        brands_to_check = [
            {
                'name': 'Telfar',
                'search_patterns': ['%telfar%']
            },
            {
                'name': 'Timex', 
                'search_patterns': ['%timex%']
            }
        ]
        
        for brand_info in brands_to_check:
            print(f"\n=== Checking {brand_info['name']} ===")
            
            # Check if brand exists
            existing_brand = None
            for pattern in brand_info['search_patterns']:
                existing_brand = await conn.fetchrow(
                    "SELECT id, name FROM core.brands WHERE name ILIKE $1", 
                    pattern
                )
                if existing_brand:
                    break
            
            if existing_brand:
                print(f"{brand_info['name']} brand found: {existing_brand['name']} (ID: {existing_brand['id']})")
                brand_id = existing_brand['id']
                brand_exists = True
            else:
                print(f"{brand_info['name']} brand NOT found")
                brand_id = None
                brand_exists = False
            
            # Find products that should belong to this brand
            all_products = []
            for pattern in brand_info['search_patterns']:
                products = await conn.fetch("""
                    SELECT id, name, brand_id, sku
                    FROM products.products
                    WHERE name ILIKE $1
                    ORDER BY name
                """, pattern)
                all_products.extend(products)
            
            # Remove duplicates
            unique_products = []
            seen_ids = set()
            for prod in all_products:
                if prod['id'] not in seen_ids:
                    unique_products.append(prod)
                    seen_ids.add(prod['id'])
            
            print(f"Found {len(unique_products)} {brand_info['name']} products:")
            wrong_assignments = 0
            
            for prod in unique_products:
                current_brand_name = 'NULL'
                if prod['brand_id']:
                    current_brand_name = await conn.fetchval(
                        "SELECT name FROM core.brands WHERE id = $1", 
                        prod['brand_id']
                    )
                
                needs_assignment = False
                if brand_exists and prod['brand_id'] != brand_id:
                    needs_assignment = True
                elif not brand_exists and prod['brand_id'] is None:
                    needs_assignment = True
                
                if needs_assignment:
                    print(f"  *** {prod['name']} | Current Brand: {current_brand_name} (NEEDS ASSIGNMENT)")
                    wrong_assignments += 1
                else:
                    print(f"  - {prod['name']} | Current Brand: {current_brand_name}")
            
            if wrong_assignments > 0:
                if not brand_exists:
                    print(f"  -> Need to CREATE {brand_info['name']} brand and assign {wrong_assignments} products")
                else:
                    print(f"  -> Need to REASSIGN {wrong_assignments} products to {brand_info['name']}")
            elif len(unique_products) == 0:
                print(f"  -> No {brand_info['name']} products found")
            else:
                print(f"  -> All {brand_info['name']} products correctly assigned!")
        
        print(f"\n=== Summary ===")
        print("Telfar and Timex brand analysis completed!")
        
    except Exception as e:
        print(f"Error checking Telfar and Timex: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_telfar_timex())
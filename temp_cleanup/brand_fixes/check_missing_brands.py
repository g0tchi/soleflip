import asyncio
import asyncpg

async def check_missing_brands():
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        brands_to_check = ['Diadora', 'Dr. Martens', 'GAP', 'Funko']
        
        for brand_name in brands_to_check:
            print(f"\n=== Checking {brand_name} ===")
            
            # Check if brand exists (flexible search)
            search_patterns = []
            if brand_name == 'Dr. Martens':
                search_patterns = ['%dr%martens%', '%dr martens%', '%martens%']
            elif brand_name == 'Funko':
                search_patterns = ['%funko%']
            else:
                search_patterns = [f'%{brand_name}%']
            
            existing_brand = None
            for pattern in search_patterns:
                existing_brand = await conn.fetchrow(
                    "SELECT id, name FROM core.brands WHERE name ILIKE $1", 
                    pattern
                )
                if existing_brand:
                    break
            
            if existing_brand:
                print(f"{brand_name} brand found: {existing_brand['name']} (ID: {existing_brand['id']})")
                brand_id = existing_brand['id']
                brand_exists = True
            else:
                print(f"{brand_name} brand NOT found")
                brand_id = None
                brand_exists = False
            
            # Find products that should belong to this brand
            product_patterns = []
            if brand_name == 'Dr. Martens':
                product_patterns = ['%dr%martens%', '%dr martens%', '%martens%']
            elif brand_name == 'Funko':
                product_patterns = ['%funko%', '%funko pop%']
            else:
                product_patterns = [f'%{brand_name}%']
            
            all_products = []
            for pattern in product_patterns:
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
            
            print(f"Found {len(unique_products)} {brand_name} products:")
            wrong_assignments = 0
            
            for prod in unique_products:
                if brand_exists and prod['brand_id'] != brand_id:
                    print(f"  *** {prod['name']} | Current Brand: {prod['brand_id'] or 'NULL'} (WRONG)")
                    wrong_assignments += 1
                elif not brand_exists and prod['brand_id'] is None:
                    print(f"  *** {prod['name']} | Current Brand: NULL (NO BRAND)")
                    wrong_assignments += 1
                else:
                    current_brand_name = await conn.fetchval(
                        "SELECT name FROM core.brands WHERE id = $1", 
                        prod['brand_id']
                    ) if prod['brand_id'] else 'NULL'
                    print(f"  - {prod['name']} | Current Brand: {current_brand_name}")
            
            if wrong_assignments > 0:
                if not brand_exists:
                    print(f"  -> Need to CREATE {brand_name} brand and assign {wrong_assignments} products")
                else:
                    print(f"  -> Need to REASSIGN {wrong_assignments} products to {brand_name}")
        
        print(f"\n=== Summary ===")
        print("Missing brand analysis completed!")
        
    except Exception as e:
        print(f"Error checking missing brands: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_missing_brands())
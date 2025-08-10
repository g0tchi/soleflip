import asyncio
import asyncpg

async def check_tesla_cybertruck():
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        # Find all Tesla Cybertruck products
        cybertruck_products = await conn.fetch("""
            SELECT p.id, p.name, p.sku, p.brand_id, b.name as brand_name,
                   p.created_at, p.updated_at
            FROM products.products p
            LEFT JOIN core.brands b ON p.brand_id = b.id
            WHERE p.name ILIKE '%cybertruck%'
            ORDER BY p.created_at
        """)
        
        print(f"Found {len(cybertruck_products)} Cybertruck products:")
        print("=" * 80)
        
        for i, prod in enumerate(cybertruck_products, 1):
            brand_name = prod['brand_name'] if prod['brand_name'] else 'NULL'
            print(f"{i}. ID: {prod['id']}")
            print(f"   Name: {prod['name']}")
            print(f"   SKU: {prod['sku']}")
            print(f"   Brand: {brand_name}")
            print(f"   Created: {prod['created_at']}")
            print(f"   Updated: {prod['updated_at']}")
            print()
        
        # Check if there are exact duplicates (same name)
        if len(cybertruck_products) > 1:
            names = [prod['name'] for prod in cybertruck_products]
            unique_names = set(names)
            
            print(f"Analysis:")
            print(f"- Total products: {len(cybertruck_products)}")
            print(f"- Unique names: {len(unique_names)}")
            
            if len(unique_names) < len(cybertruck_products):
                print(f"- DUPLICATES FOUND: {len(cybertruck_products) - len(unique_names)} duplicate(s)")
                
                # Find exact duplicates
                name_counts = {}
                for name in names:
                    name_counts[name] = name_counts.get(name, 0) + 1
                
                duplicates = {name: count for name, count in name_counts.items() if count > 1}
                for name, count in duplicates.items():
                    print(f"  * '{name}' appears {count} times")
            else:
                print(f"- No exact name duplicates")
        
        # Check inventory items for these products
        if cybertruck_products:
            product_ids = [prod['id'] for prod in cybertruck_products]
            
            inventory_items = await conn.fetch("""
                SELECT i.product_id, p.name as product_name, COUNT(*) as inventory_count
                FROM products.inventory i
                JOIN products.products p ON i.product_id = p.id
                WHERE i.product_id = ANY($1)
                GROUP BY i.product_id, p.name
                ORDER BY inventory_count DESC
            """, product_ids)
            
            print(f"\nInventory items for Cybertruck products:")
            for item in inventory_items:
                print(f"  - {item['product_name']}: {item['inventory_count']} items")
            
            if not inventory_items:
                print("  - No inventory items found")
        
        # Check for Mattel brand
        mattel_brand = await conn.fetchrow("SELECT id, name FROM core.brands WHERE name ILIKE '%mattel%'")
        
        if mattel_brand:
            print(f"\nMattel brand found: {mattel_brand['name']} (ID: {mattel_brand['id']})")
            
            # Check if Cybertruck products are correctly assigned to Mattel
            wrong_brand_products = [prod for prod in cybertruck_products if prod['brand_id'] != mattel_brand['id']]
            
            if wrong_brand_products:
                print(f"Products with wrong brand assignment:")
                for prod in wrong_brand_products:
                    current_brand = prod['brand_name'] if prod['brand_name'] else 'NULL'
                    print(f"  - {prod['name']} | Current: {current_brand} | Should be: Mattel")
        else:
            print(f"\nMattel brand NOT found - may need to create it")
        
    except Exception as e:
        print(f"Error checking Cybertruck products: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_tesla_cybertruck())
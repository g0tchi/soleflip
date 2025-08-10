import asyncio
import asyncpg

async def fix_cybertruck_duplicate():
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        # Get the two Cybertruck products
        cybertruck_products = await conn.fetch("""
            SELECT p.id, p.name, p.sku, p.brand_id, b.name as brand_name, p.created_at
            FROM products.products p
            LEFT JOIN core.brands b ON p.brand_id = b.id
            WHERE p.name ILIKE '%cybertruck%'
            ORDER BY p.created_at
        """)
        
        print(f"Found {len(cybertruck_products)} Cybertruck products:")
        for i, prod in enumerate(cybertruck_products, 1):
            brand_name = prod['brand_name'] if prod['brand_name'] else 'NULL'
            print(f"{i}. {prod['name']} | Brand: {brand_name} | SKU: {prod['sku']} | ID: {prod['id']}")
        
        if len(cybertruck_products) != 2:
            print(f"Expected 2 products, found {len(cybertruck_products)}. Aborting.")
            return
        
        # Identify which is the old (wrong) and new (correct) product
        old_product = cybertruck_products[0]  # NULL brand, older
        new_product = cybertruck_products[1]  # Mattel brand, newer
        
        print(f"\nIdentified:")
        print(f"- OLD (to delete): {old_product['id']} | Brand: {old_product['brand_name'] or 'NULL'}")
        print(f"- NEW (to keep):   {new_product['id']} | Brand: {new_product['brand_name']}")
        
        # Check inventory distribution
        inventory_old = await conn.fetchval("""
            SELECT COUNT(*) FROM products.inventory WHERE product_id = $1
        """, old_product['id'])
        
        inventory_new = await conn.fetchval("""
            SELECT COUNT(*) FROM products.inventory WHERE product_id = $1
        """, new_product['id'])
        
        print(f"\nInventory distribution:")
        print(f"- OLD product: {inventory_old} items")
        print(f"- NEW product: {inventory_new} items")
        
        # Move all inventory items from old to new product
        if inventory_old > 0:
            print(f"\nMoving {inventory_old} inventory items from old to new product...")
            
            await conn.execute("""
                UPDATE products.inventory 
                SET product_id = $1, updated_at = NOW()
                WHERE product_id = $2
            """, new_product['id'], old_product['id'])
            
            print(f"Moved {inventory_old} inventory items")
        
        # Verify inventory move
        inventory_old_after = await conn.fetchval("""
            SELECT COUNT(*) FROM products.inventory WHERE product_id = $1
        """, old_product['id'])
        
        inventory_new_after = await conn.fetchval("""
            SELECT COUNT(*) FROM products.inventory WHERE product_id = $1
        """, new_product['id'])
        
        print(f"\nAfter move:")
        print(f"- OLD product: {inventory_old_after} items")
        print(f"- NEW product: {inventory_new_after} items")
        
        # Delete the old duplicate product
        if inventory_old_after == 0:
            print(f"\nDeleting old duplicate product...")
            
            await conn.execute("""
                DELETE FROM products.products WHERE id = $1
            """, old_product['id'])
            
            print(f"Deleted old product: {old_product['id']}")
        else:
            print(f"WARNING: Old product still has {inventory_old_after} inventory items - not deleting")
            return
        
        # Verify final state
        remaining_products = await conn.fetch("""
            SELECT p.id, p.name, p.sku, b.name as brand_name
            FROM products.products p
            LEFT JOIN core.brands b ON p.brand_id = b.id
            WHERE p.name ILIKE '%cybertruck%'
        """)
        
        print(f"\nFinal verification:")
        print(f"- Remaining Cybertruck products: {len(remaining_products)}")
        
        for prod in remaining_products:
            brand_name = prod['brand_name'] if prod['brand_name'] else 'NULL'
            inventory_count = await conn.fetchval("""
                SELECT COUNT(*) FROM products.inventory WHERE product_id = $1
            """, prod['id'])
            
            print(f"  - {prod['name']}")
            print(f"    Brand: {brand_name} | SKU: {prod['sku']} | Inventory: {inventory_count} items")
        
        print(f"\nCybertruck duplicate cleanup completed!")
        
    except Exception as e:
        print(f"Error fixing Cybertruck duplicate: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(fix_cybertruck_duplicate())
import asyncio
import asyncpg

async def check_size_details():
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        # Check the specific size
        size_details = await conn.fetchrow(
            """SELECT s.id, s.value, s.category_id, s.region, 
                      c.name as current_category_name,
                      COUNT(ii.id) as inventory_items_count
               FROM core.sizes s
               LEFT JOIN core.categories c ON s.category_id = c.id
               LEFT JOIN products.inventory ii ON s.id = ii.size_id
               WHERE s.id = $1
               GROUP BY s.id, s.value, s.category_id, s.region, c.name""",
            '7aeaa0e4-a527-4c7f-8dc9-938a0f139924'
        )
        
        if size_details:
            print(f"Size Details:")
            print(f"  ID: {size_details['id']}")
            print(f"  Value: {size_details['value']}")
            print(f"  Region: {size_details['region']}")
            print(f"  Current Category: {size_details['current_category_name']}")
            print(f"  Used in {size_details['inventory_items_count']} inventory items")
            
            # Check what products use this size (simplified schema)
            products_using_size = await conn.fetch(
                """SELECT DISTINCT p.name, p.sku
                   FROM products.inventory ii
                   JOIN products.products p ON ii.product_id = p.id
                   WHERE ii.size_id = $1
                   LIMIT 10""",
                '7aeaa0e4-a527-4c7f-8dc9-938a0f139924'
            )
            
            if products_using_size:
                print(f"\nProducts using this size:")
                for product in products_using_size:
                    print(f"  - {product['name']} (SKU: {product['sku']})")
            
            # Find Apparel category ID
            apparel_category = await conn.fetchrow(
                "SELECT id, name FROM core.categories WHERE name ILIKE '%apparel%' OR name ILIKE '%clothing%'"
            )
            
            if apparel_category:
                print(f"\nApparel Category found:")
                print(f"  ID: {apparel_category['id']}")
                print(f"  Name: {apparel_category['name']}")
                
                # Show what the update would look like
                print(f"\nProposed Update:")
                print(f"  UPDATE core.sizes SET category_id = '{apparel_category['id']}' WHERE id = '{size_details['id']}';")
                
                # Ask if user wants to execute
                print(f"\nThis will move size '{size_details['value']}' from '{size_details['current_category_name']}' to '{apparel_category['name']}'")
                print(f"Affected: {size_details['inventory_items_count']} inventory items")
                
            else:
                # Show available categories
                categories = await conn.fetch("SELECT id, name FROM core.categories ORDER BY name")
                print(f"\nAvailable categories:")
                for cat in categories:
                    print(f"  {cat['id']}: {cat['name']}")
        else:
            print("Size not found!")
            
        # Check for any transactions that might be affected
        transactions_affected = await conn.fetchval(
            """SELECT COUNT(*)
               FROM sales.transactions t
               JOIN products.inventory ii ON t.inventory_id = ii.id
               WHERE ii.size_id = $1""",
            '7aeaa0e4-a527-4c7f-8dc9-938a0f139924'
        )
        
        print(f"\nTransactions that would be indirectly affected: {transactions_affected}")
        print("(Note: This is just a count - the transactions themselves won't break)")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_size_details())
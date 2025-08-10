import asyncio
import asyncpg

async def find_salomon_data():
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        # Check all suppliers that might be Salomon
        suppliers = await conn.fetch("""
            SELECT DISTINCT supplier, COUNT(*) as count
            FROM products.inventory 
            WHERE supplier IS NOT NULL AND supplier != ''
            ORDER BY supplier
        """)
        
        print('All suppliers in inventory:')
        salomon_found = False
        for supplier in suppliers:
            if 'salomon' in supplier['supplier'].lower():
                print(f"  *** {supplier['supplier']} | Count: {supplier['count']}")
                salomon_found = True
            else:
                print(f"  - {supplier['supplier']} | Count: {supplier['count']}")
        
        if not salomon_found:
            print("  No Salomon suppliers found in inventory!")
        
        # Check products with Salomon brand
        salomon_products = await conn.fetch("""
            SELECT p.id, p.name, i.supplier, COUNT(*) as inventory_count
            FROM products.products p
            JOIN products.inventory i ON p.id = i.product_id
            WHERE p.brand_id = 'f458fa75-23a2-4913-a691-1c865144531d'
            GROUP BY p.id, p.name, i.supplier
            ORDER BY inventory_count DESC
            LIMIT 10
        """)
        
        print(f'\nSalomon products in inventory ({len(salomon_products)} found):')
        for prod in salomon_products:
            print(f"  - {prod['name']} | Supplier: '{prod['supplier']}' | Items: {prod['inventory_count']}")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(find_salomon_data())
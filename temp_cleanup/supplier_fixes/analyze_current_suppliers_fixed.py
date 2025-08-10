import asyncio
import asyncpg

async def analyze_current_suppliers():
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        print("Current Supplier Analysis")
        print("="*50)
        
        # First check what tables exist
        tables = await conn.fetch(
            """SELECT schemaname, tablename 
               FROM pg_tables 
               WHERE schemaname IN ('products', 'core', 'sales')
               ORDER BY schemaname, tablename"""
        )
        
        print("Available tables:")
        for table in tables:
            print(f"  {table['schemaname']}.{table['tablename']}")
        print()
        
        # Check if inventory table exists
        inventory_table = await conn.fetchval(
            """SELECT tablename 
               FROM pg_tables 
               WHERE schemaname = 'products' 
               AND tablename LIKE '%inventory%'"""
        )
        
        if inventory_table:
            print(f"Found inventory table: products.{inventory_table}")
            
            # Get unique suppliers with statistics
            suppliers = await conn.fetch(
                f"""SELECT 
                    supplier,
                    COUNT(*) as inventory_count,
                    COUNT(DISTINCT product_id) as unique_products,
                    AVG(purchase_price) as avg_purchase_price,
                    MIN(purchase_date) as first_purchase,
                    MAX(purchase_date) as last_purchase
                   FROM products.{inventory_table}
                   WHERE supplier IS NOT NULL AND supplier != ''
                   GROUP BY supplier
                   ORDER BY inventory_count DESC"""
            )
            
            print(f"\\nFound {len(suppliers)} unique suppliers:")
            print()
            
            for supplier in suppliers:
                print(f"Supplier: {supplier['supplier']}")
                print(f"  - Inventory Items: {supplier['inventory_count']}")
                print(f"  - Unique Products: {supplier['unique_products']}")
                if supplier['avg_purchase_price']:
                    print(f"  - Avg Purchase Price: €{supplier['avg_purchase_price']:.2f}")
                if supplier['first_purchase']:
                    print(f"  - First Purchase: {supplier['first_purchase'].strftime('%Y-%m-%d')}")
                    print(f"  - Last Purchase: {supplier['last_purchase'].strftime('%Y-%m-%d')}")
                print()
            
            # Check for data quality issues
            print("Data Quality Analysis:")
            print("-" * 30)
            
            # Empty/null suppliers
            empty_suppliers = await conn.fetchval(
                f"SELECT COUNT(*) FROM products.{inventory_table} WHERE supplier IS NULL OR supplier = ''"
            )
            print(f"Items without supplier: {empty_suppliers}")
            
            total_items = await conn.fetchval(f"SELECT COUNT(*) FROM products.{inventory_table}")
            print(f"Total inventory items: {total_items}")
            
            if len(suppliers) > 0:
                print(f"\\nSupplier Coverage: {((total_items - empty_suppliers) / total_items * 100):.1f}%")
                
                # Show sample of supplier values
                print("\\nSample supplier values:")
                for i, supplier in enumerate(suppliers[:5]):
                    print(f"  {i+1}. '{supplier['supplier']}' ({supplier['inventory_count']} items)")
        else:
            print("No inventory table found!")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(analyze_current_suppliers())
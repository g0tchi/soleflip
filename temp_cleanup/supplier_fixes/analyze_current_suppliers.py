import asyncio
import asyncpg

async def analyze_current_suppliers():
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        print("Current Supplier Analysis")
        print("="*50)
        
        # Get unique suppliers with statistics
        suppliers = await conn.fetch(
            """SELECT 
                supplier,
                COUNT(*) as inventory_count,
                COUNT(DISTINCT product_id) as unique_products,
                AVG(purchase_price) as avg_purchase_price,
                MIN(purchase_date) as first_purchase,
                MAX(purchase_date) as last_purchase
               FROM products.inventory_items 
               WHERE supplier IS NOT NULL AND supplier != ''
               GROUP BY supplier
               ORDER BY inventory_count DESC"""
        )
        
        print(f"Found {len(suppliers)} unique suppliers:")
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
            "SELECT COUNT(*) FROM products.inventory_items WHERE supplier IS NULL OR supplier = ''"
        )
        print(f"Items without supplier: {empty_suppliers}")
        
        # Potential duplicates (case variations)
        potential_duplicates = await conn.fetch(
            """SELECT 
                LOWER(TRIM(supplier)) as normalized_name,
                STRING_AGG(DISTINCT supplier, ', ') as variations,
                COUNT(DISTINCT supplier) as variation_count,
                SUM(inventory_count) as total_items
               FROM (
                   SELECT supplier, COUNT(*) as inventory_count
                   FROM products.inventory_items 
                   WHERE supplier IS NOT NULL AND supplier != ''
                   GROUP BY supplier
               ) s
               GROUP BY LOWER(TRIM(supplier))
               HAVING COUNT(DISTINCT supplier) > 1
               ORDER BY total_items DESC"""
        )
        
        if potential_duplicates:
            print(f"\nPotential duplicate suppliers: {len(potential_duplicates)}")
            for dup in potential_duplicates:
                print(f"  '{dup['normalized_name']}' -> {dup['variations']} ({dup['total_items']} items)")
        else:
            print("No obvious duplicate suppliers found")
        
        # Most common supplier patterns
        print(f"\nSupplier Types Analysis:")
        print("-" * 30)
        
        # Try to categorize suppliers
        supplier_patterns = await conn.fetch(
            """SELECT 
                supplier,
                COUNT(*) as count,
                CASE 
                    WHEN supplier ILIKE '%store%' OR supplier ILIKE '%shop%' THEN 'retail'
                    WHEN supplier ILIKE '%resell%' OR supplier ILIKE '%flip%' THEN 'reseller'
                    WHEN supplier ILIKE '%@%' OR supplier ILIKE '%.%' THEN 'online/email'
                    WHEN LENGTH(supplier) < 20 AND supplier ~ '^[a-zA-Z0-9_]+$' THEN 'username'
                    ELSE 'other'
                END as supplier_type
               FROM products.inventory_items 
               WHERE supplier IS NOT NULL AND supplier != ''
               GROUP BY supplier
               ORDER BY count DESC"""
        )
        
        # Group by type
        type_summary = {}
        for pattern in supplier_patterns:
            supplier_type = pattern['supplier_type']
            if supplier_type not in type_summary:
                type_summary[supplier_type] = {'count': 0, 'items': 0, 'examples': []}
            type_summary[supplier_type]['count'] += 1
            type_summary[supplier_type]['items'] += pattern['count']
            if len(type_summary[supplier_type]['examples']) < 3:
                type_summary[supplier_type]['examples'].append(pattern['supplier'])
        
        for supplier_type, data in type_summary.items():
            print(f"{supplier_type.title()}: {data['count']} suppliers, {data['items']} items")
            print(f"  Examples: {', '.join(data['examples'])}")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(analyze_current_suppliers())
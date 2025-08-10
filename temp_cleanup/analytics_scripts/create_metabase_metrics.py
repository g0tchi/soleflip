import asyncio
import asyncpg

async def create_metabase_metrics():
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        print("=== Creating Metabase Metrics for SoleFlipper ===")
        
        # 1. INVENTORY & PERFORMANCE METRICS
        print("\n=== INVENTORY & PERFORMANCE METRICS ===")
        
        # Current Inventory Value by Brand
        inventory_value_by_brand = await conn.fetch("""
            SELECT 
                b.name as brand_name,
                COUNT(i.id) as total_items,
                ROUND(AVG(i.purchase_price), 2) as avg_purchase_price,
                ROUND(SUM(i.purchase_price * i.quantity), 2) as total_inventory_value,
                ROUND(AVG(i.purchase_price * i.quantity), 2) as avg_item_value
            FROM products.inventory i
            JOIN products.products p ON i.product_id = p.id
            JOIN core.brands b ON p.brand_id = b.id
            WHERE i.status = 'available'
            GROUP BY b.name
            ORDER BY total_inventory_value DESC
            LIMIT 10
        """)
        
        print("Top 10 Brands by Inventory Value:")
        for row in inventory_value_by_brand:
            print(f"  {row['brand_name']}: {row['total_items']} items, €{row['total_inventory_value']} total value")
        
        # Inventory Age Analysis
        inventory_age = await conn.fetch("""
            SELECT 
                b.name as brand_name,
                ROUND(AVG(EXTRACT(DAYS FROM NOW() - i.purchase_date)), 0) as avg_days_in_inventory,
                COUNT(i.id) as items_count
            FROM products.inventory i
            JOIN products.products p ON i.product_id = p.id
            JOIN core.brands b ON p.brand_id = b.id
            WHERE i.status = 'available' AND i.purchase_date IS NOT NULL
            GROUP BY b.name
            HAVING COUNT(i.id) >= 3
            ORDER BY avg_days_in_inventory DESC
            LIMIT 10
        """)
        
        print(f"\nInventory Age Analysis (slowest moving):")
        for row in inventory_age:
            print(f"  {row['brand_name']}: {row['avg_days_in_inventory']} days avg, {row['items_count']} items")
        
        # 2. BRAND & CATEGORY ANALYTICS
        print(f"\n=== BRAND & CATEGORY ANALYTICS ===")
        
        # Brand Market Share by Item Count
        brand_market_share = await conn.fetch("""
            SELECT 
                b.name as brand_name,
                COUNT(i.id) as item_count,
                ROUND(COUNT(i.id) * 100.0 / SUM(COUNT(i.id)) OVER (), 2) as market_share_percent
            FROM products.inventory i
            JOIN products.products p ON i.product_id = p.id
            JOIN core.brands b ON p.brand_id = b.id
            GROUP BY b.name
            ORDER BY item_count DESC
            LIMIT 10
        """)
        
        print("Brand Market Share (by inventory count):")
        for row in brand_market_share:
            print(f"  {row['brand_name']}: {row['item_count']} items ({row['market_share_percent']}%)")
        
        # Category Distribution
        category_distribution = await conn.fetch("""
            SELECT 
                c.name as category_name,
                COUNT(i.id) as item_count,
                ROUND(AVG(i.purchase_price), 2) as avg_price,
                ROUND(SUM(i.purchase_price * i.quantity), 2) as total_value
            FROM products.inventory i
            JOIN products.products p ON i.product_id = p.id
            JOIN core.sizes s ON i.size_id = s.id
            JOIN core.categories c ON s.category_id = c.id
            GROUP BY c.name
            ORDER BY item_count DESC
        """)
        
        print(f"\nCategory Distribution:")
        for row in category_distribution:
            print(f"  {row['category_name']}: {row['item_count']} items, €{row['avg_price']} avg, €{row['total_value']} total")
        
        # 3. SUPPLIER ANALYTICS
        print(f"\n=== SUPPLIER ANALYTICS ===")
        
        # Supplier Performance (with normalized suppliers)
        supplier_performance = await conn.fetch("""
            SELECT 
                s.display_name as supplier_name,
                s.country,
                s.return_policy_days,
                s.rating,
                COUNT(i.id) as items_supplied,
                ROUND(AVG(i.purchase_price), 2) as avg_purchase_price
            FROM core.suppliers s
            LEFT JOIN products.inventory i ON i.supplier_id = s.id
            WHERE s.status = 'active'
            GROUP BY s.id, s.display_name, s.country, s.return_policy_days, s.rating
            ORDER BY items_supplied DESC NULLS LAST
        """)
        
        print("Supplier Performance (normalized suppliers):")
        for row in supplier_performance:
            items = row['items_supplied'] if row['items_supplied'] else 0
            avg_price = row['avg_purchase_price'] if row['avg_purchase_price'] else 0
            print(f"  {row['supplier_name']} ({row['country']}): {items} items, €{avg_price} avg, {row['rating']}/5 rating, {row['return_policy_days']} days return")
        
        # Legacy Supplier Analysis (string suppliers)
        legacy_suppliers = await conn.fetch("""
            SELECT 
                supplier,
                COUNT(*) as item_count,
                ROUND(AVG(purchase_price), 2) as avg_price,
                ROUND(SUM(purchase_price * quantity), 2) as total_value
            FROM products.inventory
            WHERE supplier IS NOT NULL 
            AND supplier != ''
            AND supplier_id IS NULL
            GROUP BY supplier
            ORDER BY item_count DESC
            LIMIT 10
        """)
        
        print(f"\nLegacy Suppliers (string format - need migration):")
        for row in legacy_suppliers:
            print(f"  '{row['supplier']}': {row['item_count']} items, €{row['avg_price']} avg, €{row['total_value']} total")
        
        # 4. FINANCIAL KPIs
        print(f"\n=== FINANCIAL KPIs ===")
        
        # Total Portfolio Value
        portfolio_metrics = await conn.fetchrow("""
            SELECT 
                COUNT(*) as total_items,
                ROUND(SUM(purchase_price * quantity), 2) as total_portfolio_value,
                ROUND(AVG(purchase_price), 2) as avg_item_price,
                ROUND(MIN(purchase_price), 2) as min_price,
                ROUND(MAX(purchase_price), 2) as max_price
            FROM products.inventory
            WHERE status = 'available'
        """)
        
        print("Portfolio Overview:")
        print(f"  Total Items: {portfolio_metrics['total_items']}")
        print(f"  Total Portfolio Value: €{portfolio_metrics['total_portfolio_value']}")
        print(f"  Average Item Price: €{portfolio_metrics['avg_item_price']}")
        print(f"  Price Range: €{portfolio_metrics['min_price']} - €{portfolio_metrics['max_price']}")
        
        # Monthly Purchase Trends
        monthly_trends = await conn.fetch("""
            SELECT 
                DATE_TRUNC('month', purchase_date) as month,
                COUNT(*) as items_purchased,
                ROUND(SUM(purchase_price * quantity), 2) as total_spent
            FROM products.inventory
            WHERE purchase_date IS NOT NULL
            AND purchase_date >= NOW() - INTERVAL '12 months'
            GROUP BY DATE_TRUNC('month', purchase_date)
            ORDER BY month DESC
            LIMIT 6
        """)
        
        print(f"\nMonthly Purchase Trends (last 6 months):")
        for row in monthly_trends:
            month_str = row['month'].strftime('%Y-%m') if row['month'] else 'Unknown'
            print(f"  {month_str}: {row['items_purchased']} items, €{row['total_spent']} spent")
        
        # 5. PRODUCT & SIZE ANALYTICS
        print(f"\n=== PRODUCT & SIZE ANALYTICS ===")
        
        # Most Popular Products
        popular_products = await conn.fetch("""
            SELECT 
                p.name as product_name,
                b.name as brand_name,
                COUNT(i.id) as inventory_count,
                ROUND(AVG(i.purchase_price), 2) as avg_price
            FROM products.products p
            JOIN core.brands b ON p.brand_id = b.id
            JOIN products.inventory i ON p.id = i.product_id
            GROUP BY p.name, b.name
            ORDER BY inventory_count DESC
            LIMIT 10
        """)
        
        print("Most Popular Products (by inventory count):")
        for row in popular_products:
            print(f"  {row['product_name']} ({row['brand_name']}): {row['inventory_count']} items, €{row['avg_price']} avg")
        
        # Size Distribution
        size_distribution = await conn.fetch("""
            SELECT 
                s.size_value,
                c.name as category_name,
                COUNT(i.id) as item_count
            FROM products.inventory i
            JOIN core.sizes s ON i.size_id = s.id
            JOIN core.categories c ON s.category_id = c.id
            GROUP BY s.size_value, c.name
            ORDER BY item_count DESC
            LIMIT 15
        """)
        
        print(f"\nSize Distribution:")
        for row in size_distribution:
            print(f"  Size {row['size_value']} ({row['category_name']}): {row['item_count']} items")
        
        print(f"\n=== Metabase Metrics Analysis Complete ===")
        print(f"These metrics are ready for Metabase dashboard creation!")
        print(f"Key insights: Brand normalization working, supplier system ready, rich analytics possible")
        
    except Exception as e:
        print(f"Error creating Metabase metrics: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(create_metabase_metrics())
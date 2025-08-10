import asyncio
import asyncpg

async def create_analytics_views():
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        print("=== Creating Analytics Views for Metabase ===")
        
        # 1. Brand Performance View
        print("\n1. Creating brand_performance view...")
        await conn.execute("""
            DROP VIEW IF EXISTS analytics.brand_performance CASCADE;
            CREATE VIEW analytics.brand_performance AS
            SELECT 
                b.name as brand_name,
                b.slug as brand_slug,
                COUNT(i.id) as total_items,
                COUNT(CASE WHEN i.status = 'available' THEN 1 END) as available_items,
                COUNT(CASE WHEN i.status = 'sold' THEN 1 END) as sold_items,
                ROUND(COUNT(i.id) * 100.0 / SUM(COUNT(i.id)) OVER (), 2) as market_share_percent,
                ROUND(AVG(i.purchase_price), 2) as avg_purchase_price,
                ROUND(SUM(i.purchase_price * i.quantity), 2) as total_inventory_value,
                ROUND(MIN(i.purchase_price), 2) as min_price,
                ROUND(MAX(i.purchase_price), 2) as max_price,
                NOW() as last_updated
            FROM core.brands b
            LEFT JOIN products.products p ON b.id = p.brand_id
            LEFT JOIN products.inventory i ON p.id = i.product_id
            GROUP BY b.id, b.name, b.slug
            ORDER BY total_items DESC NULLS LAST;
        """)
        print("SUCCESS: brand_performance view created")
        
        # 2. Category Analysis View
        print("\n2. Creating category_analysis view...")
        await conn.execute("""
            DROP VIEW IF EXISTS analytics.category_analysis CASCADE;
            CREATE VIEW analytics.category_analysis AS
            SELECT 
                c.name as category_name,
                c.slug as category_slug,
                COUNT(i.id) as total_items,
                COUNT(CASE WHEN i.status = 'available' THEN 1 END) as available_items,
                ROUND(COUNT(i.id) * 100.0 / SUM(COUNT(i.id)) OVER (), 2) as category_share_percent,
                ROUND(AVG(i.purchase_price), 2) as avg_price,
                ROUND(SUM(i.purchase_price * i.quantity), 2) as total_value,
                COUNT(DISTINCT p.brand_id) as unique_brands,
                NOW() as last_updated
            FROM core.categories c
            LEFT JOIN core.sizes s ON c.id = s.category_id
            LEFT JOIN products.inventory i ON s.id = i.size_id
            LEFT JOIN products.products p ON i.product_id = p.id
            WHERE i.id IS NOT NULL
            GROUP BY c.id, c.name, c.slug
            ORDER BY total_items DESC;
        """)
        print("SUCCESS: category_analysis view created")
        
        # 3. Supplier Performance View
        print("\n3. Creating supplier_performance view...")
        await conn.execute("""
            DROP VIEW IF EXISTS analytics.supplier_performance CASCADE;
            CREATE VIEW analytics.supplier_performance AS
            SELECT 
                s.display_name as supplier_name,
                s.name as supplier_code,
                s.supplier_type,
                s.country,
                s.city,
                s.rating,
                s.preferred,
                s.return_policy_days,
                s.return_policy_text,
                s.status as supplier_status,
                COUNT(sb.brand_id) as brand_relationships,
                -- Future: Add inventory counts when supplier_id migration is complete
                0 as items_supplied,
                0.00 as avg_purchase_price,
                NOW() as last_updated
            FROM core.suppliers s
            LEFT JOIN core.supplier_brands sb ON s.id = sb.supplier_id AND sb.relationship_status = 'active'
            GROUP BY s.id, s.display_name, s.name, s.supplier_type, s.country, s.city, 
                     s.rating, s.preferred, s.return_policy_days, s.return_policy_text, s.status
            ORDER BY s.preferred DESC, s.rating DESC NULLS LAST;
        """)
        print("SUCCESS: supplier_performance view created")
        
        # 4. Legacy Supplier Analysis View
        print("\n4. Creating legacy_supplier_analysis view...")
        await conn.execute("""
            DROP VIEW IF EXISTS analytics.legacy_supplier_analysis CASCADE;
            CREATE VIEW analytics.legacy_supplier_analysis AS
            SELECT 
                supplier as supplier_name,
                COUNT(*) as total_items,
                COUNT(CASE WHEN status = 'available' THEN 1 END) as available_items,
                COUNT(CASE WHEN status = 'sold' THEN 1 END) as sold_items,
                ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as supplier_share_percent,
                ROUND(AVG(purchase_price), 2) as avg_purchase_price,
                ROUND(SUM(purchase_price * quantity), 2) as total_value,
                ROUND(MIN(purchase_price), 2) as min_price,
                ROUND(MAX(purchase_price), 2) as max_price,
                MIN(purchase_date) as first_purchase,
                MAX(purchase_date) as last_purchase,
                NOW() as last_updated
            FROM products.inventory
            WHERE supplier IS NOT NULL 
            AND supplier != ''
            GROUP BY supplier
            ORDER BY total_items DESC;
        """)
        print("SUCCESS: legacy_supplier_analysis view created")
        
        # 5. Product Performance View
        print("\n5. Creating product_performance view...")
        await conn.execute("""
            DROP VIEW IF EXISTS analytics.product_performance CASCADE;
            CREATE VIEW analytics.product_performance AS
            SELECT 
                p.name as product_name,
                p.sku as product_sku,
                b.name as brand_name,
                COUNT(i.id) as total_inventory,
                COUNT(CASE WHEN i.status = 'available' THEN 1 END) as available_items,
                COUNT(CASE WHEN i.status = 'sold' THEN 1 END) as sold_items,
                ROUND(AVG(i.purchase_price), 2) as avg_purchase_price,
                ROUND(SUM(i.purchase_price * i.quantity), 2) as total_inventory_value,
                MIN(i.purchase_date) as first_purchase,
                MAX(i.purchase_date) as last_purchase,
                NOW() as last_updated
            FROM products.products p
            JOIN core.brands b ON p.brand_id = b.id
            LEFT JOIN products.inventory i ON p.id = i.product_id
            GROUP BY p.id, p.name, p.sku, b.name
            ORDER BY total_inventory DESC NULLS LAST;
        """)
        print("SUCCESS: product_performance view created")
        
        # 6. Financial Overview View
        print("\n6. Creating financial_overview view...")
        await conn.execute("""
            DROP VIEW IF EXISTS analytics.financial_overview CASCADE;
            CREATE VIEW analytics.financial_overview AS
            SELECT 
                COUNT(*) as total_items,
                COUNT(CASE WHEN status = 'available' THEN 1 END) as available_items,
                COUNT(CASE WHEN status = 'sold' THEN 1 END) as sold_items,
                COUNT(CASE WHEN status = 'reserved' THEN 1 END) as reserved_items,
                ROUND(SUM(CASE WHEN status = 'available' THEN purchase_price * quantity ELSE 0 END), 2) as available_inventory_value,
                ROUND(SUM(purchase_price * quantity), 2) as total_portfolio_value,
                ROUND(AVG(purchase_price), 2) as avg_item_price,
                ROUND(MIN(purchase_price), 2) as min_price,
                ROUND(MAX(purchase_price), 2) as max_price,
                COUNT(DISTINCT EXTRACT(MONTH FROM purchase_date)) as active_months,
                NOW() as last_updated
            FROM products.inventory;
        """)
        print("SUCCESS: financial_overview view created")
        
        # 7. Monthly Trends View  
        print("\n7. Creating monthly_trends view...")
        await conn.execute("""
            DROP VIEW IF EXISTS analytics.monthly_trends CASCADE;
            CREATE VIEW analytics.monthly_trends AS
            SELECT 
                DATE_TRUNC('month', purchase_date) as month,
                EXTRACT(YEAR FROM purchase_date) as year,
                EXTRACT(MONTH FROM purchase_date) as month_num,
                COUNT(*) as items_purchased,
                ROUND(SUM(purchase_price * quantity), 2) as total_spent,
                ROUND(AVG(purchase_price), 2) as avg_price,
                COUNT(DISTINCT product_id) as unique_products,
                COUNT(DISTINCT supplier) as unique_suppliers,
                NOW() as last_updated
            FROM products.inventory
            WHERE purchase_date IS NOT NULL
            GROUP BY DATE_TRUNC('month', purchase_date), 
                     EXTRACT(YEAR FROM purchase_date), 
                     EXTRACT(MONTH FROM purchase_date)
            ORDER BY month DESC;
        """)
        print("SUCCESS: monthly_trends view created")
        
        # 8. Size Distribution View
        print("\n8. Creating size_distribution view...")
        await conn.execute("""
            DROP VIEW IF EXISTS analytics.size_distribution CASCADE;
            CREATE VIEW analytics.size_distribution AS
            SELECT 
                s.size_value,
                s.size_type,
                c.name as category_name,
                COUNT(i.id) as item_count,
                ROUND(COUNT(i.id) * 100.0 / SUM(COUNT(i.id)) OVER (), 2) as size_share_percent,
                ROUND(AVG(i.purchase_price), 2) as avg_price,
                COUNT(DISTINCT i.product_id) as unique_products,
                NOW() as last_updated
            FROM core.sizes s
            JOIN core.categories c ON s.category_id = c.id
            LEFT JOIN products.inventory i ON s.id = i.size_id
            WHERE i.id IS NOT NULL
            GROUP BY s.id, s.size_value, s.size_type, c.name
            ORDER BY item_count DESC;
        """)
        print("SUCCESS: size_distribution view created")
        
        # Test all views
        print("\n=== Testing Analytics Views ===")
        
        views_to_test = [
            'brand_performance',
            'category_analysis', 
            'supplier_performance',
            'legacy_supplier_analysis',
            'product_performance',
            'financial_overview',
            'monthly_trends',
            'size_distribution'
        ]
        
        for view_name in views_to_test:
            try:
                result = await conn.fetchval(f"SELECT COUNT(*) FROM analytics.{view_name}")
                print(f"SUCCESS {view_name}: {result} rows")
            except Exception as e:
                print(f"ERROR {view_name}: {e}")
        
        # Show sample data from key views
        print(f"\n=== Sample Analytics Data ===")
        
        # Brand Performance Sample
        brand_sample = await conn.fetch("SELECT brand_name, total_items, market_share_percent FROM analytics.brand_performance WHERE total_items > 0 ORDER BY total_items DESC LIMIT 5")
        print(f"\nTop 5 Brands:")
        for row in brand_sample:
            print(f"  {row['brand_name']}: {row['total_items']} items ({row['market_share_percent']}%)")
        
        # Financial Overview
        financial = await conn.fetchrow("SELECT * FROM analytics.financial_overview")
        print(f"\nFinancial Overview:")
        print(f"  Total Items: {financial['total_items']}")
        print(f"  Available Value: €{financial['available_inventory_value'] or 0}")
        print(f"  Average Price: €{financial['avg_item_price'] or 0}")
        
        print(f"\n=== Analytics Views Successfully Created! ===")
        print(f"All views are ready for Metabase dashboard creation")
        print(f"Views provide comprehensive business intelligence metrics")
        print(f"Metabase can now access structured analytics data efficiently")
        
    except Exception as e:
        print(f"Error creating analytics views: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(create_analytics_views())
import asyncio
import asyncpg

async def create_brand_deep_dive_views():
    db_url = 'postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip'
    
    brand_views = [
        ('brand_deep_dive_overview', """
        WITH brand_extracted AS (
            SELECT 
                t.*,
                p.name as product_name,
                p.sku,
                CASE 
                    WHEN p.name ILIKE '%nike%' OR p.name ILIKE '%air %' OR p.name ILIKE '%dunk%' OR p.name ILIKE '%blazer%' OR p.name ILIKE '%cortez%' THEN 'Nike'
                    WHEN p.name ILIKE '%jordan%' OR p.name ILIKE '%travis scott x%' THEN 'Nike Jordan'
                    WHEN p.name ILIKE '%adidas%' OR p.name ILIKE '%yeezy%' OR p.name ILIKE '%ultraboost%' THEN 'Adidas'
                    WHEN p.name ILIKE '%new balance%' OR p.name ~ '^[0-9]{3,4}[A-Z]?' THEN 'New Balance'
                    WHEN p.name ILIKE '%asics%' OR p.name ILIKE '%gel-%' THEN 'ASICS'
                    WHEN p.name ILIKE '%converse%' OR p.name ILIKE '%chuck%' THEN 'Converse'
                    WHEN p.name ILIKE '%vans%' THEN 'Vans'
                    WHEN p.name ILIKE '%crocs%' THEN 'Crocs'
                    WHEN p.name ILIKE '%ugg%' THEN 'UGG'
                    WHEN p.name ILIKE '%timberland%' THEN 'Timberland'
                    WHEN p.name ILIKE '%puma%' THEN 'Puma'
                    WHEN p.name ILIKE '%reebok%' THEN 'Reebok'
                    WHEN p.name ILIKE '%salomon%' OR p.name ILIKE '%xt-6%' OR p.name ILIKE '%xt-4%' OR p.name ILIKE '%acs pro%' THEN 'Salomon'
                    WHEN p.name ILIKE '%hoka%' THEN 'HOKA'
                    WHEN p.name ILIKE '%mattel%' OR p.name ILIKE '%mega construx%' OR p.name ILIKE '%cybertruck%' THEN 'Mattel'
                    WHEN p.name ILIKE '%off-white%' OR p.name ILIKE '%off white%' THEN 'Off-White'
                    WHEN p.name ILIKE '%balenciaga%' THEN 'Balenciaga'
                    WHEN p.name ILIKE '%palace%' THEN 'Palace'
                    WHEN p.name ILIKE '%supreme%' THEN 'Supreme'
                    WHEN p.name ILIKE '%telfar%' THEN 'Telfar'
                    WHEN p.name ILIKE '%taschen%' THEN 'Taschen'
                    WHEN p.name ILIKE '%kaws%' THEN 'KAWS'
                    WHEN p.name ILIKE '%takashi murakami%' THEN 'Murakami'
                    ELSE 'Other/Unknown'
                END as extracted_brand
            FROM sales.transactions t
            JOIN products.inventory i ON t.inventory_id = i.id
            JOIN products.products p ON i.product_id = p.id
        )
        SELECT 
            extracted_brand,
            COUNT(*) as total_transactions,
            COUNT(DISTINCT product_name) as unique_products,
            SUM(sale_price) as total_revenue,
            AVG(sale_price) as avg_sale_price,
            SUM(platform_fee) as total_fees_paid,
            SUM(net_profit) as total_profit,
            ROUND((SUM(net_profit) / NULLIF(SUM(sale_price), 0) * 100)::numeric, 2) as profit_margin_percent,
            MIN(transaction_date) as first_sale,
            MAX(transaction_date) as last_sale,
            ROUND((SUM(sale_price) / COUNT(*))::numeric, 2) as avg_transaction_value
        FROM brand_extracted
        GROUP BY extracted_brand
        ORDER BY total_revenue DESC
        """),
        
        ('nike_product_breakdown', """
        WITH nike_products AS (
            SELECT 
                t.*,
                p.name as product_name,
                p.sku,
                CASE 
                    WHEN p.name ILIKE '%dunk%' THEN 'Nike Dunk'
                    WHEN p.name ILIKE '%air max%' THEN 'Air Max'
                    WHEN p.name ILIKE '%air force%' THEN 'Air Force'
                    WHEN p.name ILIKE '%jordan%' THEN 'Jordan'
                    WHEN p.name ILIKE '%blazer%' THEN 'Nike Blazer'
                    WHEN p.name ILIKE '%cortez%' THEN 'Nike Cortez'
                    WHEN p.name ILIKE '%zoom%' THEN 'Nike Zoom'
                    WHEN p.name ILIKE '%travis scott%' THEN 'Travis Scott Collab'
                    ELSE 'Other Nike'
                END as nike_line
            FROM sales.transactions t
            JOIN products.inventory i ON t.inventory_id = i.id
            JOIN products.products p ON i.product_id = p.id
            WHERE p.name ILIKE '%nike%' OR p.name ILIKE '%air %' OR p.name ILIKE '%dunk%' OR p.name ILIKE '%jordan%'
        )
        SELECT 
            nike_line,
            COUNT(*) as total_sales,
            COUNT(DISTINCT product_name) as unique_products,
            SUM(sale_price) as total_revenue,
            AVG(sale_price) as avg_price,
            MIN(sale_price) as min_price,
            MAX(sale_price) as max_price,
            MIN(transaction_date) as first_sale,
            MAX(transaction_date) as last_sale
        FROM nike_products
        GROUP BY nike_line
        ORDER BY total_revenue DESC
        """),
        
        ('brand_monthly_performance', """
        WITH brand_extracted AS (
            SELECT 
                t.*,
                p.name as product_name,
                CASE 
                    WHEN p.name ILIKE '%nike%' OR p.name ILIKE '%air %' OR p.name ILIKE '%dunk%' OR p.name ILIKE '%blazer%' THEN 'Nike'
                    WHEN p.name ILIKE '%jordan%' OR p.name ILIKE '%travis scott x%' THEN 'Nike Jordan'
                    WHEN p.name ILIKE '%adidas%' OR p.name ILIKE '%yeezy%' THEN 'Adidas'
                    WHEN p.name ILIKE '%mattel%' OR p.name ILIKE '%mega construx%' OR p.name ILIKE '%cybertruck%' THEN 'Mattel'
                    WHEN p.name ILIKE '%off-white%' THEN 'Off-White'
                    WHEN p.name ILIKE '%balenciaga%' THEN 'Balenciaga'
                    WHEN p.name ILIKE '%reebok%' THEN 'Reebok'
                    WHEN p.name ILIKE '%salomon%' OR p.name ILIKE '%xt-6%' OR p.name ILIKE '%xt-4%' OR p.name ILIKE '%acs pro%' THEN 'Salomon'
                    WHEN p.name ILIKE '%telfar%' THEN 'Telfar'
                    WHEN p.name ILIKE '%taschen%' THEN 'Taschen'
                    WHEN p.name ILIKE '%kaws%' THEN 'KAWS'
                    WHEN p.name ILIKE '%takashi murakami%' THEN 'Murakami'
                    ELSE 'Other'
                END as extracted_brand
            FROM sales.transactions t
            JOIN products.inventory i ON t.inventory_id = i.id
            JOIN products.products p ON i.product_id = p.id
        )
        SELECT 
            DATE_TRUNC('month', transaction_date) as month,
            extracted_brand,
            COUNT(*) as transactions,
            SUM(sale_price) as revenue,
            AVG(sale_price) as avg_price,
            COUNT(DISTINCT product_name) as unique_products
        FROM brand_extracted
        WHERE extracted_brand != 'Other'
        GROUP BY DATE_TRUNC('month', transaction_date), extracted_brand
        ORDER BY month DESC, revenue DESC
        """)
    ]
    
    conn = await asyncpg.connect(db_url)
    try:
        for view_name, view_sql in brand_views:
            try:
                full_sql = f'CREATE OR REPLACE VIEW analytics.{view_name} AS {view_sql}'
                await conn.execute(full_sql)
                print(f'Created brand view: analytics.{view_name}')
            except Exception as e:
                print(f'Error creating {view_name}: {e}')
        
        print('All brand deep dive views created!')
        
    except Exception as e:
        print(f'Error: {e}')
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(create_brand_deep_dive_views())
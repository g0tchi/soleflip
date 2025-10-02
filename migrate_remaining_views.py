"""
Migrate remaining analytics views (Medium + High complexity)
"""
import asyncio
from sqlalchemy import text
from shared.database.connection import DatabaseManager

REMAINING_VIEWS = {
    'brand_monthly_performance': """
        WITH brand_extracted AS (
            SELECT
                o.id,
                o.inventory_item_id,
                o.platform_id,
                o.sold_at AS transaction_date,
                o.gross_sale AS sale_price,
                o.platform_fee,
                o.shipping_cost,
                o.net_profit,
                o.status,
                o.external_id,
                o.notes,
                o.created_at,
                o.updated_at,
                o.buyer_destination_country,
                o.buyer_destination_city,
                p.name AS product_name,
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
                END AS extracted_brand
            FROM transactions.orders o
            JOIN products.inventory i ON o.inventory_item_id = i.id
            JOIN products.products p ON i.product_id = p.id
        )
        SELECT
            DATE_TRUNC('month', transaction_date) AS month,
            extracted_brand,
            COUNT(*) AS transactions,
            SUM(sale_price) AS revenue,
            AVG(sale_price) AS avg_price,
            COUNT(DISTINCT product_name) AS unique_products
        FROM brand_extracted
        WHERE extracted_brand <> 'Other'
        GROUP BY DATE_TRUNC('month', transaction_date), extracted_brand
        ORDER BY month DESC, revenue DESC
    """,

    'revenue_growth': """
        WITH monthly_data AS (
            SELECT
                DATE_TRUNC('month', sold_at) AS month,
                SUM(gross_sale) AS revenue,
                COUNT(*) AS transactions
            FROM transactions.orders
            WHERE status = 'completed'
            GROUP BY DATE_TRUNC('month', sold_at)
        ),
        growth_calc AS (
            SELECT
                month,
                revenue,
                transactions,
                LAG(revenue) OVER (ORDER BY month) AS prev_month_revenue,
                LAG(transactions) OVER (ORDER BY month) AS prev_month_transactions
            FROM monthly_data
        )
        SELECT
            month,
            revenue,
            transactions,
            prev_month_revenue,
            CASE
                WHEN prev_month_revenue > 0 THEN ROUND(((revenue - prev_month_revenue) / prev_month_revenue) * 100, 2)
                ELSE NULL
            END AS revenue_growth_percent,
            CASE
                WHEN prev_month_transactions > 0 THEN ROUND(((transactions - prev_month_transactions)::numeric / prev_month_transactions) * 100, 2)
                ELSE NULL
            END AS transaction_growth_percent
        FROM growth_calc
        ORDER BY month DESC
    """,

    'brand_market_position': """
        WITH brand_stats AS (
            SELECT
                b.name AS brand_name,
                b.segment,
                b.price_tier,
                b.target_demographic,
                COUNT(o.id) AS sales_count,
                SUM(o.gross_sale) AS revenue,
                AVG(o.gross_sale) AS avg_price,
                STDDEV(o.gross_sale) AS price_variance,
                COUNT(DISTINCT p.id) AS product_variety,
                COUNT(DISTINCT DATE_TRUNC('month', o.sold_at)) AS active_months
            FROM core.brands b
            JOIN products.products p ON p.brand_id = b.id
            JOIN products.inventory i ON i.product_id = p.id
            JOIN transactions.orders o ON o.inventory_item_id = i.id
            WHERE o.status = 'completed'
            GROUP BY b.name, b.segment, b.price_tier, b.target_demographic
        ),
        market_totals AS (
            SELECT
                SUM(revenue) AS total_market_revenue,
                SUM(sales_count) AS total_market_sales
            FROM brand_stats
        )
        SELECT
            bs.brand_name,
            bs.segment,
            bs.price_tier,
            bs.target_demographic,
            bs.sales_count,
            bs.revenue,
            bs.avg_price,
            bs.price_variance,
            bs.product_variety,
            bs.active_months,
            ROUND((bs.revenue / mt.total_market_revenue) * 100, 2) AS market_share_pct,
            ROUND((bs.sales_count::numeric / mt.total_market_sales) * 100, 2) AS sales_share_pct,
            CASE
                WHEN bs.avg_price > 200 THEN 'Premium'
                WHEN bs.avg_price > 100 THEN 'Mid-Range'
                ELSE 'Entry-Level'
            END AS price_positioning,
            CASE
                WHEN bs.sales_count > 100 THEN 'High Volume'
                WHEN bs.sales_count > 50 THEN 'Medium Volume'
                ELSE 'Low Volume'
            END AS volume_tier
        FROM brand_stats bs
        CROSS JOIN market_totals mt
        ORDER BY market_share_pct DESC
    """,

    'brand_deep_dive_overview': """
        WITH brand_extracted AS (
            SELECT
                o.id,
                o.inventory_item_id,
                o.platform_id,
                o.sold_at AS transaction_date,
                o.gross_sale AS sale_price,
                o.platform_fee,
                o.shipping_cost,
                o.net_profit,
                o.status,
                o.external_id,
                o.notes,
                o.created_at,
                o.updated_at,
                o.buyer_destination_country,
                o.buyer_destination_city,
                p.name AS product_name,
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
                END AS extracted_brand
            FROM transactions.orders o
            JOIN products.inventory i ON o.inventory_item_id = i.id
            JOIN products.products p ON i.product_id = p.id
            WHERE o.status = 'completed'
        )
        SELECT
            extracted_brand,
            COUNT(*) AS total_transactions,
            COUNT(DISTINCT product_name) AS unique_products,
            SUM(sale_price) AS total_revenue,
            AVG(sale_price) AS avg_sale_price,
            SUM(platform_fee) AS total_fees_paid,
            SUM(net_profit) AS total_profit,
            ROUND((SUM(net_profit) / NULLIF(SUM(sale_price), 0)) * 100, 2) AS profit_margin_percent,
            MIN(transaction_date) AS first_sale,
            MAX(transaction_date) AS last_sale,
            ROUND(SUM(sale_price) / COUNT(*), 2) AS avg_transaction_value
        FROM brand_extracted
        GROUP BY extracted_brand
        ORDER BY total_revenue DESC
    """,

    'nike_product_breakdown': """
        WITH nike_products AS (
            SELECT
                o.id,
                o.inventory_item_id,
                o.platform_id,
                o.sold_at AS transaction_date,
                o.gross_sale AS sale_price,
                o.platform_fee,
                o.shipping_cost,
                o.net_profit,
                o.status,
                o.external_id,
                o.notes,
                o.created_at,
                o.updated_at,
                o.buyer_destination_country,
                o.buyer_destination_city,
                p.name AS product_name,
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
                END AS nike_line
            FROM transactions.orders o
            JOIN products.inventory i ON o.inventory_item_id = i.id
            JOIN products.products p ON i.product_id = p.id
            WHERE (p.name ILIKE '%nike%' OR p.name ILIKE '%air %' OR p.name ILIKE '%dunk%' OR p.name ILIKE '%jordan%')
              AND o.status = 'completed'
        )
        SELECT
            nike_line,
            COUNT(*) AS total_sales,
            COUNT(DISTINCT product_name) AS unique_products,
            SUM(sale_price) AS total_revenue,
            AVG(sale_price) AS avg_price,
            MIN(sale_price) AS min_price,
            MAX(sale_price) AS max_price,
            MIN(transaction_date) AS first_sale,
            MAX(transaction_date) AS last_sale
        FROM nike_products
        GROUP BY nike_line
        ORDER BY total_revenue DESC
    """,

    'brand_collaboration_performance': """
        SELECT
            b.name AS brand_name,
            b.is_collaboration,
            pb.name AS parent_brand,
            COUNT(o.id) AS total_sales,
            SUM(o.gross_sale) AS total_revenue,
            AVG(o.gross_sale) AS avg_price,
            SUM(o.net_profit) AS total_profit
        FROM core.brands b
        LEFT JOIN core.brands pb ON b.parent_brand_id = pb.id
        JOIN products.products p ON p.brand_id = b.id
        JOIN products.inventory i ON i.product_id = p.id
        JOIN transactions.orders o ON o.inventory_item_id = i.id
        WHERE o.status = 'completed'
        GROUP BY b.name, b.is_collaboration, pb.name
        ORDER BY total_revenue DESC
    """
}


async def migrate():
    db = DatabaseManager()
    await db.initialize()

    print("=" * 80)
    print("MIGRATING REMAINING ANALYTICS VIEWS (Medium + High Complexity)")
    print("=" * 80)
    print(f"Total views: {len(REMAINING_VIEWS)}\n")

    async with db.get_session() as session:
        success_count = 0
        error_count = 0

        for idx, (view_name, view_sql) in enumerate(REMAINING_VIEWS.items(), 1):
            try:
                print(f"[{idx}/{len(REMAINING_VIEWS)}] Migrating {view_name}...")

                # Drop existing view
                await session.execute(text(f"DROP VIEW IF EXISTS analytics.{view_name} CASCADE"))

                # Create new view
                create_sql = f"CREATE VIEW analytics.{view_name} AS {view_sql}"
                await session.execute(text(create_sql))

                await session.commit()

                success_count += 1
                print("    Success")

            except Exception as e:
                error_count += 1
                print(f"    ERROR: {str(e)[:200]}")
                await session.rollback()

        print(f"\n{'='*80}")
        print("MIGRATION SUMMARY")
        print(f"{'='*80}")
        print(f"  Total views: {len(REMAINING_VIEWS)}")
        print(f"  Successful: {success_count}")
        print(f"  Errors: {error_count}")

        if success_count == len(REMAINING_VIEWS):
            print(f"\n[OK] ALL {len(REMAINING_VIEWS)} views migrated successfully!")
        elif success_count > 0:
            print(f"\n[!] {success_count}/{len(REMAINING_VIEWS)} views migrated")

    await db.close()


if __name__ == "__main__":
    asyncio.run(migrate())

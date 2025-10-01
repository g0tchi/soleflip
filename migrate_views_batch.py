"""
Batch migrate analytics views from transactions.transactions to transactions.orders
"""
import asyncio
from sqlalchemy import text
from shared.database.connection import DatabaseManager

# Low complexity views to migrate
LOW_COMPLEXITY_VIEWS = [
    {
        'name': 'daily_revenue',
        'sql': """
            SELECT
                DATE(sold_at) AS sale_date,
                COUNT(*) AS transactions_count,
                SUM(gross_sale) AS gross_revenue,
                SUM(platform_fee) AS total_fees,
                SUM(shipping_cost) AS total_shipping,
                SUM(net_profit) AS net_profit
            FROM transactions.orders
            WHERE status = 'completed'
            GROUP BY DATE(sold_at)
            ORDER BY sale_date DESC
        """
    },
    {
        'name': 'daily_sales',
        'sql': """
            SELECT
                DATE(sold_at) AS sale_date,
                COUNT(*) AS transactions,
                SUM(gross_sale) AS total_revenue,
                SUM(net_profit) AS total_profit,
                AVG(gross_sale) AS avg_price,
                AVG(net_profit) AS avg_profit
            FROM transactions.orders
            WHERE status = 'completed'
            GROUP BY DATE(sold_at)
            ORDER BY sale_date DESC
        """
    },
    {
        'name': 'data_quality_check',
        'sql': """
            SELECT 'Missing Net Profit' AS issue, COUNT(*) AS count
            FROM transactions.orders
            WHERE net_profit IS NULL AND status = 'completed'
            UNION ALL
            SELECT 'Missing Gross Sale' AS issue, COUNT(*) AS count
            FROM transactions.orders
            WHERE gross_sale IS NULL AND status = 'completed'
            UNION ALL
            SELECT 'Negative Profit' AS issue, COUNT(*) AS count
            FROM transactions.orders
            WHERE net_profit < 0 AND status = 'completed'
            UNION ALL
            SELECT 'Missing Platform Fee' AS issue, COUNT(*) AS count
            FROM transactions.orders
            WHERE platform_fee IS NULL AND status = 'completed'
        """
    },
    {
        'name': 'executive_dashboard',
        'sql': """
            SELECT
                COUNT(*) AS total_transactions,
                SUM(gross_sale) AS total_revenue,
                AVG(gross_sale) AS avg_order_value,
                COUNT(DISTINCT DATE(sold_at)) AS active_days,
                MIN(sold_at) AS first_sale_date,
                MAX(sold_at) AS last_sale_date
            FROM transactions.orders
            WHERE status = 'completed'
        """
    },
    {
        'name': 'monthly_revenue',
        'sql': """
            SELECT
                DATE_TRUNC('month', sold_at) AS month,
                COUNT(*) AS transactions_count,
                SUM(gross_sale) AS gross_revenue,
                SUM(platform_fee) AS total_fees,
                SUM(net_profit) AS net_profit
            FROM transactions.orders
            WHERE status = 'completed'
            GROUP BY DATE_TRUNC('month', sold_at)
            ORDER BY month DESC
        """
    },
    {
        'name': 'platform_performance',
        'sql': """
            SELECT
                p.name AS platform_name,
                COUNT(o.id) AS total_transactions,
                SUM(o.gross_sale) AS total_revenue,
                SUM(o.platform_fee) AS total_fees_paid,
                AVG(o.gross_sale) AS avg_transaction_value,
                SUM(o.net_profit) AS net_profit
            FROM transactions.orders o
            JOIN core.platforms p ON o.platform_id = p.id
            WHERE o.status = 'completed'
            GROUP BY p.name
            ORDER BY total_revenue DESC
        """
    },
    {
        'name': 'recent_transactions',
        'sql': """
            SELECT
                o.sold_at AS transaction_date,
                p.name AS product_name,
                pl.name AS platform_name,
                o.gross_sale AS sale_price,
                o.platform_fee,
                o.net_profit,
                o.buyer_destination_country,
                o.buyer_destination_city,
                o.status
            FROM transactions.orders o
            JOIN products.inventory i ON o.inventory_item_id = i.id
            JOIN products.products p ON i.product_id = p.id
            JOIN core.platforms pl ON o.platform_id = pl.id
            WHERE o.status = 'completed'
            ORDER BY o.sold_at DESC
            LIMIT 100
        """
    },
    {
        'name': 'sales_by_country',
        'sql': """
            SELECT
                COALESCE(buyer_destination_country, 'Unknown') AS destination_country,
                COUNT(*) AS total_sales,
                SUM(gross_sale) AS total_revenue,
                AVG(gross_sale) AS avg_order_value
            FROM transactions.orders
            WHERE status = 'completed'
            GROUP BY buyer_destination_country
            ORDER BY total_revenue DESC
        """
    },
    {
        'name': 'sales_by_weekday',
        'sql': """
            SELECT
                EXTRACT(DOW FROM sold_at) AS day_of_week_num,
                TO_CHAR(sold_at, 'Day') AS day_of_week_name,
                COUNT(*) AS total_sales,
                SUM(gross_sale) AS total_revenue,
                AVG(gross_sale) AS avg_order_value
            FROM transactions.orders
            WHERE status = 'completed'
            GROUP BY EXTRACT(DOW FROM sold_at), TO_CHAR(sold_at, 'Day')
            ORDER BY day_of_week_num
        """
    },
    {
        'name': 'top_products',
        'sql': """
            SELECT
                p.name,
                p.sku,
                COUNT(o.*) AS sales_count,
                SUM(o.gross_sale) AS total_revenue,
                SUM(o.net_profit) AS total_profit,
                AVG(o.gross_sale) AS avg_price
            FROM products.products p
            JOIN products.inventory i ON p.id = i.product_id
            JOIN transactions.orders o ON i.id = o.inventory_item_id
            WHERE o.status = 'completed'
            GROUP BY p.id, p.name, p.sku
            ORDER BY total_revenue DESC
            LIMIT 50
        """
    },
    {
        'name': 'top_products_revenue',
        'sql': """
            SELECT
                p.name AS product_name,
                p.sku AS product_sku,
                b.name AS brand_name,
                COUNT(o.id) AS total_sales,
                SUM(o.gross_sale) AS total_revenue,
                AVG(o.gross_sale) AS avg_sale_price,
                SUM(o.net_profit) AS total_profit
            FROM transactions.orders o
            JOIN products.inventory i ON o.inventory_item_id = i.id
            JOIN products.products p ON i.product_id = p.id
            JOIN products.brands b ON p.brand_id = b.id
            WHERE o.status = 'completed'
            GROUP BY p.name, p.sku, b.name
            ORDER BY total_revenue DESC
            LIMIT 50
        """
    }
]


async def migrate_views():
    db = DatabaseManager()
    await db.initialize()

    print("=" * 80)
    print("MIGRATING LOW-COMPLEXITY ANALYTICS VIEWS")
    print("=" * 80)
    print(f"Total views to migrate: {len(LOW_COMPLEXITY_VIEWS)}\n")

    async with db.get_session() as session:
        success_count = 0
        error_count = 0

        for idx, view in enumerate(LOW_COMPLEXITY_VIEWS, 1):
            try:
                print(f"[{idx}/{len(LOW_COMPLEXITY_VIEWS)}] Migrating {view['name']}...")

                # Drop existing view
                await session.execute(text(f"DROP VIEW IF EXISTS analytics.{view['name']} CASCADE"))

                # Create new view
                create_sql = f"CREATE VIEW analytics.{view['name']} AS {view['sql']}"
                await session.execute(text(create_sql))

                await session.commit()

                success_count += 1
                print(f"    Success")

            except Exception as e:
                error_count += 1
                print(f"    ERROR: {str(e)[:200]}")
                await session.rollback()

        print(f"\n{'='*80}")
        print(f"MIGRATION SUMMARY")
        print(f"{'='*80}")
        print(f"  Total views: {len(LOW_COMPLEXITY_VIEWS)}")
        print(f"  Successful: {success_count}")
        print(f"  Errors: {error_count}")

        if success_count > 0:
            print(f"\n[OK] {success_count}/{len(LOW_COMPLEXITY_VIEWS)} views migrated successfully!")

    await db.close()


if __name__ == "__main__":
    asyncio.run(migrate_views())

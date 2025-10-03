"""
Verify Synced Sales in Database
Shows recently synced sales with all new fields
"""
import asyncio
from sqlalchemy import text
from shared.database.connection import DatabaseManager


async def main():
    """Verify synced sales"""
    db = DatabaseManager()
    await db.initialize()

    try:
        async with db.get_session() as session:
            # Get recent orders with all new fields
            result = await session.execute(text("""
                SELECT
                    o.stockx_order_number,
                    p.sku,
                    p.name AS product_name,
                    sz.value AS size,
                    s.name AS supplier,

                    -- Purchase fields
                    i.purchase_price AS net_buy,
                    i.gross_purchase_price,
                    i.vat_amount,
                    i.vat_rate,
                    i.purchase_date,
                    i.delivery_date,

                    -- Sale fields
                    o.sold_at,
                    o.gross_sale,
                    o.net_proceeds,
                    o.net_profit,
                    o.roi,
                    o.shelf_life_days,
                    o.payout_received,

                    -- Metadata
                    o.status,
                    o.created_at
                FROM transactions.orders o
                JOIN products.inventory i ON o.inventory_item_id = i.id
                JOIN products.products p ON i.product_id = p.id
                JOIN core.sizes sz ON i.size_id = sz.id
                JOIN core.suppliers s ON i.supplier_id = s.id
                ORDER BY o.created_at DESC
                LIMIT 5
            """))

            orders = result.fetchall()

            print("=" * 120)
            print("RECENTLY SYNCED SALES")
            print("=" * 120)
            print()

            for i, order in enumerate(orders, 1):
                print(f"[{i}] {order.sku} - Size {order.size}")
                print(f"    StockX Order: {order.stockx_order_number}")
                print(f"    Supplier: {order.supplier}")
                print()
                print("    PURCHASE:")
                print(f"      Net Buy:     €{order.net_buy:,.2f}")
                print(f"      Gross Buy:   €{order.gross_purchase_price:,.2f}" if order.gross_purchase_price else "      Gross Buy:   N/A")
                print(f"      VAT:         €{order.vat_amount:,.2f} ({order.vat_rate}%)" if order.vat_amount else "      VAT:         N/A")
                print(f"      Buy Date:    {order.purchase_date.date() if order.purchase_date else 'N/A'}")
                print(f"      Delivery:    {order.delivery_date.date() if order.delivery_date else 'N/A'}")
                print()
                print("    SALE:")
                print(f"      Sold Date:   {order.sold_at.date() if order.sold_at else 'N/A'}")
                print(f"      Gross Sale:  €{order.gross_sale:,.2f}" if order.gross_sale else "      Gross Sale:  N/A")
                print(f"      Net Sale:    €{order.net_proceeds:,.2f}" if order.net_proceeds else "      Net Sale:    N/A")
                print(f"      Profit:      €{order.net_profit:,.2f}" if order.net_profit else "      Profit:      N/A")
                print(f"      ROI:         {order.roi:,.2f}%" if order.roi else "      ROI:         N/A")
                print(f"      Shelf Life:  {order.shelf_life_days} days" if order.shelf_life_days is not None else "      Shelf Life:  N/A")
                print(f"      Payout:      {'[OK] Received' if order.payout_received else '[PENDING]'}")
                print()
                print(f"    Status: {order.status}")
                print(f"    Synced: {order.created_at}")
                print("-" * 120)
                print()

            print()
            print(f"Total orders in database: {len(orders)} shown (most recent)")
            print()

            # Summary stats
            result = await session.execute(text("""
                SELECT
                    COUNT(*) as total_orders,
                    COUNT(DISTINCT i.supplier_id) as unique_suppliers,
                    COUNT(DISTINCT i.product_id) as unique_products,
                    SUM(o.net_profit) as total_profit,
                    AVG(o.roi) as avg_roi,
                    AVG(o.shelf_life_days) as avg_shelf_life
                FROM transactions.orders o
                JOIN products.inventory i ON o.inventory_item_id = i.id
            """))

            stats = result.fetchone()

            print("=" * 120)
            print("DATABASE STATISTICS")
            print("=" * 120)
            print(f"Total Orders:       {stats.total_orders}")
            print(f"Unique Suppliers:   {stats.unique_suppliers}")
            print(f"Unique Products:    {stats.unique_products}")
            print(f"Total Profit:       €{stats.total_profit:,.2f}" if stats.total_profit else "Total Profit:       €0.00")
            print(f"Average ROI:        {stats.avg_roi:,.2f}%" if stats.avg_roi else "Average ROI:        N/A")
            print(f"Avg Shelf Life:     {stats.avg_shelf_life:.1f} days" if stats.avg_shelf_life else "Avg Shelf Life:     N/A")
            print("=" * 120)

    finally:
        await db.close()


if __name__ == '__main__':
    asyncio.run(main())
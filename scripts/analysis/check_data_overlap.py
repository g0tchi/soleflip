"""Check for duplicate data between transactions.orders and transactions.transactions"""

import asyncio

from sqlalchemy import text

from shared.database.connection import DatabaseManager


async def check_overlap():
    db = DatabaseManager()
    await db.initialize()

    async with db.get_session() as session:
        # Check for overlapping external_id / stockx_order_number
        print("=" * 80)
        print("CHECKING FOR DUPLICATE DATA")
        print("=" * 80)

        result = await session.execute(
            text(
                """
            SELECT
                o.stockx_order_number,
                o.sold_at as order_sold_at,
                t.external_id,
                t.transaction_date,
                o.net_proceeds as order_net,
                t.sale_price as trans_price
            FROM transactions.orders o
            LEFT JOIN transactions.transactions t
                ON t.external_id LIKE '%' || o.stockx_order_number || '%'
                OR o.stockx_order_number LIKE '%' || t.external_id || '%'
            WHERE t.id IS NOT NULL
        """
            )
        )

        matches = list(result)
        print(f"\nOverlapping StockX Order Numbers: {len(matches)}")

        if matches:
            print("\n[!] DUPLICATES FOUND:")
            for row in matches:
                print(
                    f"\n  Orders: {row.stockx_order_number} ({row.order_sold_at}) - EUR{row.order_net}"
                )
                print(
                    f"  Trans:  {row.external_id} ({row.transaction_date}) - EUR{row.trans_price}"
                )
        else:
            print("\n[OK] NO OVERLAP by order number - Different data sets!")

        # Check inventory_id overlap
        result = await session.execute(
            text(
                """
            SELECT
                COUNT(DISTINCT o.inventory_item_id) as order_items,
                COUNT(DISTINCT t.inventory_id) as trans_items,
                COUNT(DISTINCT CASE WHEN EXISTS (
                    SELECT 1 FROM transactions.transactions t2
                    WHERE t2.inventory_id = o.inventory_item_id
                ) THEN o.inventory_item_id END) as shared_items
            FROM transactions.orders o
            CROSS JOIN transactions.transactions t
        """
            )
        )

        stats = result.fetchone()
        print("\n" + "=" * 80)
        print("INVENTORY OVERLAP CHECK")
        print("=" * 80)
        print(f"  Items in orders table: {stats.order_items}")
        print(f"  Items in transactions table: {stats.trans_items}")
        print(f"  Shared inventory items: {stats.shared_items}")

        if stats.shared_items == 0:
            print("\n[OK] NO SHARED INVENTORY - Completely separate datasets!")
        else:
            print(f"\n[!] {stats.shared_items} inventory items exist in both tables")

        # Date range comparison
        result = await session.execute(
            text(
                """
            SELECT
                MIN(sold_at) as order_min,
                MAX(sold_at) as order_max,
                MIN(transaction_date) as trans_min,
                MAX(transaction_date) as trans_max
            FROM transactions.orders o
            CROSS JOIN transactions.transactions t
        """
            )
        )

        dates = result.fetchone()
        print("\n" + "=" * 80)
        print("DATE RANGE COMPARISON")
        print("=" * 80)
        print(f"Orders table:       {dates.order_min.date()} → {dates.order_max.date()}")
        print(f"Transactions table: {dates.trans_min.date()} → {dates.trans_max.date()}")

    await db.close()


if __name__ == "__main__":
    asyncio.run(check_overlap())

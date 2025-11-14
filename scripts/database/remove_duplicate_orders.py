"""
Remove duplicate orders that were synced from Notion but already existed in legacy data
Keep the legacy data as it has more accurate historical information
"""

import asyncio

from sqlalchemy import text

from shared.database.connection import DatabaseManager


async def remove_duplicates():
    db = DatabaseManager()
    await db.initialize()

    async with db.get_session() as session:
        print("=" * 80)
        print("REMOVING DUPLICATE ORDERS (NOTION SYNC)")
        print("=" * 80)

        # Find duplicates (Notion orders that match legacy orders)
        result = await session.execute(
            text(
                """
            SELECT o.id, o.stockx_order_number, o.sold_at, o.net_proceeds,
                   t.external_id, t.sold_at as legacy_sold_at, t.gross_sale
            FROM transactions.orders o
            JOIN transactions.orders t ON (
                t.external_id LIKE '%' || o.stockx_order_number || '%'
                AND t.id != o.id
            )
            WHERE o.stockx_order_number IS NOT NULL
              AND t.external_id LIKE 'stockx_%'
            ORDER BY o.sold_at DESC
        """
            )
        )

        duplicates = list(result)
        print(f"\nFound {len(duplicates)} duplicate orders from Notion sync:")

        if not duplicates:
            print("No duplicates found!")
            return

        print("\nDuplicates to remove:")
        for row in duplicates[:5]:
            print(
                f"  Notion: {row.stockx_order_number} ({row.sold_at.date()}) - EUR{row.net_proceeds}"
            )
            print(
                f"  Legacy: {row.external_id} ({row.legacy_sold_at.date()}) - EUR{row.gross_sale}"
            )
            print()

        if len(duplicates) > 5:
            print(f"  ... and {len(duplicates) - 5} more")

        # Delete duplicates (keep the ones with external_id starting with 'stockx_')
        print("\n" + "=" * 80)
        print("Deleting Notion-synced duplicates...")

        result = await session.execute(
            text(
                """
            DELETE FROM transactions.orders
            WHERE id IN (
                SELECT o.id
                FROM transactions.orders o
                WHERE EXISTS (
                    SELECT 1 FROM transactions.orders t
                    WHERE t.external_id LIKE 'stockx_%' ||  o.stockx_order_number || '%'
                      AND t.id != o.id
                )
                AND (o.external_id IS NULL OR o.external_id NOT LIKE 'stockx_%')
            )
        """
            )
        )

        await session.commit()
        print(f"[OK] Deleted {result.rowcount} duplicate orders")

        # Verify final count
        result = await session.execute(
            text(
                """
            SELECT COUNT(*) as total FROM transactions.orders
        """
            )
        )
        final_count = result.fetchone()[0]
        print(f"[OK] Orders table now has {final_count} records (no duplicates)")

    await db.close()


if __name__ == "__main__":
    asyncio.run(remove_duplicates())

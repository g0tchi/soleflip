"""
Check transactions schema tables: orders and transactions
"""

import asyncio

from sqlalchemy import text

from shared.database.connection import DatabaseManager


async def main():
    db = DatabaseManager()
    await db.initialize()

    async with db.get_session() as session:
        # Get orders table info
        print("=" * 80)
        print("TRANSACTIONS.ORDERS TABLE")
        print("=" * 80)

        result = await session.execute(
            text(
                """
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = 'transactions'
            AND table_name = 'orders'
            ORDER BY ordinal_position
        """
            )
        )

        print("\nColumns:")
        for row in result:
            nullable = "NULL" if row.is_nullable == "YES" else "NOT NULL"
            default = f" DEFAULT {row.column_default}" if row.column_default else ""
            print(f"  {row.column_name:30} {row.data_type:20} {nullable}{default}")

        # Count records
        result = await session.execute(text("SELECT COUNT(*) FROM transactions.orders"))
        count = result.scalar()
        print(f"\nTotal Records: {count}")

        # Sample data
        result = await session.execute(
            text(
                """
            SELECT
                id,
                stockx_order_number,
                status,
                sold_at,
                gross_sale,
                net_proceeds,
                roi,
                payout_received,
                created_at
            FROM transactions.orders
            ORDER BY created_at DESC
            LIMIT 5
        """
            )
        )

        print("\nRecent Orders (5 most recent):")
        for row in result:
            print(f"\n  Order ID: {row.id}")
            print(f"  StockX: {row.stockx_order_number}")
            print(f"  Status: {row.status}")
            print(f"  Sold: {row.sold_at}")
            print(f"  Gross: €{row.gross_sale}")
            print(f"  Net: €{row.net_proceeds}")
            print(f"  ROI: {row.roi}%")
            print(f"  Payout: {row.payout_received}")

        # Get transactions table info
        print("\n" + "=" * 80)
        print("TRANSACTIONS.TRANSACTIONS TABLE")
        print("=" * 80)

        result = await session.execute(
            text(
                """
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = 'transactions'
            AND table_name = 'transactions'
            ORDER BY ordinal_position
        """
            )
        )

        print("\nColumns:")
        for row in result:
            nullable = "NULL" if row.is_nullable == "YES" else "NOT NULL"
            default = f" DEFAULT {row.column_default}" if row.column_default else ""
            print(f"  {row.column_name:30} {row.data_type:20} {nullable}{default}")

        # Count records
        result = await session.execute(text("SELECT COUNT(*) FROM transactions.transactions"))
        count = result.scalar()
        print(f"\nTotal Records: {count}")

        # Sample data if exists
        if count > 0:
            result = await session.execute(
                text(
                    """
                SELECT
                    id,
                    external_id,
                    status,
                    transaction_date,
                    sale_price,
                    created_at
                FROM transactions.transactions
                ORDER BY created_at DESC
                LIMIT 5
            """
                )
            )

            print("\nRecent Transactions (5 most recent):")
            for row in result:
                print(f"\n  Transaction ID: {row.id}")
                print(f"  External ID: {row.external_id}")
                print(f"  Status: {row.status}")
                print(f"  Date: {row.transaction_date}")
                print(f"  Price: €{row.sale_price}")

        # Check for overlaps/relationships
        print("\n" + "=" * 80)
        print("RELATIONSHIP ANALYSIS")
        print("=" * 80)

        # Check if orders reference transactions
        result = await session.execute(
            text(
                """
            SELECT
                c.column_name,
                c.data_type,
                tc.constraint_type,
                kcu.table_schema || '.' || kcu.table_name AS references
            FROM information_schema.columns c
            LEFT JOIN information_schema.key_column_usage kcu
                ON c.table_schema = kcu.table_schema
                AND c.table_name = kcu.table_name
                AND c.column_name = kcu.column_name
            LEFT JOIN information_schema.table_constraints tc
                ON kcu.constraint_name = tc.constraint_name
            WHERE c.table_schema = 'transactions'
            AND c.table_name = 'orders'
            AND tc.constraint_type = 'FOREIGN KEY'
        """
            )
        )

        fkeys = result.fetchall()
        if fkeys:
            print("\nForeign Keys in orders table:")
            for row in fkeys:
                print(f"  {row.column_name} -> {row.references}")
        else:
            print("\nNo foreign keys found between orders and transactions tables")

        # Check data overlap
        result = await session.execute(
            text(
                """
            SELECT
                (SELECT COUNT(*) FROM transactions.orders) as orders_count,
                (SELECT COUNT(*) FROM transactions.transactions) as transactions_count,
                (SELECT COUNT(DISTINCT inventory_item_id) FROM transactions.orders) as unique_inventory_in_orders
        """
            )
        )

        row = result.fetchone()
        print("\nData Summary:")
        print(f"  Orders table: {row.orders_count} records")
        print(f"  Transactions table: {row.transactions_count} records")
        print(f"  Unique inventory items in orders: {row.unique_inventory_in_orders}")

    await db.close()


if __name__ == "__main__":
    asyncio.run(main())

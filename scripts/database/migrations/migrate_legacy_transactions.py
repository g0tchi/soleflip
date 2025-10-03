"""
Migrate data from transactions.transactions to transactions.orders
This unifies all transaction data into a single multi-platform table
"""
import asyncio
from sqlalchemy import text
from shared.database.connection import DatabaseManager


async def migrate_legacy_transactions():
    db = DatabaseManager()
    await db.initialize()

    async with db.get_session() as session:
        print("=" * 80)
        print("MIGRATING LEGACY TRANSACTIONS TO ORDERS TABLE")
        print("=" * 80)

        # Step 1: Check what we're working with
        result = await session.execute(text("""
            SELECT COUNT(*) as total,
                   COUNT(DISTINCT external_id) as unique_external_ids,
                   MIN(transaction_date) as earliest,
                   MAX(transaction_date) as latest
            FROM transactions.transactions
        """))
        stats = result.fetchone()
        print("\nLegacy transactions table:")
        print(f"  Total records: {stats.total}")
        print(f"  Unique external_ids: {stats.unique_external_ids}")
        print(f"  Date range: {stats.earliest.date()} to {stats.latest.date()}")

        # Step 2: Find duplicates (transactions that match existing orders)
        result = await session.execute(text("""
            SELECT COUNT(*) as duplicate_count
            FROM transactions.transactions t
            WHERE EXISTS (
                SELECT 1 FROM transactions.orders o
                WHERE o.stockx_order_number LIKE '%' || REPLACE(t.external_id, 'stockx_', '') || '%'
                   OR t.external_id LIKE '%' || o.stockx_order_number || '%'
            )
        """))
        duplicate_count = result.fetchone()[0]
        print(f"\n  Duplicates (already in orders): {duplicate_count}")
        print(f"  Unique to migrate: {stats.total - duplicate_count}")

        # Step 3: Show sample of what will be migrated
        result = await session.execute(text("""
            SELECT t.external_id, t.transaction_date, t.sale_price, t.status
            FROM transactions.transactions t
            WHERE NOT EXISTS (
                SELECT 1 FROM transactions.orders o
                WHERE o.stockx_order_number LIKE '%' || REPLACE(t.external_id, 'stockx_', '') || '%'
                   OR t.external_id LIKE '%' || o.stockx_order_number || '%'
            )
            ORDER BY t.transaction_date DESC
            LIMIT 5
        """))

        print("\nSample records to migrate:")
        for row in result:
            print(f"  {row.external_id} | {row.transaction_date.date()} | EUR{row.sale_price} | {row.status}")

        # Step 4: Ask for confirmation
        print("\n" + "=" * 80)
        response = input("\nMigrate these records? (yes/no): ")

        if response.lower() != 'yes':
            print("Migration aborted.")
            return

        # Step 5: Perform the migration
        print("\nMigrating...")

        result = await session.execute(text("""
            INSERT INTO transactions.orders (
                id,
                platform_id,
                inventory_item_id,
                external_id,
                stockx_order_number,
                status,
                sold_at,
                gross_sale,
                net_proceeds,
                platform_fee,
                shipping_cost,
                net_profit,
                buyer_destination_country,
                buyer_destination_city,
                notes,
                created_at,
                updated_at
            )
            SELECT
                gen_random_uuid() as id,
                t.platform_id,
                t.inventory_id as inventory_item_id,
                t.external_id,
                REPLACE(t.external_id, 'stockx_', '') as stockx_order_number,
                t.status,
                t.transaction_date as sold_at,
                t.sale_price as gross_sale,
                t.net_profit + t.platform_fee + t.shipping_cost as net_proceeds,
                t.platform_fee,
                t.shipping_cost,
                t.net_profit,
                t.buyer_destination_country,
                t.buyer_destination_city,
                t.notes,
                t.created_at,
                t.updated_at
            FROM transactions.transactions t
            WHERE NOT EXISTS (
                SELECT 1 FROM transactions.orders o
                WHERE o.stockx_order_number LIKE '%' || REPLACE(t.external_id, 'stockx_', '') || '%'
                   OR t.external_id LIKE '%' || o.stockx_order_number || '%'
            )
        """))

        await session.commit()
        print(f"[OK] Migrated {result.rowcount} records to orders table")

        # Step 6: Verify migration
        result = await session.execute(text("""
            SELECT COUNT(*) as total FROM transactions.orders
        """))
        new_total = result.fetchone()[0]
        print(f"[OK] Orders table now has {new_total} total records")

    await db.close()


if __name__ == "__main__":
    asyncio.run(migrate_legacy_transactions())

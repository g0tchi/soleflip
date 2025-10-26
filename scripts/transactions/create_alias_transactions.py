#!/usr/bin/env python3
"""
Create transactions from existing Alias batch
"""
import asyncio
import sys

sys.path.append(".")

from sqlalchemy import text

from domains.sales.services.order_processor import OrderProcessor
from shared.database.connection import DatabaseManager, db_manager


async def create_alias_transactions():
    """Create transactions from the existing processed Alias batch"""

    print("Creating transactions from Alias batch")
    print("=" * 50)

    db = DatabaseManager()
    await db.initialize()

    # Also initialize the global db_manager used by OrderProcessor
    await db_manager.initialize()

    try:
        # Get the latest Alias batch ID
        async with db.get_session() as session:
            batch_result = await session.execute(
                text(
                    """
                SELECT id, total_records, processed_records 
                FROM integration.import_batches 
                WHERE source_type = 'alias' 
                ORDER BY created_at DESC 
                LIMIT 1
            """
                )
            )

            batch = batch_result.fetchone()
            if not batch:
                print("No Alias batch found!")
                return

            batch_id = str(batch.id)
            print(f"Processing Alias batch: {batch_id[:8]}...")
            print(f"Records: {batch.processed_records}/{batch.total_records}")

        # Create transaction processor and process the batch
        print("\nStarting transaction creation...")
        processor = OrderProcessor()
        stats = await processor.create_orders_from_batch(batch_id)

        print("\nTransaction creation completed!")
        print("Stats:")
        for key, value in stats.items():
            if key == "errors" and isinstance(value, list):
                print(f"  {key}: {len(value)} errors")
                if value:
                    print("  First few errors:")
                    for error in value[:3]:
                        print(f"    - {error}")
            else:
                print(f"  {key}: {value}")

        # Verify results
        print("\nVerifying transaction creation...")
        async with db.get_session() as session:
            # Count new transactions
            tx_result = await session.execute(
                text(
                    """
                SELECT COUNT(*) as count,
                       pl.name as platform_name
                FROM sales.transactions t
                LEFT JOIN core.platforms pl ON t.platform_id = pl.id
                WHERE t.created_at >= CURRENT_TIMESTAMP - INTERVAL '10 minutes'
                GROUP BY pl.name
            """
                )
            )

            tx_counts = tx_result.fetchall()
            if tx_counts:
                print("Recent transactions created:")
                for tx in tx_counts:
                    print(f"  {tx.platform_name}: {tx.count} transactions")
            else:
                print("No recent transactions found")

    finally:
        await db.close()
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(create_alias_transactions())

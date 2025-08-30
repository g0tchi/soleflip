#!/usr/bin/env python3
"""
Check if Alias transactions were created successfully
"""
import asyncio
import sys
from pathlib import Path

sys.path.append(".")

from shared.database.connection import DatabaseManager
from sqlalchemy import text


async def check_alias_transactions():
    """Check if Alias transactions were properly created"""

    print("Checking Alias Transaction Processing")
    print("=" * 50)

    db = DatabaseManager()
    await db.initialize()

    try:
        async with db.get_session() as session:
            # Get the latest Alias batch
            latest_batch_result = await session.execute(
                text(
                    """
                SELECT id, total_records, processed_records, completed_at
                FROM integration.import_batches 
                WHERE source_type = 'alias'
                ORDER BY created_at DESC
                LIMIT 1
            """
                )
            )

            latest_batch = latest_batch_result.fetchone()
            if not latest_batch:
                print("No Alias batches found!")
                return

            print(f"Latest Alias Batch: {latest_batch.id}")
            print(f"Records: {latest_batch.processed_records}/{latest_batch.total_records}")
            print(f"Completed: {latest_batch.completed_at}")

            # Check transactions created from this batch
            transactions_result = await session.execute(
                text(
                    """
                SELECT 
                    COUNT(*) as transaction_count,
                    MIN(t.transaction_date) as earliest_date,
                    MAX(t.transaction_date) as latest_date,
                    SUM(t.sale_price) as total_revenue,
                    SUM(t.net_profit) as total_profit,
                    AVG(t.sale_price) as avg_price
                FROM sales.transactions t
                WHERE t.notes ILIKE '%alias%' 
                   OR t.external_id ILIKE 'alias_%'
                   OR t.created_at >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
            """
                )
            )

            transaction_stats = transactions_result.fetchone()

            print(f"\\nTransaction Statistics:")
            print(f"  Transactions created: {transaction_stats.transaction_count}")
            print(
                f"  Date range: {transaction_stats.earliest_date} to {transaction_stats.latest_date}"
            )
            print(f"  Total revenue: ${transaction_stats.total_revenue or 0}")
            print(f"  Average price: ${transaction_stats.avg_price or 0:.2f}")

            # Sample of recent transactions
            sample_result = await session.execute(
                text(
                    """
                SELECT 
                    t.external_id,
                    t.sale_price,
                    t.transaction_date,
                    t.status,
                    p.name as product_name,
                    s.value as size,
                    pl.name as platform_name
                FROM sales.transactions t
                LEFT JOIN products.inventory i ON t.inventory_id = i.id
                LEFT JOIN products.products p ON i.product_id = p.id  
                LEFT JOIN core.sizes s ON i.size_id = s.id
                LEFT JOIN core.platforms pl ON t.platform_id = pl.id
                WHERE t.created_at >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
                ORDER BY t.created_at DESC
                LIMIT 5
            """
                )
            )

            sample_transactions = sample_result.fetchall()

            print(f"\\nSample Recent Transactions ({len(sample_transactions)}):")
            for tx in sample_transactions:
                print(
                    f"  {tx.external_id}: {tx.product_name} (Size {tx.size}) - ${tx.sale_price} on {tx.platform_name}"
                )

            # Check platform distribution
            platform_result = await session.execute(
                text(
                    """
                SELECT 
                    pl.name as platform_name,
                    COUNT(*) as transaction_count
                FROM sales.transactions t
                JOIN core.platforms pl ON t.platform_id = pl.id
                WHERE t.created_at >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
                GROUP BY pl.name
                ORDER BY transaction_count DESC
            """
                )
            )

            platform_stats = platform_result.fetchall()

            print(f"\\nPlatform Distribution (Last Hour):")
            for platform in platform_stats:
                print(f"  {platform.platform_name}: {platform.transaction_count} transactions")

            # Check for any processing errors
            error_result = await session.execute(
                text(
                    """
                SELECT 
                    COUNT(*) as error_count,
                    error_message
                FROM integration.import_records 
                WHERE batch_id = :batch_id
                  AND status = 'failed'
                GROUP BY error_message
            """
                ),
                {"batch_id": latest_batch.id},
            )

            errors = error_result.fetchall()

            if errors:
                print(f"\\nProcessing Errors:")
                for error in errors:
                    print(f"  {error.error_count} records: {error.error_message}")
            else:
                print(f"\\nNo processing errors found! All records processed successfully.")

    except Exception as e:
        print(f"ERROR: Failed to check transactions: {e}")

    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(check_alias_transactions())

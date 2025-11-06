"""
Run Bulk Sync with Notion Sales Data
Executes bulk sync with sales data collected from Notion MCP

This script is designed to be populated with sales data by Claude Code,
then executed to sync all sales to PostgreSQL.

Usage from Claude Code:
1. Claude fetches all sales from Notion
2. Claude populates SALES_DATA list below
3. Claude executes: python run_bulk_sync_with_notion_data.py --dry-run
4. After review: python run_bulk_sync_with_notion_data.py
"""

import asyncio
from sync_notion_to_postgres import NotionPostgresSyncService
import structlog

logger = structlog.get_logger(__name__)

# ==============================================================================
# SALES DATA - To be populated by Claude Code with Notion MCP
# ==============================================================================
# Each sale should have format:
# {
#     'properties': {
#         'SKU': 'FZ4159-100',
#         'Brand': 'Jordan',
#         'Size': '8',
#         'Type': 'US',
#         'Supplier': 'BSTN',
#         'Gross Buy': 115.99,
#         'VAT?': True,
#         'date:Buy Date:start': '2024-07-24',
#         ... (all other fields)
#     },
#     'url': 'https://www.notion.so/...'
# }

SALES_DATA = [
    # Claude will populate this list
]

# ==============================================================================


async def main():
    """Execute bulk sync with collected Notion data"""
    import sys

    # Parse command line args
    dry_run = "--dry-run" in sys.argv

    print("=" * 80)
    print("NOTION -> POSTGRESQL BULK SYNC")
    print("=" * 80)
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE SYNC'}")
    print(f"Sales to process: {len(SALES_DATA)}")
    print("=" * 80)
    print()

    if not SALES_DATA:
        print("[ERROR] No sales data available!")
        print()
        print("SALES_DATA must be populated by Claude Code before running.")
        print("Claude will fetch all sales from Notion and populate this list.")
        return

    # Initialize sync service
    service = NotionPostgresSyncService(dry_run=dry_run)

    try:
        await service.initialize()

        # Get database session
        if not dry_run:
            session = await service.db_manager.get_session().__aenter__()
        else:
            session = None

        # Process each sale
        processed = 0

        for i, sale in enumerate(SALES_DATA, 1):
            # Parse Notion properties
            sale_data = service.parse_notion_properties(sale["properties"], sale["url"])

            if not sale_data:
                logger.warning(f"Skipping invalid sale [{i}/{len(SALES_DATA)}]")
                service.stats["skipped_invalid"] += 1
                continue

            service.stats["total_found"] += 1

            # Filter: Only StockX
            if sale_data["sale_platform"] != "StockX":
                continue

            # Check if already synced
            if not dry_run:
                if await service.check_if_synced(session, sale_data["sale_id"]):
                    logger.info(f"Already synced: {sale_data['sale_id']}")
                    service.stats["already_synced"] += 1
                    continue

            # Sync
            if dry_run:
                logger.info(f"[DRY RUN] Would sync: {sale_data['sale_id']}")
                service.stats["newly_synced"] += 1
            else:
                success = await service.sync_sale(session, sale_data)
                if success:
                    processed += 1

                    # Commit every 10 sales
                    if processed % 10 == 0:
                        await session.commit()
                        logger.info(f"Checkpoint: {processed} sales committed")

            # Progress
            if i % 20 == 0:
                print(f"Progress: {i}/{len(SALES_DATA)} processed")

        # Final commit
        if not dry_run and session:
            await session.commit()

        # Summary
        print()
        service.print_summary()

    finally:
        if not dry_run and "session" in locals() and session:
            await session.__aexit__(None, None, None)
        await service.close()


if __name__ == "__main__":
    asyncio.run(main())

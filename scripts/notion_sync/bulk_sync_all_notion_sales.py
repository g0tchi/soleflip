"""
Bulk Sync ALL Notion Sales to PostgreSQL
Fetches all sales from Notion Inventory database and syncs to PostgreSQL

This script uses the proven sync logic from test_notion_sync_single.py
and extends it to handle all sales from the Notion database.

Usage:
    # Dry run first (recommended)
    python bulk_sync_all_notion_sales.py --dry-run

    # Real sync
    python bulk_sync_all_notion_sales.py

    # Sync only StockX sales
    python bulk_sync_all_notion_sales.py --platform StockX

    # Skip already synced
    python bulk_sync_all_notion_sales.py --skip-existing
"""

import argparse
import asyncio
from typing import Dict, List

import structlog
from sync_notion_to_postgres import NotionPostgresSyncService

logger = structlog.get_logger(__name__)

# This will be populated with real Notion data via MCP
NOTION_SALES_DATA = []


async def fetch_all_notion_sales() -> List[Dict]:
    """
    Fetch all sales from Notion Inventory database

    NOTE: This function is designed to be called from Claude Code
    with access to Notion MCP. The actual fetching happens via
    mcp__notion__notion-search and mcp__notion__notion-fetch.

    For standalone execution, populate NOTION_SALES_DATA manually.
    """
    if NOTION_SALES_DATA:
        logger.info(f"Using {len(NOTION_SALES_DATA)} pre-loaded Notion sales")
        return NOTION_SALES_DATA

    logger.warning("No Notion sales data loaded!")
    logger.warning("Run this script from Claude Code with Notion MCP access,")
    logger.warning("or populate NOTION_SALES_DATA manually.")
    return []


async def main():
    """Main bulk sync entry point"""
    parser = argparse.ArgumentParser(description="Bulk sync all Notion sales")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no DB writes)")
    parser.add_argument("--platform", type=str, default="StockX", help="Filter by platform")
    parser.add_argument("--skip-existing", action="store_true", help="Skip already synced sales")
    parser.add_argument("--limit", type=int, help="Limit number of sales to sync")
    args = parser.parse_args()

    print("=" * 80)
    print("BULK SYNC: NOTION -> POSTGRESQL")
    print("=" * 80)
    print(f"Mode:          {'DRY RUN' if args.dry_run else 'LIVE SYNC'}")
    print(f"Platform:      {args.platform}")
    print(f"Skip existing: {args.skip_existing}")
    if args.limit:
        print(f"Limit:         {args.limit} sales")
    print("=" * 80)
    print()

    # Fetch all Notion sales
    print("Fetching Notion sales data...")
    notion_sales = await fetch_all_notion_sales()

    if not notion_sales:
        print()
        print("[ERROR] No Notion sales data available!")
        print()
        print("This script requires Notion sales data to be loaded.")
        print("Run from Claude Code with Notion MCP access.")
        print()
        return

    print(f"Found {len(notion_sales)} sales in Notion")
    print()

    # Initialize sync service
    service = NotionPostgresSyncService(dry_run=args.dry_run)

    try:
        await service.initialize()

        # Get database session
        if not args.dry_run:
            session = await service.db_manager.get_session().__aenter__()
        else:
            session = None

        # Process each sale
        processed = 0
        for i, notion_sale in enumerate(notion_sales, 1):
            if args.limit and processed >= args.limit:
                logger.info(f"Reached limit of {args.limit} sales")
                break

            # Parse Notion properties
            sale_data = service.parse_notion_properties(
                notion_sale["properties"], notion_sale["url"]
            )

            if not sale_data:
                logger.warning(f"Skipping invalid sale [{i}/{len(notion_sales)}]")
                service.stats["skipped_invalid"] += 1
                continue

            service.stats["total_found"] += 1

            # Filter by platform
            if sale_data["sale_platform"] != args.platform:
                logger.debug(f"Skipping non-{args.platform} sale: {sale_data['sale_id']}")
                continue

            # Check if already synced
            if not args.dry_run and args.skip_existing:
                if await service.check_if_synced(session, sale_data["sale_id"]):
                    logger.info(f"Skipping already synced: {sale_data['sale_id']}")
                    service.stats["already_synced"] += 1
                    continue

            # Sync to database
            if args.dry_run:
                # Just validate in dry run
                logger.info(f"[DRY RUN] Would sync: {sale_data['sale_id']} ({sale_data['sku']})")
                service.stats["newly_synced"] += 1
            else:
                # Real sync
                success = await service.sync_sale(session, sale_data)
                if success:
                    processed += 1

                    # Commit every 10 sales for safety
                    if processed % 10 == 0:
                        await session.commit()
                        logger.info(f"Checkpoint: Committed {processed} sales")

            # Progress update every 50 sales
            if i % 50 == 0:
                print(f"Progress: {i}/{len(notion_sales)} sales processed")

        # Final commit
        if not args.dry_run and session:
            await session.commit()
            logger.info("Final commit completed")

        # Print summary
        print()
        service.print_summary()

        # Show some statistics
        if service.stats["newly_synced"] > 0:
            print()
            print("=" * 80)
            print("RECOMMENDATIONS")
            print("=" * 80)
            if args.dry_run:
                print("DRY RUN completed successfully!")
                print()
                print("Next steps:")
                print("1. Review the output above")
                print("2. Run without --dry-run to execute real sync:")
                print("   python bulk_sync_all_notion_sales.py")
            else:
                print("SYNC completed successfully!")
                print()
                print("Verify data in PostgreSQL:")
                print("  SELECT COUNT(*) FROM transactions.orders;")
                print("  SELECT COUNT(*) FROM products.inventory;")
            print("=" * 80)

    except Exception as e:
        logger.error(f"Fatal error during bulk sync: {e}")
        if not args.dry_run and session:
            await session.rollback()
            logger.info("Changes rolled back due to error")
        raise

    finally:
        if not args.dry_run and session:
            await session.__aexit__(None, None, None)
        await service.close()


if __name__ == "__main__":
    asyncio.run(main())

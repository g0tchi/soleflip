"""
Fetch All Notion Sales and Execute Bulk Sync
Uses Notion MCP to fetch all StockX sales and sync to PostgreSQL

This script is designed to be run from Claude Code with Notion MCP access.
It fetches all sales from the Notion Inventory database and populates
the bulk_sync_all_notion_sales.py NOTION_SALES_DATA array.

Usage:
    python fetch_and_sync_notion_sales.py --dry-run
    python fetch_and_sync_notion_sales.py
"""

import asyncio
import argparse
import structlog

from sync_notion_to_postgres import NotionPostgresSyncService

logger = structlog.get_logger(__name__)

# This will be populated by Claude Code with Notion MCP
# Format: List of page objects with 'properties' and 'url' keys
NOTION_SALES_DATA = []


async def main():
    """Main entry point for fetch and sync"""
    parser = argparse.ArgumentParser(description="Fetch and sync all Notion sales")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no DB writes)")
    parser.add_argument("--limit", type=int, help="Limit number of sales to sync")
    args = parser.parse_args()

    print("=" * 80)
    print("NOTION -> POSTGRESQL BULK SYNC")
    print("=" * 80)
    print(f"Mode:          {'DRY RUN' if args.dry_run else 'LIVE SYNC'}")
    if args.limit:
        print(f"Limit:         {args.limit} sales")
    print("=" * 80)
    print()

    if not NOTION_SALES_DATA:
        print()
        print("[ERROR] No Notion sales data available!")
        print()
        print("This script requires NOTION_SALES_DATA to be populated.")
        print("Run from Claude Code with Notion MCP access.")
        print()
        print("Claude Code will:")
        print("1. Fetch all sales from Notion Inventory database")
        print("2. Populate NOTION_SALES_DATA with page data")
        print("3. Execute this script with the data")
        print()
        return

    print(f"Found {len(NOTION_SALES_DATA)} sales in NOTION_SALES_DATA")
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
        skipped = 0

        for i, notion_page in enumerate(NOTION_SALES_DATA, 1):
            if args.limit and processed >= args.limit:
                logger.info(f"Reached limit of {args.limit} sales")
                break

            # Extract page data
            page_url = notion_page.get("url", "")
            properties = notion_page.get("properties", {})

            # Parse Notion properties
            sale_data = service.parse_notion_properties(properties, page_url)

            if not sale_data:
                logger.warning(f"Skipping invalid sale [{i}/{len(NOTION_SALES_DATA)}]")
                service.stats["skipped_invalid"] += 1
                skipped += 1
                continue

            service.stats["total_found"] += 1

            # Filter: Only StockX sales
            if sale_data["sale_platform"] != "StockX":
                logger.debug(f"Skipping non-StockX sale: {sale_data.get('sale_id', 'unknown')}")
                skipped += 1
                continue

            # Check if already synced
            if not args.dry_run:
                if await service.check_if_synced(session, sale_data["sale_id"]):
                    logger.info(f"Skipping already synced: {sale_data['sale_id']}")
                    service.stats["already_synced"] += 1
                    skipped += 1
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

            # Progress update every 25 sales
            if i % 25 == 0:
                print(
                    f"Progress: {i}/{len(NOTION_SALES_DATA)} sales processed ({processed} synced, {skipped} skipped)"
                )

        # Final commit
        if not args.dry_run and session:
            await session.commit()
            logger.info("Final commit completed")

        # Print summary
        print()
        service.print_summary()

        # Show recommendations
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
                print("   python fetch_and_sync_notion_sales.py")
            else:
                print("SYNC completed successfully!")
                print()
                print("Verify data in PostgreSQL:")
                print("  SELECT COUNT(*) FROM transactions.orders;")
                print("  SELECT COUNT(*) FROM products.inventory;")
                print()
                print("Check specific synced sales:")
                print("  SELECT o.stockx_order_number, o.sold_at, o.net_profit, o.roi")
                print("  FROM transactions.orders o")
                print("  ORDER BY o.sold_at DESC LIMIT 10;")
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

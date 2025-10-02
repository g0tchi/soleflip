"""
Test Single Notion Sale Sync
Tests the complete sync pipeline with one real Notion sale

Usage:
    python test_notion_sync_single.py
"""
import asyncio
from sync_notion_to_postgres import NotionPostgresSyncService
import structlog

logger = structlog.get_logger(__name__)


# Example Notion sale data (from FZ4159-100)
TEST_SALE_PROPERTIES = {
    'SKU': 'FZ4159-100',
    'Brand': 'Jordan',
    'Size': '8',
    'Type': 'US',
    'Supplier': 'BSTN',
    'Gross Buy': 115.99,
    'VAT?': True,
    'date:Buy Date:start': '2024-07-24',
    'date:Delivery Date:start': '2024-07-23',
    'Order No.': '13001671992',
    'Invoice Nr.': 'VR131674973',
    'Email': '',
    'Sale Platform': 'StockX',
    'Sale ID': ' 68237673-68137432',
    'date:Sale Date:start': '2024-10-04',
    'Gross Sale': 88.48,
    'Net Sale': 88.48,
    'Payout Received?': True,
    'Status': 'Sale completed',
    'Profit': -8.99,
    'ROI': -8.0,
    'Shelf Life': 73,
}

TEST_PAGE_URL = 'https://www.notion.so/2a64f394153647e399003a8e2fbdaa09'


async def main():
    """Test sync with single sale"""
    print("=" * 80)
    print("TESTING SINGLE NOTION SALE SYNC")
    print("=" * 80)
    print(f"Sale: FZ4159-100 (Sale ID: {TEST_SALE_PROPERTIES['Sale ID'].strip()})")
    print(f"Supplier: {TEST_SALE_PROPERTIES['Supplier']}")
    print(f"Purchase: {TEST_SALE_PROPERTIES['Gross Buy']} EUR")
    print(f"Sale: {TEST_SALE_PROPERTIES['Gross Sale']} EUR")
    print(f"Profit: {TEST_SALE_PROPERTIES['Profit']} EUR")
    print("=" * 80)
    print()

    # Test with dry run first
    print("Step 1: DRY RUN (validation only)")
    print("-" * 80)

    service = NotionPostgresSyncService(dry_run=True)

    try:
        await service.initialize()

        # Parse properties
        sale_data = service.parse_notion_properties(TEST_SALE_PROPERTIES, TEST_PAGE_URL)

        if not sale_data:
            print("[ERROR] Failed to parse Notion properties")
            return

        print("[OK] Successfully parsed Notion data:")
        print(f"   SKU: {sale_data['sku']}")
        print(f"   Brand: {sale_data['brand']}")
        print(f"   Size: {sale_data['size']} {sale_data['size_type']}")
        print(f"   Supplier: {sale_data['supplier']}")
        print(f"   Net Buy: {sale_data['net_buy']} EUR")
        print(f"   Gross Buy: {sale_data['gross_buy']} EUR")
        print(f"   VAT Amount: {sale_data['vat_amount']} EUR")
        print(f"   VAT Rate: {sale_data['vat_rate']}%")
        print(f"   Sale Date: {sale_data['sale_date']}")
        print(f"   Net Sale: {sale_data['net_sale']} EUR")
        print(f"   Profit: {sale_data['profit']} EUR")
        print(f"   ROI: {sale_data['roi']}%")
        print(f"   Shelf Life: {sale_data['shelf_life_days']} days")
        print()

        service.print_summary()

    finally:
        await service.close()

    # Ask for confirmation before real sync
    print()
    response = input("Proceed with REAL database sync? (yes/no): ")

    if response.lower() != 'yes':
        print("Sync cancelled.")
        return

    # Real sync
    print()
    print("Step 2: REAL SYNC")
    print("-" * 80)

    service = NotionPostgresSyncService(dry_run=False)

    try:
        await service.initialize()

        # Parse again
        sale_data = service.parse_notion_properties(TEST_SALE_PROPERTIES, TEST_PAGE_URL)

        async with service.db_manager.get_session() as session:
            # Check if already synced
            if await service.check_if_synced(session, sale_data['sale_id']):
                print(f"[WARN] Sale {sale_data['sale_id']} already exists in database")
                print("   Use a different test sale or delete existing record")
                return

            # Sync to database
            success = await service.sync_sale(session, sale_data)

            if success:
                await session.commit()
                print("[OK] Successfully synced to database!")
            else:
                await session.rollback()
                print("[ERROR] Sync failed - changes rolled back")

        service.print_summary()

    finally:
        await service.close()


if __name__ == '__main__':
    asyncio.run(main())
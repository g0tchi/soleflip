"""
Script to import Nike accounts from accounts.csv
"""

import asyncio
import os

from shared.database.connection import db_manager
from shared.database.models import Supplier
from domains.suppliers.services.account_import_service import AccountImportService
from sqlalchemy import select


async def import_nike_accounts():
    """Import accounts for Nike supplier"""

    # Initialize database
    await db_manager.initialize()

    async with db_manager.get_session() as session:
        # Check if Nike supplier exists
        result = await session.execute(
            select(Supplier).where(Supplier.name.ilike('%nike%'))
        )
        nike_supplier = result.scalar_one_or_none()

        if not nike_supplier:
            print("Creating Nike supplier...")
            # Create Nike supplier
            nike_supplier = Supplier(
                name="Nike",
                slug="nike",
                display_name="Nike Inc.",
                supplier_type="brand",
                business_size="large",
                website="https://www.nike.com",
                country="US"
            )
            session.add(nike_supplier)
            await session.commit()
            await session.refresh(nike_supplier)
            print(f"Created Nike supplier with ID: {nike_supplier.id}")
        else:
            print(f"Found existing Nike supplier: {nike_supplier.name} (ID: {nike_supplier.id})")

        # Create supplier mapping for import
        supplier_mapping = {
            "default": nike_supplier.id,
            "LazyMails 2795": nike_supplier.id,
            "LazyMails 6901": nike_supplier.id,
            "Ungrouped": nike_supplier.id,
            "Local": nike_supplier.id,
            "clipped": nike_supplier.id,
            "n!ke discounts": nike_supplier.id
        }

        # Initialize import service
        import_service = AccountImportService(session)

        # Import accounts from CSV
        csv_path = "C:\\nth_dev\\soleflip\\src\\data\\accounts.csv"
        if not os.path.exists(csv_path):
            print(f"CSV file not found: {csv_path}")
            return

        print(f"Starting import from {csv_path}...")
        result = await import_service.import_accounts_from_csv(
            csv_file_path=csv_path,
            supplier_mapping=supplier_mapping,
            batch_size=10  # Smaller batch size for safety
        )

        print("\n=== IMPORT RESULTS ===")
        print(f"Total rows processed: {result['total_rows']}")
        print(f"Successful imports: {result['successful_imports']}")
        print(f"Failed imports: {result['failed_imports']}")
        print(f"Skipped rows: {result['skipped_rows']}")
        print(f"Duplicate accounts: {result['duplicate_accounts']}")

        if result['errors']:
            print("\n=== ERRORS ===")
            for error in result['errors'][:5]:  # Show first 5 errors
                print(f"Row {error.get('row', 'N/A')}: {error.get('error', 'Unknown error')}")

            if len(result['errors']) > 5:
                print(f"... and {len(result['errors']) - 5} more errors")

        # Get final statistics
        summary = await import_service.get_import_summary(nike_supplier.id)
        print("\n=== NIKE SUPPLIER SUMMARY ===")
        print(f"Total accounts: {summary['total_accounts']}")
        print(f"Active accounts: {summary['active_accounts']}")
        print(f"Total purchases: {summary['total_purchases']}")
        print(f"Total revenue: ${summary['total_revenue']:.2f}")
        print(f"Average success rate: {summary['average_success_rate']:.2f}%")


if __name__ == "__main__":
    asyncio.run(import_nike_accounts())
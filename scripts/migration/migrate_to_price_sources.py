"""
Data Migration Script: Legacy Tables → price_sources Architecture
Migrates existing Awin and StockX data to the new unified price_sources table

Usage:
    python scripts/migration/migrate_to_price_sources.py [--dry-run] [--batch-size 1000]

Options:
    --dry-run: Preview changes without committing
    --batch-size: Number of records per batch (default: 1000)
"""

import argparse
import asyncio
from typing import Any, Dict

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.connection import get_db_session

logger = structlog.get_logger(__name__)


class PriceSourcesMigration:
    """Migrates legacy Awin and StockX data to unified price_sources architecture"""

    def __init__(self, session: AsyncSession, dry_run: bool = False, batch_size: int = 1000):
        self.session = session
        self.dry_run = dry_run
        self.batch_size = batch_size
        self.stats = {
            "awin_retail_migrated": 0,
            "stockx_resale_migrated": 0,
            "suppliers_linked": 0,
            "products_matched": 0,
            "errors": 0,
        }

    async def run_full_migration(self) -> Dict[str, Any]:
        """Execute complete migration in correct order"""
        logger.info("Starting price_sources migration", dry_run=self.dry_run)

        try:
            # Step 1: Migrate Awin retail prices
            await self._migrate_awin_retail_prices()

            # Step 2: Migrate StockX resale prices (from enriched Awin data)
            await self._migrate_stockx_resale_prices()

            # Step 3: Link Awin merchants to suppliers
            await self._link_awin_merchants_to_suppliers()

            if not self.dry_run:
                await self.session.commit()
                logger.info("Migration completed successfully", stats=self.stats)
            else:
                await self.session.rollback()
                logger.info("DRY RUN completed - no changes committed", stats=self.stats)

            return self.stats

        except Exception as e:
            await self.session.rollback()
            logger.error("Migration failed", error=str(e), exc_info=True)
            raise

    async def _migrate_awin_retail_prices(self):
        """Migrate Awin products → price_sources (retail prices)"""
        logger.info("Migrating Awin retail prices...")

        # Get all Awin products with EAN (to match with products.products)
        query = text(
            """
            SELECT
                ap.id as awin_id,
                ap.awin_product_id,
                ap.product_name,
                ap.ean,
                ap.retail_price_cents,
                ap.in_stock,
                ap.stock_quantity,
                ap.affiliate_link,
                ap.merchant_id,
                ap.merchant_name,
                ap.created_at,
                ap.updated_at,
                p.id as product_id
            FROM integration.awin_products ap
            LEFT JOIN products.products p ON ap.ean = p.ean
            WHERE ap.ean IS NOT NULL AND ap.ean != ''
            ORDER BY ap.created_at
        """
        )

        result = await self.session.execute(query)
        awin_products = result.fetchall()

        logger.info(f"Found {len(awin_products)} Awin products to migrate")

        # Process in batches
        for i in range(0, len(awin_products), self.batch_size):
            batch = awin_products[i : i + self.batch_size]

            for ap in batch:
                try:
                    # Skip if no product match found
                    if not ap.product_id:
                        logger.warning(
                            "No product match for Awin product",
                            ean=ap.ean,
                            awin_id=ap.awin_product_id,
                        )
                        self.stats["errors"] += 1
                        continue

                    # Insert into price_sources
                    insert_query = text(
                        """
                        INSERT INTO integration.price_sources
                            (product_id, source_type, source_product_id, source_name,
                             price_type, price_cents, currency, in_stock, stock_quantity,
                             affiliate_link, metadata, last_updated, created_at, updated_at)
                        VALUES
                            (:product_id, 'awin', :source_product_id, :source_name,
                             'retail', :price_cents, 'EUR', :in_stock, :stock_quantity,
                             :affiliate_link, :metadata::jsonb, :last_updated, :created_at, :updated_at)
                        ON CONFLICT (product_id, source_type, source_product_id) DO UPDATE SET
                            price_cents = EXCLUDED.price_cents,
                            in_stock = EXCLUDED.in_stock,
                            stock_quantity = EXCLUDED.stock_quantity,
                            affiliate_link = EXCLUDED.affiliate_link,
                            last_updated = EXCLUDED.last_updated,
                            updated_at = EXCLUDED.updated_at
                    """
                    )

                    metadata = {
                        "merchant_id": ap.merchant_id,
                        "merchant_name": ap.merchant_name,
                        "awin_internal_id": str(ap.awin_id),
                    }

                    await self.session.execute(
                        insert_query,
                        {
                            "product_id": str(ap.product_id),
                            "source_product_id": ap.awin_product_id,
                            "source_name": ap.merchant_name,
                            "price_cents": ap.retail_price_cents,
                            "in_stock": ap.in_stock,
                            "stock_quantity": ap.stock_quantity,
                            "affiliate_link": ap.affiliate_link,
                            "metadata": str(metadata).replace("'", '"'),
                            "last_updated": ap.updated_at or ap.created_at,
                            "created_at": ap.created_at,
                            "updated_at": ap.updated_at,
                        },
                    )

                    self.stats["awin_retail_migrated"] += 1

                except Exception as e:
                    logger.error(
                        "Failed to migrate Awin product",
                        awin_id=ap.awin_product_id,
                        error=str(e),
                    )
                    self.stats["errors"] += 1

            # Commit batch
            if not self.dry_run and i % (self.batch_size * 5) == 0:
                await self.session.commit()
                logger.info(f"Processed {i + len(batch)} / {len(awin_products)} Awin products")

        logger.info(f"Awin retail prices migrated: {self.stats['awin_retail_migrated']}")

    async def _migrate_stockx_resale_prices(self):
        """Migrate StockX prices from enriched Awin data → price_sources (resale prices)"""
        logger.info("Migrating StockX resale prices...")

        # Get all Awin products that were matched with StockX
        query = text(
            """
            SELECT
                ap.stockx_product_id,
                ap.stockx_url_key,
                ap.stockx_style_id,
                ap.stockx_lowest_ask_cents,
                ap.last_enriched_at,
                p.id as product_id,
                p.name as product_name
            FROM integration.awin_products ap
            JOIN products.products p ON ap.ean = p.ean
            WHERE ap.stockx_product_id IS NOT NULL
              AND ap.enrichment_status = 'matched'
              AND ap.stockx_lowest_ask_cents IS NOT NULL
        """
        )

        result = await self.session.execute(query)
        stockx_matches = result.fetchall()

        logger.info(f"Found {len(stockx_matches)} StockX matches to migrate")

        for match in stockx_matches:
            try:
                insert_query = text(
                    """
                    INSERT INTO integration.price_sources
                        (product_id, source_type, source_product_id, source_name,
                         price_type, price_cents, currency, in_stock,
                         source_url, metadata, last_updated, created_at, updated_at)
                    VALUES
                        (:product_id, 'stockx', :source_product_id, 'StockX',
                         'resale', :price_cents, 'EUR', true,
                         :source_url, :metadata::jsonb, :last_updated, NOW(), NOW())
                    ON CONFLICT (product_id, source_type, source_product_id) DO UPDATE SET
                        price_cents = EXCLUDED.price_cents,
                        last_updated = EXCLUDED.last_updated,
                        updated_at = EXCLUDED.updated_at
                """
                )

                metadata = {
                    "url_key": match.stockx_url_key,
                    "style_id": match.stockx_style_id,
                    "price_type": "lowest_ask",
                }

                source_url = (
                    f"https://stockx.com/{match.stockx_url_key}" if match.stockx_url_key else None
                )

                await self.session.execute(
                    insert_query,
                    {
                        "product_id": str(match.product_id),
                        "source_product_id": str(match.stockx_product_id),
                        "price_cents": match.stockx_lowest_ask_cents,
                        "source_url": source_url,
                        "metadata": str(metadata).replace("'", '"'),
                        "last_updated": match.last_enriched_at,
                    },
                )

                self.stats["stockx_resale_migrated"] += 1

            except Exception as e:
                logger.error(
                    "Failed to migrate StockX price",
                    stockx_id=match.stockx_product_id,
                    error=str(e),
                )
                self.stats["errors"] += 1

        logger.info(f"StockX resale prices migrated: {self.stats['stockx_resale_migrated']}")

    async def _link_awin_merchants_to_suppliers(self):
        """Link Awin merchants to existing suppliers and update price_sources"""
        logger.info("Linking Awin merchants to suppliers...")

        # Find Awin merchants that match existing suppliers by name
        query = text(
            """
            SELECT DISTINCT
                ap.merchant_id,
                ap.merchant_name,
                s.id as supplier_id,
                s.name as supplier_name
            FROM integration.awin_products ap
            LEFT JOIN core.suppliers s ON LOWER(ap.merchant_name) = LOWER(s.name)
            WHERE ap.merchant_id IS NOT NULL
        """
        )

        result = await self.session.execute(query)
        merchant_supplier_links = result.fetchall()

        for link in merchant_supplier_links:
            if link.supplier_id:
                # Update price_sources to link to supplier
                update_query = text(
                    """
                    UPDATE integration.price_sources
                    SET supplier_id = :supplier_id
                    WHERE source_type = 'awin'
                      AND metadata->>'merchant_id' = :merchant_id
                """
                )

                await self.session.execute(
                    update_query,
                    {
                        "supplier_id": str(link.supplier_id),
                        "merchant_id": link.merchant_id,
                    },
                )

                self.stats["suppliers_linked"] += 1
                logger.debug(
                    "Linked Awin merchant to supplier",
                    merchant=link.merchant_name,
                    supplier=link.supplier_name,
                )
            else:
                logger.warning(
                    "No supplier match for Awin merchant",
                    merchant_id=link.merchant_id,
                    merchant_name=link.merchant_name,
                )

        logger.info(f"Suppliers linked: {self.stats['suppliers_linked']}")

    async def verify_migration(self) -> Dict[str, Any]:
        """Verify migration integrity"""
        verification = {}

        # Count records in old vs new tables
        old_awin_count = await self.session.execute(
            text("SELECT COUNT(*) FROM integration.awin_products WHERE ean IS NOT NULL")
        )
        verification["old_awin_count"] = old_awin_count.scalar()

        new_retail_count = await self.session.execute(
            text(
                "SELECT COUNT(*) FROM integration.price_sources WHERE source_type = 'awin' AND price_type = 'retail'"
            )
        )
        verification["new_retail_count"] = new_retail_count.scalar()

        new_resale_count = await self.session.execute(
            text(
                "SELECT COUNT(*) FROM integration.price_sources WHERE source_type = 'stockx' AND price_type = 'resale'"
            )
        )
        verification["new_resale_count"] = new_resale_count.scalar()

        # Check profit opportunities view
        profit_opps = await self.session.execute(
            text("SELECT COUNT(*) FROM integration.profit_opportunities_v2")
        )
        verification["profit_opportunities"] = profit_opps.scalar()

        return verification


async def main():
    parser = argparse.ArgumentParser(
        description="Migrate legacy data to price_sources architecture"
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without committing")
    parser.add_argument("--batch-size", type=int, default=1000, help="Number of records per batch")
    args = parser.parse_args()

    async with get_db_session() as session:
        migration = PriceSourcesMigration(session, dry_run=args.dry_run, batch_size=args.batch_size)

        # Run migration
        stats = await migration.run_full_migration()

        # Verify results
        if not args.dry_run:
            verification = await migration.verify_migration()
            logger.info("Migration verification", **verification)

        print("\n" + "=" * 60)
        print("MIGRATION RESULTS")
        print("=" * 60)
        print(f"Awin Retail Prices Migrated:  {stats['awin_retail_migrated']}")
        print(f"StockX Resale Prices Migrated: {stats['stockx_resale_migrated']}")
        print(f"Suppliers Linked:              {stats['suppliers_linked']}")
        print(f"Errors:                        {stats['errors']}")
        print("=" * 60)

        if args.dry_run:
            print("\n⚠️  DRY RUN MODE - No changes were committed")
        else:
            print("\n✅ Migration completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())

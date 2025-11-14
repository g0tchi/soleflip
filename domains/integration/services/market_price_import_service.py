"""
Market Price Import Service
Imports external product data from various sources (AWIN, Webgains, etc.) for QuickFlip detection
"""

import csv
import re
from decimal import Decimal
from typing import Dict, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import Brand, Category, Product, SourcePrice
from shared.repositories.base_repository import BaseRepository

logger = structlog.get_logger(__name__)


class MarketPriceImportService:
    """Service for importing market price data from various sources into market_prices table"""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.product_repo = BaseRepository(Product, db_session)
        self.brand_repo = BaseRepository(Brand, db_session)
        self.category_repo = BaseRepository(Category, db_session)
        self.source_price_repo = BaseRepository(SourcePrice, db_session)
        self.logger = logger.bind(service="market_price_import")

    async def import_csv_file(self, file_path: str, source: str = "awin") -> Dict[str, int]:
        """
        Import CSV file from various sources (AWIN, Webgains, etc.) and create market prices
        Returns statistics about the import
        """
        stats = {"processed": 0, "created": 0, "updated": 0, "errors": 0, "skipped": 0}

        self.logger.info("Starting market price CSV import", file_path=file_path, source=source)

        try:
            with open(file_path, "r", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)

                for row_num, row in enumerate(reader, start=2):  # Start at 2 for header
                    stats["processed"] += 1

                    try:
                        await self._process_row(row, stats, source)

                        # Commit every 100 rows for better performance
                        if stats["processed"] % 100 == 0:
                            await self.db_session.commit()
                            self.logger.info(
                                "Import progress",
                                source=source,
                                processed=stats["processed"],
                                created=stats["created"],
                                errors=stats["errors"],
                            )

                    except Exception as e:
                        stats["errors"] += 1
                        self.logger.error(
                            "Error processing row",
                            source=source,
                            row_number=row_num,
                            error=str(e),
                            row_data=row,
                        )

            # Final commit
            await self.db_session.commit()

            self.logger.info("Market price import completed", source=source, **stats)
            return stats

        except Exception as e:
            await self.db_session.rollback()
            self.logger.error("Market price import failed", source=source, error=str(e))
            raise

    async def _process_row(self, row: Dict[str, str], stats: Dict[str, int], source: str) -> None:
        """Process a single CSV row"""
        # Skip rows without essential data
        if not row.get("id") or not row.get("title") or not row.get("price"):
            stats["skipped"] += 1
            return

        # Extract and clean data
        awin_id = row["id"].strip()
        title = row["title"].strip()
        brand_name = row.get("brand", "").strip()
        price_str = row.get("price", "").strip()
        program_name = row.get("program_name", "").strip()

        # Parse price
        try:
            # Remove currency symbols and convert to decimal
            price_clean = re.sub(r"[^\d.,]", "", price_str)
            price_clean = price_clean.replace(",", ".")
            buy_price = Decimal(price_clean)
        except (ValueError, TypeError):
            self.logger.warning("Invalid price format", price=price_str, awin_id=awin_id)
            stats["skipped"] += 1
            return

        # Find or create product
        product = await self._find_or_create_product(
            awin_id=awin_id, title=title, brand_name=brand_name, row=row
        )

        if not product:
            stats["skipped"] += 1
            return

        # Check if market price already exists
        existing_price = await self.source_price_repo.find_one(
            product_id=product.id, source=source, external_id=awin_id
        )

        if existing_price:
            # Update existing price
            await self.source_price_repo.update(
                existing_price.id,
                buy_price=buy_price,
                supplier_name=program_name,
                availability=row.get("availability", ""),
                stock_qty=self._parse_int(row.get("stock_qty")),
                product_url=row.get("link", ""),
                raw_data=row,
            )
            stats["updated"] += 1
        else:
            # Create new market price
            await self.source_price_repo.create(
                product_id=product.id,
                source=source,
                supplier_name=program_name,
                external_id=awin_id,
                buy_price=buy_price,
                currency="EUR",  # Default, can be enhanced
                availability=row.get("availability", ""),
                stock_qty=self._parse_int(row.get("stock_qty")),
                product_url=row.get("link", ""),
                raw_data=row,
            )
            stats["created"] += 1

    async def _find_or_create_product(
        self, awin_id: str, title: str, brand_name: str, row: Dict[str, str]
    ) -> Optional[Product]:
        """Find existing product or create new one"""

        # Try to find by GTIN first
        gtin = row.get("gtin", "").strip()
        if gtin:
            # Store GTIN in raw_data for now (could be added as product field later)
            product = await self._find_product_by_gtin(gtin)
            if product:
                return product

        # Try to find by SKU (using AWIN ID)
        product = await self.product_repo.find_one(sku=awin_id)
        if product:
            return product

        # Try to find by name similarity
        product = await self._find_product_by_name_similarity(title, brand_name)
        if product:
            return product

        # Create new product
        try:
            brand = await self._find_or_create_brand(brand_name) if brand_name else None
            category = await self._find_or_create_category("Sneakers")  # Default category

            product = await self.product_repo.create(
                sku=awin_id,
                name=title,
                description=row.get("description", ""),
                brand_id=brand.id if brand else None,
                category_id=category.id,
                retail_price=self._parse_decimal(row.get("price")),
                # Store additional AWIN data in a structured way
                # Could be moved to separate fields later
            )

            self.logger.info(
                "Created new product from AWIN data",
                product_id=str(product.id),
                sku=awin_id,
                title=title,
            )

            return product

        except Exception as e:
            self.logger.error(
                "Failed to create product", awin_id=awin_id, title=title, error=str(e)
            )
            return None

    async def _find_product_by_gtin(self, gtin: str) -> Optional[Product]:
        """Find product by GTIN (stored in raw_data for now)"""
        # This would require a more sophisticated search
        # For now, we'll implement a simple approach
        return None

    async def _find_product_by_name_similarity(
        self, title: str, brand_name: str
    ) -> Optional[Product]:
        """Find product by name similarity"""
        # Simple approach: exact name match with same brand
        if brand_name:
            brand = await self.brand_repo.find_one(name=brand_name)
            if brand:
                product = await self.product_repo.find_one(name=title, brand_id=brand.id)
                return product

        return None

    async def _find_or_create_brand(self, brand_name: str) -> Optional[Brand]:
        """Find existing brand or create new one"""
        if not brand_name:
            return None

        # Try to find existing
        brand = await self.brand_repo.find_one(name=brand_name)
        if brand:
            return brand

        # Create new brand
        try:
            slug = brand_name.lower().replace(" ", "-").replace("&", "and")
            slug = re.sub(r"[^a-z0-9\-]", "", slug)

            brand = await self.brand_repo.create(name=brand_name, slug=slug)

            self.logger.info("Created new brand", brand_name=brand_name)
            return brand

        except Exception as e:
            self.logger.error("Failed to create brand", brand_name=brand_name, error=str(e))
            return None

    async def _find_or_create_category(self, category_name: str) -> Category:
        """Find existing category or create new one"""
        category = await self.category_repo.find_one(name=category_name)
        if category:
            return category

        # Create new category
        slug = category_name.lower().replace(" ", "-")
        category = await self.category_repo.create(name=category_name, slug=slug)

        return category

    def _parse_decimal(self, value: str) -> Optional[Decimal]:
        """Parse decimal value from string"""
        if not value:
            return None

        try:
            clean_value = re.sub(r"[^\d.,]", "", value.strip())
            clean_value = clean_value.replace(",", ".")
            return Decimal(clean_value)
        except (ValueError, TypeError):
            return None

    def _parse_int(self, value: str) -> Optional[int]:
        """Parse integer value from string"""
        if not value:
            return None

        try:
            return int(value.strip())
        except (ValueError, TypeError):
            return None

    async def get_import_stats(self, source: Optional[str] = None) -> Dict[str, int]:
        """Get statistics about imported market price data"""
        if source:
            total_prices = await self.source_price_repo.count({"source": source})
            return {
                f"total_{source}_prices": total_prices,
            }
        else:
            # Get stats for all sources
            stats = {}
            # This would require a more sophisticated query to get counts by source
            total_prices = await self.source_price_repo.count()
            stats["total_market_prices"] = total_prices
            return stats

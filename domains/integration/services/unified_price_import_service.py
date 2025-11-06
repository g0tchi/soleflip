"""
Unified Price Import Service
Imports prices from any source (Awin, StockX, eBay, etc.) into price_sources table

This service replaces source-specific imports with a unified approach
"""

import json
from typing import Dict, List, Optional, Any
from uuid import UUID

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class UnifiedPriceImportService:
    """
    Universal service for importing prices from any source

    Supports: Awin, StockX, eBay, GOAT, Klekt, and future sources
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def import_retail_price(
        self,
        product_ean: str,
        source_type: str,  # 'awin', 'ebay', etc.
        source_product_id: str,
        source_name: str,
        price_cents: int,
        currency: str = "EUR",
        in_stock: bool = True,
        stock_quantity: Optional[int] = None,
        affiliate_link: Optional[str] = None,
        source_url: Optional[str] = None,
        supplier_name: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """
        Import a retail price (from Awin, eBay, etc.)

        Args:
            product_ean: EAN/GTIN code to match product
            source_type: 'awin', 'ebay', 'goat', etc.
            source_product_id: External ID from source system
            source_name: Human-readable source name (e.g., "size?Official DE")
            price_cents: Price in cents
            currency: Currency code (default: EUR)
            in_stock: Stock availability
            stock_quantity: Available quantity
            affiliate_link: Affiliate/tracking link
            source_url: Direct product URL
            supplier_name: Supplier name (will link to suppliers table)
            metadata: Additional source-specific data

        Returns:
            True if successful, False if product not found
        """
        try:
            # Find or create product by EAN
            product_id = await self._get_or_create_product(product_ean, metadata)

            if not product_id:
                logger.warning("Could not find/create product", ean=product_ean)
                return False

            # Find supplier if provided
            supplier_id = None
            if supplier_name:
                supplier_id = await self._get_supplier_id(supplier_name)

            # Insert/update price source
            await self._upsert_price_source(
                product_id=product_id,
                source_type=source_type,
                source_product_id=source_product_id,
                source_name=source_name,
                price_type="retail",
                price_cents=price_cents,
                currency=currency,
                in_stock=in_stock,
                stock_quantity=stock_quantity,
                affiliate_link=affiliate_link,
                source_url=source_url,
                supplier_id=supplier_id,
                metadata=metadata,
            )

            logger.debug(
                "Imported retail price",
                ean=product_ean,
                source=source_type,
                price_eur=price_cents / 100.0,
            )
            return True

        except Exception as e:
            logger.error("Failed to import retail price", ean=product_ean, error=str(e))
            raise

    async def import_resale_price(
        self,
        product_ean: str,
        source_type: str,  # 'stockx', 'goat', 'klekt', etc.
        source_product_id: str,
        price_cents: int,
        currency: str = "EUR",
        source_url: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """
        Import a resale price (from StockX, GOAT, etc.)

        Args:
            product_ean: EAN/GTIN code to match product
            source_type: 'stockx', 'goat', 'klekt', etc.
            source_product_id: External ID from source system
            price_cents: Resale price in cents
            currency: Currency code
            source_url: Direct product URL
            metadata: Additional source-specific data (e.g., variant info)

        Returns:
            True if successful, False if product not found
        """
        try:
            # Find product by EAN
            product_id = await self._get_product_id_by_ean(product_ean)

            if not product_id:
                logger.warning("Product not found for resale price", ean=product_ean)
                return False

            # Insert/update resale price
            await self._upsert_price_source(
                product_id=product_id,
                source_type=source_type,
                source_product_id=source_product_id,
                source_name=source_type.upper(),  # "STOCKX", "GOAT"
                price_type="resale",
                price_cents=price_cents,
                currency=currency,
                in_stock=True,  # Resale prices are typically available
                source_url=source_url,
                metadata=metadata,
            )

            logger.debug(
                "Imported resale price",
                ean=product_ean,
                source=source_type,
                price_eur=price_cents / 100.0,
            )
            return True

        except Exception as e:
            logger.error("Failed to import resale price", ean=product_ean, error=str(e))
            raise

    async def import_awin_product(self, awin_product: Dict) -> bool:
        """
        Import Awin product using unified architecture

        Args:
            awin_product: Product dict from AwinFeedImportService.parse_feed()

        Returns:
            True if imported successfully
        """
        ean = awin_product.get("ean")
        if not ean:
            logger.warning(
                "Skipping Awin product without EAN",
                awin_id=awin_product.get("awin_product_id"),
            )
            return False

        metadata = {
            "merchant_id": awin_product.get("merchant_id"),
            "data_feed_id": awin_product.get("data_feed_id"),
            "brand_name": awin_product.get("brand_name"),
            "color": awin_product.get("colour"),
            "size": awin_product.get("size"),
            "material": awin_product.get("material"),
            "description": awin_product.get("description"),
            "alternate_images": awin_product.get("alternate_images"),
        }

        return await self.import_retail_price(
            product_ean=ean,
            source_type="awin",
            source_product_id=awin_product["awin_product_id"],
            source_name=awin_product.get("merchant_name", "Awin"),
            price_cents=awin_product.get("retail_price_cents", 0),
            currency=awin_product.get("currency", "EUR"),
            in_stock=awin_product.get("in_stock", False),
            stock_quantity=awin_product.get("stock_quantity"),
            affiliate_link=awin_product.get("affiliate_link"),
            source_url=awin_product.get("merchant_link"),
            supplier_name=awin_product.get("merchant_name"),
            metadata=metadata,
        )

    async def import_stockx_price(
        self, product_ean: str, stockx_product_id: str, lowest_ask_cents: int, stockx_data: Dict
    ) -> bool:
        """
        Import StockX resale price

        Args:
            product_ean: EAN code
            stockx_product_id: StockX UUID
            lowest_ask_cents: Current lowest ask price
            stockx_data: Additional StockX data

        Returns:
            True if imported successfully
        """
        metadata = {
            "url_key": stockx_data.get("urlKey"),
            "style_id": stockx_data.get("styleId"),
            "product_category": stockx_data.get("productCategory"),
            "price_type": "lowest_ask",
        }

        source_url = (
            f"https://stockx.com/{stockx_data.get('urlKey')}" if stockx_data.get("urlKey") else None
        )

        return await self.import_resale_price(
            product_ean=product_ean,
            source_type="stockx",
            source_product_id=stockx_product_id,
            price_cents=lowest_ask_cents,
            source_url=source_url,
            metadata=metadata,
        )

    # =============================================================================
    # INTERNAL HELPER METHODS
    # =============================================================================

    async def _get_product_id_by_ean(self, ean: str) -> Optional[UUID]:
        """Get product ID by EAN"""
        result = await self.session.execute(
            text("SELECT id FROM catalog.product WHERE ean = :ean"), {"ean": ean}
        )
        row = result.fetchone()
        return row[0] if row else None

    async def _get_or_create_product(self, ean: str, metadata: Optional[Dict]) -> Optional[UUID]:
        """Get existing product or create minimal product record"""

        # Try to find existing
        product_id = await self._get_product_id_by_ean(ean)
        if product_id:
            return product_id

        # Create minimal product record
        # Note: Brand should be created separately or resolved from metadata
        product_name = (
            metadata.get("product_name", f"Product {ean}") if metadata else f"Product {ean}"
        )
        brand_name = metadata.get("brand_name", "Unknown") if metadata else "Unknown"

        result = await self.session.execute(
            text(
                """
                INSERT INTO catalog.product (
                    name, ean, sku,
                    brand_id, color, size,
                    description, image_url,
                    created_at, updated_at
                )
                VALUES (
                    :name, :ean, :ean,
                    (SELECT id FROM catalog.brand WHERE LOWER(name) = LOWER(:brand_name) LIMIT 1),
                    :color, :size,
                    :description, :image_url,
                    NOW(), NOW()
                )
                RETURNING id
            """
            ),
            {
                "name": product_name,
                "ean": ean,
                "brand_name": brand_name,
                "color": metadata.get("color") if metadata else None,
                "size": metadata.get("size") if metadata else None,
                "description": metadata.get("description") if metadata else None,
                "image_url": metadata.get("image_url") if metadata else None,
            },
        )

        row = result.fetchone()
        await self.session.commit()

        logger.info("Created new product", ean=ean, product_id=str(row[0]))
        return row[0] if row else None

    async def _get_supplier_id(self, supplier_name: str) -> Optional[UUID]:
        """Get supplier ID by name"""
        result = await self.session.execute(
            text("SELECT id FROM core.suppliers WHERE LOWER(name) = LOWER(:name)"),
            {"name": supplier_name},
        )
        row = result.fetchone()
        return row[0] if row else None

    async def _upsert_price_source(
        self,
        product_id: UUID,
        source_type: str,
        source_product_id: str,
        source_name: str,
        price_type: str,
        price_cents: int,
        currency: str = "EUR",
        in_stock: bool = True,
        stock_quantity: Optional[int] = None,
        affiliate_link: Optional[str] = None,
        source_url: Optional[str] = None,
        supplier_id: Optional[UUID] = None,
        metadata: Optional[Dict] = None,
    ):
        """Insert or update price source"""

        metadata_json = json.dumps(metadata) if metadata else None

        await self.session.execute(
            text(
                """
                INSERT INTO integration.price_sources (
                    product_id, source_type, source_product_id, source_name,
                    price_type, price_cents, currency,
                    in_stock, stock_quantity,
                    affiliate_link, source_url,
                    supplier_id, metadata,
                    last_updated, created_at, updated_at
                )
                VALUES (
                    :product_id, :source_type, :source_product_id, :source_name,
                    :price_type, :price_cents, :currency,
                    :in_stock, :stock_quantity,
                    :affiliate_link, :source_url,
                    :supplier_id, CAST(:metadata AS jsonb),
                    NOW(), NOW(), NOW()
                )
                ON CONFLICT (product_id, source_type, source_product_id)
                DO UPDATE SET
                    price_cents = EXCLUDED.price_cents,
                    in_stock = EXCLUDED.in_stock,
                    stock_quantity = EXCLUDED.stock_quantity,
                    affiliate_link = EXCLUDED.affiliate_link,
                    source_url = EXCLUDED.source_url,
                    last_updated = NOW(),
                    updated_at = NOW()
            """
            ),
            {
                "product_id": str(product_id),
                "source_type": source_type,
                "source_product_id": source_product_id,
                "source_name": source_name,
                "price_type": price_type,
                "price_cents": price_cents,
                "currency": currency,
                "in_stock": in_stock,
                "stock_quantity": stock_quantity,
                "affiliate_link": affiliate_link,
                "source_url": source_url,
                "supplier_id": str(supplier_id) if supplier_id else None,
                "metadata": metadata_json,
            },
        )

        await self.session.commit()

    async def get_price_source_stats(self) -> Dict[str, Any]:
        """Get statistics about imported price sources"""
        result = await self.session.execute(
            text(
                """
                SELECT
                    source_type,
                    price_type,
                    COUNT(*) as count,
                    COUNT(DISTINCT product_id) as unique_products,
                    AVG(price_cents) / 100.0 as avg_price_eur,
                    MIN(price_cents) / 100.0 as min_price_eur,
                    MAX(price_cents) / 100.0 as max_price_eur,
                    COUNT(CASE WHEN in_stock = true THEN 1 END) as in_stock_count
                FROM integration.price_sources
                GROUP BY source_type, price_type
                ORDER BY source_type, price_type
            """
            )
        )

        stats = []
        for row in result:
            stats.append(
                {
                    "source_type": row[0],
                    "price_type": row[1],
                    "total_prices": row[2],
                    "unique_products": row[3],
                    "avg_price_eur": float(row[4]) if row[4] else 0.0,
                    "min_price_eur": float(row[5]) if row[5] else 0.0,
                    "max_price_eur": float(row[6]) if row[6] else 0.0,
                    "in_stock_count": row[7],
                }
            )

        return {"price_sources": stats}

    async def get_profit_opportunities(
        self, min_profit_eur: float = 20.0, min_profit_percentage: float = 10.0, limit: int = 50
    ) -> List[Dict]:
        """
        Get profit opportunities using the unified view

        Args:
            min_profit_eur: Minimum profit in EUR
            min_profit_percentage: Minimum ROI percentage
            limit: Max results

        Returns:
            List of profit opportunities
        """
        result = await self.session.execute(
            text(
                """
                SELECT
                    product_name,
                    product_sku,
                    product_ean,
                    brand_name,
                    retail_source,
                    retail_source_name,
                    retail_price_eur,
                    retail_affiliate_link,
                    resale_source,
                    resale_price_eur,
                    profit_eur,
                    profit_percentage
                FROM integration.profit_opportunities_v2
                WHERE profit_eur >= :min_profit_eur
                  AND profit_percentage >= :min_profit_percentage
                ORDER BY profit_eur DESC
                LIMIT :limit
            """
            ),
            {
                "min_profit_eur": min_profit_eur,
                "min_profit_percentage": min_profit_percentage,
                "limit": limit,
            },
        )

        opportunities = []
        for row in result:
            opportunities.append(
                {
                    "product": {
                        "name": row[0],
                        "sku": row[1],
                        "ean": row[2],
                        "brand": row[3],
                    },
                    "retail": {
                        "source": row[4],
                        "source_name": row[5],
                        "price_eur": float(row[6]) if row[6] else 0.0,
                        "affiliate_link": row[7],
                    },
                    "resale": {"source": row[8], "price_eur": float(row[9]) if row[9] else 0.0},
                    "profit": {
                        "amount_eur": float(row[10]) if row[10] else 0.0,
                        "percentage": float(row[11]) if row[11] else 0.0,
                    },
                }
            )

        return opportunities

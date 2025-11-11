"""
Awin Product Feed Import Service
Handles downloading, parsing, and importing product data from Awin affiliate feeds
"""

import csv
import gzip
import os
from typing import Dict, List, Optional

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.connection import db_manager


class AwinFeedImportService:
    """Service for importing product data from Awin affiliate network"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.api_key = os.getenv("AWIN_API_KEY")
        if not self.api_key:
            raise ValueError("AWIN_API_KEY environment variable is required")
        self.base_url = "https://productdata.awin.com/datafeed/download"

    async def download_feed(
        self,
        merchant_ids: List[int],
        output_path: str = "context/integrations/awin_feed_latest.csv.gz",
        categories: Optional[List[int]] = None,
        feed_ids: Optional[List[int]] = None,
    ) -> str:
        """
        Download latest feed from Awin

        Args:
            merchant_ids: List of Awin merchant IDs (e.g., [10597] for size?Official DE)
            output_path: Where to save the downloaded feed
            categories: Optional category IDs filter
            feed_ids: Optional feed IDs filter

        Returns:
            Path to downloaded file
        """
        # Build URL with all required columns
        columns = [
            "aw_deep_link",
            "product_name",
            "aw_product_id",
            "merchant_product_id",
            "merchant_image_url",
            "description",
            "merchant_category",
            "search_price",
            "merchant_name",
            "merchant_id",
            "category_name",
            "category_id",
            "aw_image_url",
            "currency",
            "store_price",
            "delivery_cost",
            "merchant_deep_link",
            "language",
            "last_updated",
            "display_price",
            "data_feed_id",
            "brand_name",
            "brand_id",
            "colour",
            "product_short_description",
            "specifications",
            "condition",
            "product_model",
            "model_number",
            "dimensions",
            "keywords",
            "promotional_text",
            "product_type",
            "commission_group",
            "merchant_product_category_path",
            "merchant_product_second_category",
            "merchant_product_third_category",
            "rrp_price",
            "saving",
            "savings_percent",
            "base_price",
            "base_price_amount",
            "base_price_text",
            "product_price_old",
            "delivery_restrictions",
            "delivery_weight",
            "warranty",
            "terms_of_contract",
            "delivery_time",
            "in_stock",
            "stock_quantity",
            "valid_from",
            "valid_to",
            "is_for_sale",
            "web_offer",
            "pre_order",
            "stock_status",
            "size_stock_status",
            "size_stock_amount",
            "merchant_thumb_url",
            "large_image",
            "alternate_image",
            "aw_thumb_url",
            "alternate_image_two",
            "alternate_image_three",
            "alternate_image_four",
            "reviews",
            "average_rating",
            "rating",
            "number_available",
            "custom_1",
            "custom_2",
            "custom_3",
            "custom_4",
            "custom_5",
            "custom_6",
            "custom_7",
            "custom_8",
            "custom_9",
            "ean",
            "isbn",
            "upc",
            "mpn",
            "parent_product_id",
            "product_GTIN",
            "basket_link",
            "Fashion:suitable_for",
            "Fashion:category",
            "Fashion:size",
            "Fashion:material",
            "Fashion:pattern",
            "Fashion:swatch",
        ]

        url = (
            f"{self.base_url}/apikey/{self.api_key}"
            f"/language/de"
            f"/bid/{','.join(str(m) for m in merchant_ids)}"
        )

        if categories:
            url += f"/cid/{','.join(str(c) for c in categories)}"

        if feed_ids:
            url += f"/fid/{','.join(str(f) for f in feed_ids)}"

        url += (
            f"/columns/{','.join(columns)}"
            f"/format/csv/delimiter/%2C/compression/gzip/adultcontent/1/"
        )

        print(f"[*] Downloading Awin feed from: {merchant_ids}")
        print(f"    URL: {url[:100]}...")

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.get(url)
            response.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(response.content)

        print(f"[OK] Feed downloaded: {output_path}")
        return output_path

    async def parse_feed(self, csv_file_path: str) -> List[Dict]:
        """
        Parse gzip CSV feed and return product records

        Args:
            csv_file_path: Path to gzip compressed CSV file

        Returns:
            List of product dictionaries
        """
        products = []
        print(f"[*] Parsing feed: {csv_file_path}")

        with gzip.open(csv_file_path, "rt", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for i, row in enumerate(reader, 1):
                try:
                    product = self._transform_row(row)
                    products.append(product)

                    if i % 100 == 0:
                        print(f"    Parsed {i} products...")

                except Exception as e:
                    print(f"[WARN] Error parsing row {i}: {e}")
                    continue

        print(f"[OK] Parsed {len(products)} products")
        return products

    def _transform_row(self, row: Dict) -> Dict:
        """
        Transform CSV row to database model format

        Args:
            row: Raw CSV row dictionary

        Returns:
            Transformed product dictionary
        """

        # Parse price safely
        def parse_price(value: str) -> Optional[int]:
            if not value or value.strip() == "":
                return None
            try:
                return int(float(value) * 100)  # Convert to cents
            except (ValueError, TypeError):
                return None

        # Parse int safely
        def parse_int(value: str) -> Optional[int]:
            if not value or value.strip() == "":
                return None
            try:
                return int(value)
            except (ValueError, TypeError):
                return None

        # Parse bool from '0'/'1'
        def parse_bool(value: str) -> bool:
            return value == "1" if value else False

        # Collect alternate images
        alternate_images = []
        for img_field in [
            "large_image",
            "alternate_image",
            "alternate_image_two",
            "alternate_image_three",
            "alternate_image_four",
        ]:
            if row.get(img_field):
                alternate_images.append(row[img_field])

        return {
            "awin_product_id": row.get("aw_product_id", ""),
            "merchant_product_id": row.get("merchant_product_id"),
            "merchant_id": parse_int(row.get("merchant_id")) or 0,
            "merchant_name": row.get("merchant_name"),
            "data_feed_id": parse_int(row.get("data_feed_id")),
            # Product info
            "product_name": row.get("product_name", ""),
            "brand_name": row.get("brand_name"),
            "brand_id": parse_int(row.get("brand_id")),
            "ean": row.get("ean"),
            "product_gtin": row.get("product_GTIN"),
            "mpn": row.get("mpn"),
            "product_model": row.get("product_model"),
            # Pricing
            "retail_price_cents": parse_price(row.get("search_price")),
            "store_price_cents": parse_price(row.get("store_price")),
            "rrp_price_cents": parse_price(row.get("rrp_price")),
            "currency": row.get("currency", "EUR"),
            # Details
            "description": row.get("description"),
            "short_description": row.get("product_short_description"),
            "colour": row.get("colour"),
            "size": row.get("Fashion:size"),
            "material": row.get("Fashion:material"),
            # Stock
            "in_stock": parse_bool(row.get("in_stock")),
            "stock_quantity": parse_int(row.get("stock_quantity")) or 0,
            "delivery_time": row.get("delivery_time"),
            # Images
            "image_url": row.get("merchant_image_url"),
            "thumbnail_url": row.get("aw_thumb_url"),
            "alternate_images": alternate_images if alternate_images else None,
            # Links
            "affiliate_link": row.get("aw_deep_link"),
            "merchant_link": row.get("merchant_deep_link"),
            # Metadata
            "last_updated": (
                row.get("last_updated")
                if row.get("last_updated") and row.get("last_updated").strip()
                else None
            ),
        }

    async def import_products(self, products: List[Dict]) -> int:
        """
        Bulk import products to database

        Args:
            products: List of product dictionaries

        Returns:
            Number of products imported
        """
        print(f"[*] Importing {len(products)} products to database...")

        imported_count = 0
        for i, product in enumerate(products, 1):
            try:
                await self._upsert_product(product)
                imported_count += 1

                if i % 100 == 0:
                    await self.session.commit()
                    print(f"    Imported {i}/{len(products)} products...")

            except Exception as e:
                print(
                    f"[WARN] Error importing product {product.get('awin_product_id')}: {str(e)[:200]}"
                )
                # Rollback failed transaction
                await self.session.rollback()
                continue

        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()

        print(f"[OK] Imported {imported_count} products")
        return imported_count

    async def _upsert_product(self, product_data: Dict):
        """Insert or update product (ON CONFLICT DO UPDATE)"""

        # Convert alternate_images list to JSON string
        alternate_images_json = None
        if product_data.get("alternate_images"):
            import json

            alternate_images_json = json.dumps(product_data["alternate_images"])

        await self.session.execute(
            text(
                """
                INSERT INTO integration.awin_products (
                    awin_product_id, merchant_product_id, merchant_id,
                    merchant_name, data_feed_id, product_name, brand_name, brand_id,
                    ean, product_gtin, mpn, product_model,
                    retail_price_cents, store_price_cents, rrp_price_cents, currency,
                    description, short_description, colour, size, material,
                    in_stock, stock_quantity, delivery_time,
                    image_url, thumbnail_url, alternate_images,
                    affiliate_link, merchant_link,
                    last_updated, updated_at
                ) VALUES (
                    :awin_product_id, :merchant_product_id, :merchant_id,
                    :merchant_name, :data_feed_id, :product_name, :brand_name, :brand_id,
                    :ean, :product_gtin, :mpn, :product_model,
                    :retail_price_cents, :store_price_cents, :rrp_price_cents, :currency,
                    :description, :short_description, :colour, :size, :material,
                    :in_stock, :stock_quantity, :delivery_time,
                    :image_url, :thumbnail_url, CAST(:alternate_images AS jsonb),
                    :affiliate_link, :merchant_link,
                    :last_updated, NOW()
                )
                ON CONFLICT (awin_product_id)
                DO UPDATE SET
                    retail_price_cents = EXCLUDED.retail_price_cents,
                    store_price_cents = EXCLUDED.store_price_cents,
                    in_stock = EXCLUDED.in_stock,
                    stock_quantity = EXCLUDED.stock_quantity,
                    last_updated = EXCLUDED.last_updated,
                    updated_at = NOW()
            """
            ),
            {**product_data, "alternate_images": alternate_images_json},
        )

    async def match_products_by_ean(self) -> int:
        """
        Match Awin products to core products by EAN

        Returns:
            Number of products matched
        """
        print("[*] Matching products by EAN...")

        try:
            result = await self.session.execute(
                text(
                    """
                    UPDATE integration.awin_products ap
                    SET
                        matched_product_id = p.id,
                        match_confidence = 1.00,
                        match_method = 'ean',
                        updated_at = NOW()
                    FROM core.products p
                    WHERE ap.ean = p.ean
                      AND ap.ean IS NOT NULL
                      AND ap.ean != ''
                      AND ap.matched_product_id IS NULL
                """
                )
            )

            await self.session.commit()
            matched_count = result.rowcount
            print(f"[OK] Matched {matched_count} products by EAN")
            return matched_count
        except Exception as e:
            print(f"[WARN] Product matching skipped (core.products table not found): {e}")
            return 0

    async def get_import_stats(self) -> Dict:
        """Get statistics about imported products"""
        result = await self.session.execute(
            text(
                """
                SELECT
                    COUNT(*) as total_products,
                    COUNT(DISTINCT brand_name) as total_brands,
                    COUNT(DISTINCT merchant_id) as total_merchants,
                    COUNT(CASE WHEN in_stock = true THEN 1 END) as in_stock_count,
                    COUNT(CASE WHEN matched_product_id IS NOT NULL THEN 1 END) as matched_count,
                    AVG(retail_price_cents) / 100.0 as avg_price_eur,
                    MIN(retail_price_cents) / 100.0 as min_price_eur,
                    MAX(retail_price_cents) / 100.0 as max_price_eur
                FROM integration.awin_products
            """
            )
        )

        stats = result.fetchone()

        return {
            "total_products": int(stats[0]) if stats[0] else 0,
            "total_brands": int(stats[1]) if stats[1] else 0,
            "total_merchants": int(stats[2]) if stats[2] else 0,
            "in_stock_count": int(stats[3]) if stats[3] else 0,
            "matched_count": int(stats[4]) if stats[4] else 0,
            "avg_price_eur": float(stats[5]) if stats[5] else 0.0,
            "min_price_eur": float(stats[6]) if stats[6] else 0.0,
            "max_price_eur": float(stats[7]) if stats[7] else 0.0,
        }

    async def find_profit_opportunities(
        self, min_profit_cents: int = 2000, in_stock_only: bool = True, limit: int = 50
    ) -> List[Dict]:
        """
        Find profit opportunities by comparing retail vs resale prices

        Args:
            min_profit_cents: Minimum profit in cents (default 20 EUR)
            in_stock_only: Only show in-stock items
            limit: Max number of results

        Returns:
            List of profit opportunities
        """
        query = """
            SELECT
                ap.product_name,
                ap.brand_name,
                ap.size,
                ap.colour,
                ap.retail_price_cents,
                p.lowest_ask as stockx_price_cents,
                p.style_code,
                p.name as stockx_name,
                (p.lowest_ask - ap.retail_price_cents) as profit_cents,
                ap.in_stock,
                ap.stock_quantity,
                ap.affiliate_link,
                ap.image_url,
                ap.merchant_name
            FROM integration.awin_products ap
            JOIN core.products p ON ap.matched_product_id = p.id
            WHERE (p.lowest_ask - ap.retail_price_cents) >= :min_profit
        """

        if in_stock_only:
            query += " AND ap.in_stock = true"

        query += " ORDER BY profit_cents DESC LIMIT :limit"

        result = await self.session.execute(
            text(query), {"min_profit": min_profit_cents, "limit": limit}
        )

        opportunities = []
        for row in result:
            opportunities.append(
                {
                    "product_name": row[0],
                    "brand_name": row[1],
                    "size": row[2],
                    "colour": row[3],
                    "retail_price_eur": row[4] / 100.0 if row[4] else 0,
                    "stockx_price_eur": row[5] / 100.0 if row[5] else 0,
                    "style_code": row[6],
                    "stockx_name": row[7],
                    "profit_eur": row[8] / 100.0 if row[8] else 0,
                    "in_stock": row[9],
                    "stock_quantity": row[10],
                    "affiliate_link": row[11],
                    "image_url": row[12],
                    "merchant_name": row[13],
                }
            )

        return opportunities


async def sync_awin_feed(merchant_ids: List[int] = [10597]):
    """
    Complete sync workflow: download, parse, import, and match

    Args:
        merchant_ids: List of Awin merchant IDs to sync
    """
    async with db_manager.get_session() as session:
        service = AwinFeedImportService(session)

        # Download feed
        feed_path = await service.download_feed(merchant_ids)

        # Parse feed
        products = await service.parse_feed(feed_path)

        # Import to database
        imported_count = await service.import_products(products)

        # Match products by EAN
        matched_count = await service.match_products_by_ean()

        # Get stats
        stats = await service.get_import_stats()

        print("\n" + "=" * 80)
        print("AWIN FEED SYNC COMPLETE")
        print("=" * 80)
        print(f"Imported: {imported_count} products")
        print(f"Matched: {matched_count} products by EAN")
        print("\nStatistics:")
        print(f"  Total Products: {stats['total_products']}")
        print(f"  Brands: {stats['total_brands']}")
        print(f"  In Stock: {stats['in_stock_count']}")
        print(f"  Matched to StockX: {stats['matched_count']}")
        print(f"  Avg Price: EUR {stats['avg_price_eur']:.2f}")
        print("=" * 80)

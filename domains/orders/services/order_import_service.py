"""
Order Import Service
Handles importing orders from external platforms (StockX, eBay, GOAT) into the database
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import Order, InventoryItem, Product, Size, Platform
from domains.products.services.brand_service import BrandExtractorService
from domains.products.services.category_service import CategoryDetectionService

logger = structlog.get_logger(__name__)


class OrderImportService:
    """Service for importing orders from external platforms into the database"""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        # Initialize shared services for brand/category detection
        self.brand_service = BrandExtractorService(db_session)
        self.category_service = CategoryDetectionService(db_session)
        # Cache for platform IDs
        self._platform_cache: Dict[str, UUID] = {}

    async def import_stockx_orders(
        self, orders_data: List[Dict[str, Any]], batch_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Import StockX orders into the database with upsert logic.

        Args:
            orders_data: List of order dictionaries from StockX API
            batch_id: Optional batch ID for tracking imports

        Returns:
            Dictionary with import statistics
        """
        logger.info(
            "Starting StockX order import",
            order_count=len(orders_data),
            batch_id=batch_id,
        )

        stats = {
            "total_orders": len(orders_data),
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": [],
        }

        for order_data in orders_data:
            try:
                result = await self._import_single_stockx_order(order_data)
                if result == "created":
                    stats["created"] += 1
                elif result == "updated":
                    stats["updated"] += 1
                else:
                    stats["skipped"] += 1

            except Exception as e:
                order_number = order_data.get("orderNumber", "unknown")
                error_msg = f"Failed to import order {order_number}: {str(e)}"
                stats["errors"].append(error_msg)
                logger.error(
                    "Order import failed",
                    order_number=order_number,
                    error=str(e),
                    exc_info=True,
                )

        await self.db_session.commit()

        logger.info(
            "StockX order import completed",
            batch_id=batch_id,
            **stats,
        )

        return stats

    async def _import_single_stockx_order(self, order_data: Dict[str, Any]) -> str:
        """
        Import or update a single StockX order.

        Args:
            order_data: Order dictionary from StockX API

        Returns:
            "created", "updated", or "skipped"
        """
        order_number = order_data.get("orderNumber")
        if not order_number:
            logger.warning("Order missing orderNumber field", order_data=order_data)
            return "skipped"

        # Parse order data from StockX API response structure
        amount_data = order_data.get("amount", {})
        amount_value = amount_data.get("amount") if isinstance(amount_data, dict) else None
        currency_code = amount_data.get("currency") if isinstance(amount_data, dict) else None

        # Parse dates
        created_at = self._parse_datetime(order_data.get("createdAt"))
        updated_at = self._parse_datetime(order_data.get("updatedAt"))

        # Try to match with inventory item (optional for now)
        inventory_item_id = await self._find_matching_inventory_item(order_data)

        # Get StockX platform ID (Gibson Schema v2.4)
        platform_id = await self._get_platform_id("stockx")

        # Prepare order record
        order_values = {
            "platform_id": platform_id,  # Gibson v2.4 required field
            "external_id": order_number,  # Generic platform order ID
            "stockx_order_number": order_number,  # Keep for backward compatibility
            "status": order_data.get("status", "UNKNOWN"),
            "amount": Decimal(str(amount_value)) if amount_value is not None else None,
            "currency_code": currency_code,
            "inventory_type": order_data.get("inventoryType"),
            "stockx_created_at": created_at,
            "last_stockx_updated_at": updated_at,
            "raw_data": order_data,  # Store complete API response
            "platform_specific_data": {
                "product_id": order_data.get("productId"),
                "variant_id": order_data.get("variantId"),
                "shipment_display_id": order_data.get("shipmentDisplayId"),
            },
            "updated_at": datetime.utcnow(),
        }

        # Only set inventory_item_id if we found a match
        if inventory_item_id:
            order_values["inventory_item_id"] = inventory_item_id

        # Check if order already exists
        stmt = select(Order).where(Order.stockx_order_number == order_number)
        result = await self.db_session.execute(stmt)
        existing_order = result.scalar_one_or_none()

        if existing_order:
            # Update existing order
            for key, value in order_values.items():
                if key != "stockx_order_number":  # Don't update the unique key
                    setattr(existing_order, key, value)

            logger.debug(
                "Updated existing order",
                order_number=order_number,
                status=order_data.get("status"),
            )
            return "updated"
        else:
            # Create new order - inventory_item_id is required by schema
            # For now, we create a placeholder inventory item or find one
            if not inventory_item_id:
                # Try to find or create a placeholder inventory item
                inventory_item_id = await self._get_or_create_placeholder_inventory_item(order_data)

            order_values["inventory_item_id"] = inventory_item_id

            # Create new order
            new_order = Order(**order_values)
            self.db_session.add(new_order)

            logger.debug(
                "Created new order",
                order_number=order_number,
                status=order_data.get("status"),
            )
            return "created"

    async def _find_matching_inventory_item(self, order_data: Dict[str, Any]) -> Optional[UUID]:
        """
        Try to find a matching inventory item for the order.

        Matches based on (in order of priority):
        1. StockX listing ID (exact match)
        2. Product ID + Size (high confidence)
        3. SKU + Size (medium confidence)
        4. Product name + Size + Brand (lower confidence)

        Returns the inventory item ID if found, None otherwise.
        """
        try:
            # Extract order data
            product_data = order_data.get("product", {})
            variant_data = order_data.get("variant", {})

            stockx_product_id = product_data.get("productId")
            product_name = product_data.get("productName", "")
            style_code = product_data.get("styleId")
            size_value = variant_data.get("variantValue")
            brand_name = order_data.get("brand", "")  # If available in order data

            # Strategy 1: Try to find by StockX listing ID (if order has it)
            stockx_listing_id = order_data.get("listingId")
            if stockx_listing_id:
                stmt = select(InventoryItem).where(
                    and_(
                        InventoryItem.external_ids.is_not(None),
                        InventoryItem.external_ids["stockx_listing_id"].astext
                        == stockx_listing_id,
                    )
                )
                result = await self.db_session.execute(stmt)
                item = result.scalar_one_or_none()
                if item:
                    logger.info(
                        f"Found inventory match by StockX listing ID: {stockx_listing_id}"
                    )
                    return item.id

            # Strategy 2: Match by StockX product ID + size
            if stockx_product_id and size_value:
                stmt = (
                    select(InventoryItem)
                    .join(Size, isouter=True)
                    .where(
                        and_(
                            InventoryItem.external_ids.is_not(None),
                            InventoryItem.external_ids["stockx_product_id"].astext
                            == stockx_product_id,
                            or_(Size.value == size_value, Size.value.is_(None)),
                        )
                    )
                )
                result = await self.db_session.execute(stmt)
                item = result.scalar_one_or_none()
                if item:
                    logger.info(
                        f"Found inventory match by StockX product ID + size: {stockx_product_id}"
                    )
                    return item.id

            # Strategy 3: Match by SKU (style code) + size
            if style_code and size_value:
                stmt = (
                    select(InventoryItem)
                    .join(Product)
                    .join(Size, isouter=True)
                    .where(
                        and_(
                            Product.sku == style_code,
                            or_(Size.value == size_value, Size.value.is_(None)),
                        )
                    )
                )
                result = await self.db_session.execute(stmt)
                item = result.scalar_one_or_none()
                if item:
                    logger.info(f"Found inventory match by SKU + size: {style_code}")
                    return item.id

            # Strategy 4: Fuzzy match by product name + size + brand (least confident)
            if product_name and size_value:
                normalized_name = product_name.lower().strip()
                stmt = (
                    select(InventoryItem)
                    .join(Product)
                    .join(Brand, isouter=True)
                    .join(Size, isouter=True)
                    .where(
                        and_(
                            func.lower(Product.name).like(f"%{normalized_name}%"),
                            or_(Size.value == size_value, Size.value.is_(None)),
                            or_(
                                Brand.name.ilike(f"%{brand_name}%") if brand_name else True,
                                Brand.name.is_(None),
                            ),
                        )
                    )
                )
                result = await self.db_session.execute(stmt)
                item = result.scalar_one_or_none()
                if item:
                    logger.info(
                        f"Found inventory match by product name + size: {product_name}"
                    )
                    return item.id

            # No match found
            logger.debug(
                f"No inventory match found for order {order_data.get('orderNumber', 'unknown')}"
            )
            return None

        except Exception as e:
            logger.error(
                f"Error finding matching inventory item: {str(e)}", exc_info=True
            )
            return None

    async def _get_or_create_placeholder_inventory_item(self, order_data: Dict[str, Any]) -> UUID:
        """
        Get or create a placeholder inventory item for orders without matched inventory.

        Uses Gibson-optimized schema:
        - Extracts nested product/variant data from StockX API
        - Detects and creates Brand from product name
        - Detects Category from product type
        - Creates InventoryItem with proper foreign keys
        """
        order_number = order_data.get("orderNumber", "unknown")

        # Extract nested product data from StockX API response
        product_data = order_data.get("product", {})
        variant_data = order_data.get("variant", {})

        stockx_product_id = product_data.get("productId")
        product_name = product_data.get("productName", "Unknown Product")
        style_code = product_data.get("styleId")  # Real manufacturer SKU
        variant_id = variant_data.get("variantId")
        variant_value = variant_data.get("variantValue")

        # Extract size from variant data
        size_value = variant_value or "Unknown"

        # Check if placeholder already exists using external_ids
        stmt = select(InventoryItem).where(
            InventoryItem.external_ids.contains({"stockx_order_number": order_number})
        )
        result = await self.db_session.execute(stmt)
        existing_item = result.scalar_one_or_none()

        if existing_item:
            logger.debug("Found existing placeholder", order_number=order_number)
            return existing_item.id

        # Get or create Product with brand and category detection
        product_id = await self._get_or_create_product(
            stockx_product_id=stockx_product_id,
            product_name=product_name,
            style_code=style_code,
        )

        # Get or create Size
        size_id = await self._get_or_create_size(
            size_value=size_value or "Unknown", region="US"  # Default to US sizing for StockX
        )

        # Create new placeholder inventory item with Gibson schema fields
        placeholder = InventoryItem(
            product_id=product_id,  # REQUIRED FK
            size_id=size_id,  # REQUIRED FK
            quantity=1,  # REQUIRED
            status="sold",  # REQUIRED
            location="StockX",
            notes=f"Auto-created for StockX order {order_number}",
            external_ids={  # JSONB field for tracking
                "stockx_order_number": order_number,
                "stockx_product_id": stockx_product_id,
                "stockx_variant_id": variant_id,
                "is_placeholder": True,
            },
        )
        self.db_session.add(placeholder)
        await self.db_session.flush()  # Get the ID without committing

        logger.debug(
            "Created placeholder inventory item",
            order_number=order_number,
            inventory_item_id=str(placeholder.id),
            product_id=str(product_id),
            size_id=str(size_id),
        )

        return placeholder.id

    async def _get_or_create_product(
        self, stockx_product_id: Optional[str], product_name: str, style_code: Optional[str] = None
    ) -> UUID:
        """
        Find or create a Product with intelligent Brand and Category detection.

        Uses shared services:
        - BrandExtractorService: DB-driven pattern matching + intelligent fallback
        - CategoryDetectionService: Keyword-based category classification

        Gibson schema requirements:
        - sku (VARCHAR, REQUIRED, UNIQUE) - Uses style_code if available, otherwise generates from stockx_product_id
        - category_id (UUID, REQUIRED, FK)
        - name (VARCHAR, REQUIRED)
        - brand_id (UUID, OPTIONAL, FK)
        - style_code (VARCHAR, OPTIONAL) - Real manufacturer product code
        """
        # 1. Try to find existing product by StockX product ID
        if stockx_product_id:
            stmt = select(Product).where(Product.stockx_product_id == stockx_product_id)
            result = await self.db_session.execute(stmt)
            product = result.scalar_one_or_none()

            if product:
                logger.debug("Found existing product", stockx_product_id=stockx_product_id)
                return product.id

        # 2. Extract brand using shared service (DB patterns + intelligent fallback)
        brand = await self.brand_service.extract_brand_from_name(
            product_name, create_if_not_found=True
        )

        # 3. Detect category using shared service (keyword-based classification)
        category = await self.category_service.detect_category_from_name(
            product_name, create_if_not_found=True
        )

        # 4. Generate SKU - prefer real style_code, fallback to generated SKU
        if style_code:
            sku = style_code  # Use real manufacturer SKU (e.g., "DV0982-100", "ID2350")
        elif stockx_product_id:
            sku = f"STOCKX-{stockx_product_id}"  # Fallback for items without style_code
        else:
            sku = f"STOCKX-UNKNOWN-{product_name[:20]}"  # Last resort

        # 5. Check if SKU already exists (SKU is UNIQUE)
        stmt = select(Product).where(Product.sku == sku)
        result = await self.db_session.execute(stmt)
        existing_product = result.scalar_one_or_none()

        if existing_product:
            logger.debug("Found product by SKU", sku=sku)
            return existing_product.id

        # 6. Create new product with detected brand and category
        product = Product(
            sku=sku,
            category_id=category.id if category else None,  # Category should always exist
            brand_id=brand.id if brand else None,  # Brand is optional
            name=product_name,
            stockx_product_id=stockx_product_id,
            style_code=style_code,  # Store the real manufacturer code
        )
        self.db_session.add(product)
        await self.db_session.flush()

        logger.info(
            "Created new product with brand/category",
            product_id=str(product.id),
            sku=sku,
            style_code=style_code,
            name=product_name,
            brand=brand.name if brand else "Unknown",
            category=category.name if category else "Unknown",
        )
        return product.id

    async def _get_or_create_size(self, size_value: str, region: str = "US") -> UUID:
        """
        Find or create a Size entry.

        Gibson schema requirements:
        - value (VARCHAR, REQUIRED)
        - region (VARCHAR, REQUIRED)
        - category_id (UUID, optional)
        """
        # Try to find existing size
        stmt = select(Size).where(Size.value == size_value, Size.region == region)
        result = await self.db_session.execute(stmt)
        size = result.scalar_one_or_none()

        if size:
            logger.debug("Found existing size", size_value=size_value, region=region)
            return size.id

        # Create new size
        size = Size(value=size_value, region=region, category_id=None)  # Optional, can be set later
        self.db_session.add(size)
        await self.db_session.flush()

        logger.debug("Created new size", size_id=str(size.id), value=size_value, region=region)
        return size.id

    async def _get_platform_id(self, platform_slug: str) -> UUID:
        """
        Get platform ID by slug (e.g., 'stockx', 'ebay', 'goat', 'alias').
        Caches results to minimize database queries.

        Gibson Schema v2.4 Compliance: All orders must have platform_id
        """
        if platform_slug in self._platform_cache:
            return self._platform_cache[platform_slug]

        stmt = select(Platform).where(Platform.slug == platform_slug)
        result = await self.db_session.execute(stmt)
        platform = result.scalar_one_or_none()

        if not platform:
            raise ValueError(f"Platform '{platform_slug}' not found in database")

        self._platform_cache[platform_slug] = platform.id
        logger.debug(
            "Cached platform ID", platform_slug=platform_slug, platform_id=str(platform.id)
        )
        return platform.id

    @staticmethod
    def _parse_datetime(date_string: Optional[str]) -> Optional[datetime]:
        """Parse ISO format datetime string from StockX API"""
        if not date_string:
            return None

        try:
            # StockX uses ISO 8601 format with timezone
            return datetime.fromisoformat(date_string.replace("Z", "+00:00"))
        except (ValueError, AttributeError) as e:
            logger.warning("Failed to parse datetime", date_string=date_string, error=str(e))
            return None

"""
Order Processing Service (Gibson Schema v2.4)
Creates marketplace orders from validated import data
Migrated from legacy Order model to unified Order model
"""

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional, Union
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from shared.database.models import (
    InventoryItem,
    Platform,
    Order,
)

logger = structlog.get_logger(__name__)

from sqlalchemy.ext.asyncio import AsyncSession


class OrderProcessor:
    """Creates orders from validated sales data (Gibson Schema v2.4 compliant)"""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.platform_cache: Dict[str, UUID] = {}  # Cache platform IDs
        self.product_cache = {}

    async def create_orders_from_batch(self, batch_id: str) -> Dict[str, Any]:
        """
        Create sales orders from an import batch

        Args:
            batch_id: Import batch ID to process

        Returns:
            Processing statistics
        """
        logger.info("Creating orders from batch", batch_id=batch_id)

        stats = {"orders_created": 0, "orders_updated": 0, "errors": [], "skipped": 0}

        from shared.database.models import ImportRecord

        query = select(ImportRecord).where(
            ImportRecord.batch_id == batch_id, ImportRecord.status == "processed"
        )

        result = await self.db_session.execute(query)
        records = result.scalars().all()

        logger.info("Processing records for orders", batch_id=batch_id, records_count=len(records))

        for record in records:
            try:
                order_created = await self._create_order_from_record(record)

                if order_created:
                    stats["orders_created"] += 1
                else:
                    stats["skipped"] += 1

            except Exception as e:
                error_msg = f"Failed to create order for record {record.id}: {str(e)}"
                stats["errors"].append(error_msg)
                logger.error(
                    "Order creation failed",
                    record_id=str(record.id),
                    error=str(e),
                    error_type=type(e).__name__,
                )

        logger.info("Order creation completed", batch_id=batch_id, **stats)

        return stats

    async def _create_order_from_record(self, import_record) -> bool:
        """Create a order from an import record"""

        processed_data = import_record.processed_data
        if not processed_data:
            return False

        # Extract order data
        source_platform = (
            processed_data.get("source_platform") or processed_data.get("platform") or ""
        ).lower()
        order_number = processed_data.get("order_number")
        external_transaction_id = processed_data.get("external_transaction_id")

        if not order_number:
            return False

        # Check if order already exists
        existing_order = await self._find_existing_order(
            source_platform, order_number, external_transaction_id
        )

        if existing_order:
            return False

        # Get or create platform
        platform = await self._get_or_create_platform(source_platform)
        if not platform:
            return False

        # Get or create product and inventory item
        inventory_item = await self._get_or_create_inventory_item(processed_data)
        if not inventory_item:
            return False

        # Create order (Gibson Schema v2.4)
        try:
            sale_date = self._parse_datetime(processed_data.get("sale_date"))
            if sale_date is None:
                sale_date = datetime.utcnow()

            # Ensure IDs are accessible
            inventory_item_id = inventory_item.id
            platform_id = platform.id

            order = Order(
                inventory_item_id=inventory_item_id,  # Gibson v2.4 field name
                platform_id=platform_id,
                sold_at=sale_date,  # Gibson v2.4: sold_at (not transaction_date)
                gross_sale=self._extract_decimal(processed_data, "sale_price")
                or self._extract_decimal(processed_data, "listing_price")
                or Decimal("0.00"),
                platform_fee=self._extract_decimal(processed_data, "seller_fee")
                or self._extract_decimal(processed_data, "platform_fee")
                or Decimal("0.00"),
                shipping_cost=self._extract_decimal(processed_data, "shipping_fee")
                or Decimal("0.00"),
                net_profit=self._extract_decimal(processed_data, "net_profit")
                or self._extract_decimal(processed_data, "total_payout")
                or Decimal("0.00"),
                status="completed",  # Imported sales are completed
                external_id=external_transaction_id or f"{source_platform}_{order_number}",
                stockx_order_number=(
                    order_number if source_platform == "stockx" else None
                ),  # For backward compat
                buyer_destination_country=processed_data.get("buyer_destination_country"),
                buyer_destination_city=processed_data.get("buyer_destination_city"),
                notes=f"Imported from {source_platform.upper()} batch {import_record.batch_id}",
            )
        except Exception:
            raise

        self.db_session.add(order)

        return True

    async def _find_existing_order(
        self, platform_name: str, order_number: str, external_id: str = None
    ) -> Optional[Order]:
        """Check if order already exists"""

        # Try to find by external_id first
        if external_id:
            query = select(Order).where(Order.external_id == external_id)
            result = await self.db_session.execute(query)
            orders = result.scalars().all()
            if orders:
                return orders[0]  # Return first match if multiple found

        # Fallback: find by platform + order number pattern
        platform = await self._get_platform(platform_name)
        if platform:
            query = select(Order).where(
                Order.platform_id == platform.id,
                Order.external_id.ilike(f"%{order_number}%"),
            )
            result = await self.db_session.execute(query)
            orders = result.scalars().all()
            return orders[0] if orders else None

        return None

    async def _get_or_create_platform(self, platform_name: str) -> Optional[Platform]:
        """Get or create platform by name"""
        if not platform_name:
            return None

        # Check cache first (cache platform IDs, not objects)
        if platform_name in self.platform_cache:
            # Re-query the platform to ensure it's attached to current session
            platform_id = self.platform_cache[platform_name]
            query = select(Platform).where(Platform.id == platform_id)
            result = await self.db_session.execute(query)
            platforms = result.scalars().all()
            if platforms:
                return platforms[0]
            else:
                # Platform was deleted, remove from cache
                del self.platform_cache[platform_name]

        # Query database
        platform = await self._get_platform(platform_name)

        if platform:
            # Cache the platform ID for future use
            self.platform_cache[platform_name] = platform.id
            return platform

        if not platform:
            # Create new platform
            platform = Platform(
                name=platform_name.title(),
                slug=platform_name.lower(),
                fee_percentage=self._get_default_fee_percentage(platform_name),
                supports_fees=self._platform_supports_fees(platform_name),
                active=True,
            )
            self.db_session.add(platform)

            logger.info("Created new platform", name=platform_name)

        # Cache platform ID for future use (not the object itself)
        self.platform_cache[platform_name] = platform.id
        return platform

    async def _get_platform(self, platform_name: str) -> Optional[Platform]:
        """Get platform by name or slug"""
        query = select(Platform).where(
            (Platform.name.ilike(platform_name)) | (Platform.slug == platform_name.lower())
        )
        result = await self.db_session.execute(query)
        platforms = result.scalars().all()
        return platforms[0] if platforms else None

    async def _get_or_create_inventory_item(
        self, processed_data: Dict[str, Any]
    ) -> Optional[InventoryItem]:
        """Get or create inventory item for the order"""

        # For now, create a basic inventory item
        # In a real system, you'd want to match against existing inventory
        # or create placeholder items for sales tracking

        product_name = processed_data.get("product_name", processed_data.get("item_name", ""))
        sku = self._normalize_sku(processed_data.get("sku", ""))
        size = processed_data.get("size", "Unknown")

        if not product_name:
            return None

        # For simplicity, create a placeholder inventory item
        # In production, you'd want proper product/inventory matching
        from shared.database.models import Category, Product

        # Get or create product (simplified)
        # First try to find by SKU if we have a valid one
        product = None
        if sku:
            sku_query = select(Product).where(Product.sku == sku)
            sku_result = await self.db_session.execute(sku_query)
            products = sku_result.scalars().all()
            product = products[0] if products else None

        # If no product found by SKU (or no valid SKU), try by name
        # This is especially important for StockX items with N/A SKUs
        if not product:
            query = select(Product).where(Product.name == product_name)
            result = await self.db_session.execute(query)
            products = result.scalars().all()
            product = products[0] if products else None

            # If we found a product by name but it has no SKU and we have one, update it
            if product and not product.sku and sku:
                logger.info(
                    "Updating existing product with new SKU", product_name=product_name, new_sku=sku
                )
                product.sku = sku

        if not product:
            # Create basic product
            # Get default category and brand
            category_query = select(Category).where(Category.name == "Footwear")
            category_result = await self.db_session.execute(category_query)
            categories = category_result.scalars().all()
            category = categories[0] if categories else None

            if not category:
                # Create default category
                category = Category(name="Footwear", slug="footwear")
                self.db_session.add(category)

            # For items without valid SKU (like StockX N/A), we'll create a product without SKU
            # and rely on product name for identification. Only generate auto-SKU if we have
            # partial SKU data that needs to be made unique.
            safe_name = product_name[:15].upper().replace(" ", "_").replace("-", "_")
            # Remove special characters
            safe_name = "".join(c for c in safe_name if c.isalnum() or c == "_")

            # For truly missing SKUs (like StockX N/A), don't generate auto-SKU
            # The product will be identified by name instead
            if sku:
                # We have some SKU data, ensure it's unique
                pass  # Use the provided SKU
            else:
                # No SKU available (N/A case) - product will be SKU-less
                sku = None

            # Try to create product with error handling for duplicate SKU
            try:
                product = Product(
                    sku=sku,
                    name=product_name,
                    category_id=category.id,
                    description=f"Auto-created from import: {product_name}",
                )
                self.db_session.add(product)
            except IntegrityError:
                # If SKU already exists, try to find the existing product
                if sku:
                    existing_query = select(Product).where(Product.sku == sku)
                    existing_result = await self.db_session.execute(existing_query)
                    products = existing_result.scalars().all()
                    product = products[0] if products else None
                else:
                    # If no SKU, try to find by name
                    existing_query = select(Product).where(Product.name == product_name)
                    existing_result = await self.db_session.execute(existing_query)
                    products = existing_result.scalars().all()
                    product = products[0] if products else None

                if not product:
                    # If still no product found, generate a new unique SKU
                    import uuid

                    unique_suffix = str(uuid.uuid4())[:8]
                    new_sku = (
                        f"{sku}_{unique_suffix}" if sku else f"AUTO_{safe_name}_{unique_suffix}"
                    )

                    product = Product(
                        sku=new_sku,
                        name=product_name,
                        category_id=category.id,
                        description=f"Auto-created from import: {product_name}",
                    )
                    self.db_session.add(product)

        # Ensure we have a valid product
        if not product:
            return None

        # Get or create size
        size_obj = await self._get_or_create_size(size)

        # Create inventory item
        try:
            purchase_date = self._parse_datetime(processed_data.get("purchase_date"))

            # Ensure IDs are accessible
            product_id = product.id
            size_id = size_obj.id

            inventory_item = InventoryItem(
                product_id=product_id,
                size_id=size_id,
                quantity=1,
                status="sold",  # Imported sales are already sold
                purchase_date=purchase_date,
                purchase_price=self._extract_decimal(processed_data, "purchase_price"),
                supplier=processed_data.get("supplier", processed_data.get("seller_name", "")),
                notes=f"Auto-created from sales import - Size: {size}",
            )
        except Exception:
            raise

        self.db_session.add(inventory_item)

        return inventory_item

    def _extract_decimal(self, data: Dict[str, Any], key: str) -> Optional[Decimal]:
        """Safely extract Decimal value from data"""
        value = data.get(key)
        if value is None:
            return None

        try:
            if isinstance(value, (int, float)):
                return Decimal(str(value))
            elif isinstance(value, str):
                # Clean string and convert
                cleaned = value.replace(",", "").replace("$", "").replace("€", "").strip()
                if cleaned:
                    return Decimal(cleaned)
        except (ValueError, InvalidOperation):
            pass

        return None

    def _get_default_fee_percentage(self, platform_name: str) -> Decimal:
        """Get default fee percentage for platform"""
        default_fees = {
            "stockx": Decimal("9.5"),
            "goat": Decimal("9.5"),
            "ebay": Decimal("10.0"),
            "alias": Decimal("0.0"),  # Alias = GOAT platform
            "manual": Decimal("0.0"),
        }

        return default_fees.get(platform_name.lower(), Decimal("5.0"))

    def _platform_supports_fees(self, platform_name: str) -> bool:
        """Check if platform supports explicit fees"""
        no_fee_platforms = ["alias", "manual"]  # Alias = GOAT (no explicit fees in export)
        return platform_name.lower() not in no_fee_platforms

    def _parse_datetime(self, date_value: Union[str, datetime, None]) -> Optional[datetime]:
        """Parse date value to datetime object"""
        if date_value is None:
            return None

        if isinstance(date_value, datetime):
            return date_value

        if isinstance(date_value, str):
            try:
                # Try dateutil first (most flexible)
                from dateutil import parser

                return parser.parse(date_value)
            except ImportError:
                # Fallback to manual parsing for common formats
                try:
                    if "T" in date_value and "+" in date_value:
                        # ISO format: 2022-07-08T00:46:09+00:00
                        return datetime.fromisoformat(date_value.replace("Z", "+00:00"))
                    else:
                        # Try standard format
                        return datetime.strptime(date_value, "%Y-%m-%d %H:M:%S")
                except Exception:
                    return None
            except Exception:
                return None

        return None

    def _normalize_sku(self, sku_value: Any) -> Optional[str]:
        """Normalize SKU value, handling 'nan' and invalid values"""
        if sku_value is None:
            return None

        sku_str = str(sku_value).strip()

        # Handle pandas NaN values and invalid SKUs (including N/A from StockX)
        if not sku_str or sku_str.lower() in ["nan", "none", "null", "", "n/a", "na"]:
            return None

        # Handle numeric NaN from pandas/numpy
        try:
            import math

            if isinstance(sku_value, float) and math.isnan(sku_value):
                return None
        except (ImportError, TypeError):
            pass

        return sku_str

    async def _get_or_create_size(self, size_value: str):
        """Get or create size object"""
        from shared.database.models import Category, Size

        if not size_value:
            size_value = "Unknown"

        # Try to find existing size
        query = select(Size).where(Size.value == size_value)
        result = await self.db_session.execute(query)
        sizes = result.scalars().all()
        size_obj = sizes[0] if sizes else None

        if not size_obj:
            # Get default category for size
            category_query = select(Category).where(Category.name == "Footwear")
            category_result = await self.db_session.execute(category_query)
            categories = category_result.scalars().all()
            category = categories[0] if categories else None

            if not category:
                category = Category(name="Footwear", slug="footwear")
                self.db_session.add(category)

            # Create new size
            size_obj = Size(
                category_id=category.id, value=size_value, region="US"  # Default to US sizing
            )
            self.db_session.add(size_obj)

        return size_obj

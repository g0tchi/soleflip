"""
Inventory Domain Service
Business logic layer for inventory management
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import structlog
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import (
    Brand,
    Category,
    InventoryItem,
    MarketplaceData,
    Platform,
    Product,
    Size,
)
from shared.repositories import BaseRepository

from ..repositories.inventory_repository import (
    InventoryRepository,
)
from ..repositories.product_repository import ProductRepository

logger = structlog.get_logger(__name__)


@dataclass
class InventoryStats:
    """Inventory statistics"""

    total_items: int
    in_stock: int
    sold: int
    listed: int
    total_value: Decimal
    avg_purchase_price: Decimal


@dataclass
class ProductCreationRequest:
    """Request for creating a new product"""

    sku: str
    name: str
    brand_name: str
    category_name: str
    description: Optional[str] = None
    retail_price: Optional[Decimal] = None
    release_date: Optional[datetime] = None


@dataclass
class InventoryItemRequest:
    """Request for adding inventory item"""

    product_id: UUID
    size_value: str
    size_region: str
    quantity: int
    purchase_price: Optional[Decimal] = None
    purchase_date: Optional[datetime] = None
    supplier: Optional[str] = None


class InventoryService:
    """Domain service for inventory operations"""

    def __init__(self, db_session: AsyncSession, stockx_service: Optional[Any] = None):
        self.db_session = db_session
        self.logger = logger.bind(service="inventory")
        self.product_repo = ProductRepository(self.db_session)
        self.brand_repo = BaseRepository(Brand, self.db_session)
        self.category_repo = BaseRepository(Category, self.db_session)
        self.size_repo = BaseRepository(Size, self.db_session)
        self.inventory_repo = InventoryRepository(self.db_session)
        self.stockx_service = stockx_service

    async def get_inventory_overview(self) -> InventoryStats:
        """Get overall inventory statistics using optimized aggregation query"""
        repo_stats = await self.inventory_repo.get_inventory_stats()

        self.logger.info(
            "Generated inventory overview",
            total_items=repo_stats.total_items,
            in_stock=repo_stats.in_stock,
            sold=repo_stats.sold,
            listed=repo_stats.listed,
            total_value=float(repo_stats.total_value),
        )

        # Convert repository stats to service stats (compatibility)
        return InventoryStats(
            total_items=repo_stats.total_items,
            in_stock=repo_stats.in_stock,
            sold=repo_stats.sold,
            listed=repo_stats.listed,
            total_value=repo_stats.total_value,
            avg_purchase_price=repo_stats.avg_purchase_price,
        )

    async def mark_stockx_item_as_presale(self, stockx_listing_id: str) -> bool:
        """Mark a StockX listed item as presale - finds the inventory item automatically"""
        try:
            # Find inventory item by StockX listing ID
            from sqlalchemy import select

            from shared.database.models import InventoryItem

            stmt = select(InventoryItem).where(
                and_(
                    InventoryItem.external_ids.is_not(None),
                    InventoryItem.external_ids["stockx_listing_id"].astext == stockx_listing_id,
                )
            )
            result = await self.db_session.execute(stmt)
            item = result.scalar_one_or_none()

            if not item:
                self.logger.error(f"No inventory item found for StockX listing {stockx_listing_id}")
                return False

            # Simply update the status to presale
            await self.inventory_repo.update(item.id, {"status": "presale"})

            self.logger.info(f"Marked StockX listing {stockx_listing_id} as presale")
            return True

        except Exception as e:
            self.logger.error(f"Failed to mark StockX item as presale: {e}")
            return False

    async def unmark_stockx_presale(self, stockx_listing_id: str) -> bool:
        """Remove presale marking from a StockX item"""
        try:
            # Find inventory item by StockX listing ID
            from sqlalchemy import select

            from shared.database.models import InventoryItem

            stmt = select(InventoryItem).where(
                and_(
                    InventoryItem.external_ids.is_not(None),
                    InventoryItem.external_ids["stockx_listing_id"].astext == stockx_listing_id,
                )
            )
            result = await self.db_session.execute(stmt)
            item = result.scalar_one_or_none()

            if not item:
                self.logger.error(f"No inventory item found for StockX listing {stockx_listing_id}")
                return False

            # Reset status back to listed_stockx
            await self.inventory_repo.update(item.id, {"status": "listed_stockx"})

            self.logger.info(f"Removed presale marking from StockX listing {stockx_listing_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to remove presale marking: {e}")
            return False

    async def get_stockx_presale_markings(self) -> dict:
        """Get all StockX presale markings as a dict"""
        try:
            from sqlalchemy import select

            from shared.database.models import StockXPresaleMarking

            stmt = select(StockXPresaleMarking).where(StockXPresaleMarking.is_presale.is_(True))
            result = await self.db_session.execute(stmt)
            markings = result.scalars().all()

            # Return as dict with stockx_listing_id as key
            return {
                marking.stockx_listing_id: {
                    "is_presale": marking.is_presale,
                    "marked_at": marking.marked_at.isoformat() if marking.marked_at else None,
                    "product_name": marking.product_name,
                    "size": marking.size,
                }
                for marking in markings
            }

        except Exception as e:
            self.logger.error("Failed to get StockX presale markings", error=str(e))
            return {}

    async def sync_all_stockx_listings_to_inventory(self) -> Dict[str, int]:
        """
        SIMPLIFIED: Sync StockX listings to inventory without complex queries
        """
        self.logger.info("Starting simplified sync of StockX listings to inventory")
        stats = {"created": 0, "updated": 0, "skipped": 0, "matched": 0}

        try:
            # Get StockX service
            stockx_service = self.stockx_service
            if not stockx_service:
                from domains.integration.services.stockx_service import StockXService

                stockx_service = StockXService(self.db_session)

            # Get all ACTIVE StockX listings only (not history)
            all_listings = await stockx_service.get_all_listings()
            # Filter for ACTIVE and PENDING listings only
            listings = [
                listing
                for listing in all_listings
                if listing.get("status", "").upper() in ["ACTIVE", "PENDING"]
            ]
            self.logger.info(
                f"Found {len(listings)} active StockX listings to sync "
                f"(filtered from {len(all_listings)} total listings)"
            )

            # Get or create default category and brand
            default_category = await self._get_default_category()
            default_brand = await self._get_default_brand()

            # Get or create StockX platform for marketplace data
            stockx_platform = await self._get_or_create_stockx_platform()

            # Process each listing individually (simple approach)
            for listing in listings:
                listing_id = listing.get("listingId")
                if not listing_id:
                    stats["skipped"] += 1
                    continue

                try:
                    # Simple check: does this listing already exist?
                    existing_item = await self._simple_listing_check(listing_id)
                    if existing_item:
                        stats["matched"] += 1
                        # Update marketplace data for existing items
                        await self._create_or_update_marketplace_data(
                            existing_item, listing, stockx_platform
                        )
                        continue

                    # Create new inventory item
                    inventory_item = await self._create_simple_inventory_item(
                        listing, default_category, default_brand
                    )

                    # Create marketplace data for the new item
                    await self._create_or_update_marketplace_data(
                        inventory_item, listing, stockx_platform
                    )

                    stats["created"] += 1

                except Exception as e:
                    self.logger.error(f"Failed to process listing {listing_id}: {e}")
                    stats["skipped"] += 1
                    continue

            # Commit all changes
            await self.db_session.commit()

            self.logger.info("Completed simplified StockX listings sync", stats=stats)
            return stats

        except Exception as e:
            await self.db_session.rollback()
            self.logger.error("Failed to sync StockX listings to inventory", error=str(e))
            return {"error": str(e)}

    async def _get_default_category(self):
        """Get or create default category for StockX items"""
        from shared.database.models import Category

        result = await self.db_session.execute(
            select(Category).where(Category.name == "StockX Import")
        )
        category = result.scalar_one_or_none()
        if not category:
            category = Category(name="StockX Import", slug="stockx-import")
            self.db_session.add(category)
            await self.db_session.flush()
        return category

    async def _get_default_brand(self):
        """Get or create default brand for unknown brands"""
        from shared.database.models import Brand

        result = await self.db_session.execute(select(Brand).where(Brand.name == "Unknown Brand"))
        brand = result.scalar_one_or_none()
        if not brand:
            brand = Brand(name="Unknown Brand", slug="unknown-brand")
            self.db_session.add(brand)
            await self.db_session.flush()
        return brand

    async def _simple_listing_check(self, listing_id: str):
        """Simple check if listing already exists in external_ids"""
        from shared.database.models import InventoryItem

        try:
            result = await self.db_session.execute(
                select(InventoryItem).where(
                    and_(
                        InventoryItem.external_ids.is_not(None),
                        InventoryItem.external_ids.op("->>")("stockx_listing_id") == listing_id,
                    )
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            self.logger.warning(f"Error checking for existing listing {listing_id}: {e}")
            return None

    async def _create_simple_inventory_item(self, listing, default_category, default_brand):
        """Create simple inventory item from StockX listing with proper SKU strategy"""
        from datetime import datetime, timezone

        from shared.database.models import InventoryItem, Size

        listing_id = listing.get("listingId")
        product_info = listing.get("product", {})
        variant_info = listing.get("variant", {})
        ask_info = listing.get("ask", {})

        product_name = product_info.get("productName", "Unknown Product")
        size_value = variant_info.get("variantValue") or "Unknown Size"

        # CORRECT SKU STRATEGY: Use styleId as primary, fallback to productId
        style_id = product_info.get("styleId", "").strip()
        product_id = product_info.get("productId", "")

        if style_id:
            sku = style_id  # e.g., "DR5540-006", "HQ8752"
        elif product_id:
            sku = f"pid-{product_id[:8]}"  # e.g., "pid-89b4275b"
        else:
            sku = f"stockx-{listing_id[:8]}"  # last resort

        # Check if product with this SKU already exists
        existing_product = await self._get_or_create_product_by_sku(
            sku, product_name, default_brand, default_category
        )

        # Create or get size
        size_result = await self.db_session.execute(
            select(Size).where(
                or_(
                    and_(Size.value.is_not(None), Size.value == size_value),
                    and_(Size.value.is_(None), size_value in [None, "", "Unknown Size"]),
                )
            )
        )
        size_obj = size_result.scalar_one_or_none()
        if not size_obj:
            size_obj = Size(value=size_value, category_id=default_category.id, region="US")
            self.db_session.add(size_obj)
            await self.db_session.flush()

        # Create inventory item with comprehensive external_ids and Phase 2 fields
        inventory_item = InventoryItem(
            product_id=existing_product.id,
            size_id=size_obj.id,
            quantity=1,
            status="listed_stockx",
            purchase_price=float(listing.get("amount", 0)),
            reserved_quantity=0,  # Phase 2: Initialize reserved quantity
            external_ids={
                "stockx_listing_id": listing_id,
                "stockx_product_id": product_info.get("productId"),
                "stockx_variant_id": variant_info.get("variantId"),
                "stockx_ask_id": ask_info.get("askId"),
                "created_from_sync": True,
                "sync_timestamp": datetime.now(timezone.utc).isoformat(),
                "currency_code": listing.get("currencyCode", "EUR"),
                "listing_status": listing.get("status", "ACTIVE"),
            },
        )

        # Phase 2: Add platform listing using model helper
        inventory_item.add_platform_listing(
            platform="stockx",
            listing_id=listing_id,
            ask_price=float(listing.get("amount", 0)),
            metadata={
                "currency": listing.get("currencyCode", "EUR"),
                "status": listing.get("status", "ACTIVE"),
            }
        )

        # Phase 2: Add initial status to history
        inventory_item.add_status_change(None, "listed_stockx", "Created from StockX sync")

        self.db_session.add(inventory_item)
        await self.db_session.flush()

        return inventory_item

    async def _get_or_create_product_by_sku(self, sku, name, brand, category):
        """Get existing product by SKU or create new one"""
        from shared.database.models import Product

        # Check if product with this SKU exists
        result = await self.db_session.execute(select(Product).where(Product.sku == sku))
        existing_product = result.scalar_one_or_none()

        if existing_product:
            return existing_product

        # Create new product
        product = Product(sku=sku, name=name, brand_id=brand.id, category_id=category.id)
        self.db_session.add(product)
        await self.db_session.flush()
        return product

    async def _preload_sync_entities(self, listings: List[Dict]) -> Dict[str, Any]:
        """Pre-load all entities needed for sync to avoid N+1 queries"""
        from shared.database.models import Category

        # Extract unique values from listings
        brand_names = set(listing.get("brand", "Unknown") for listing in listings)
        product_skus = set(
            f"stockx-{listing.get('listingId')}" for listing in listings if listing.get("listingId")
        )
        size_values = set(
            listing.get("variant", {}).get("variantValue", "Unknown Size") for listing in listings
        )

        # Batch load all brands
        brands_query = select(Brand).where(Brand.name.in_(brand_names))
        brands_result = await self.db_session.execute(brands_query)
        existing_brands = {brand.name: brand for brand in brands_result.scalars().all()}

        # Batch load all products
        products_query = (
            select(Product).where(Product.sku.in_(product_skus)) if product_skus else None
        )
        existing_products = {}
        if products_query:
            products_result = await self.db_session.execute(products_query)
            existing_products = {
                product.sku: product for product in products_result.scalars().all()
            }

        # Get default category (Sneakers)
        category_query = select(Category).where(Category.name == "Sneakers")
        category_result = await self.db_session.execute(category_query)
        category = category_result.scalar_one_or_none()

        if not category:
            category = Category(name="Sneakers", slug="sneakers")
            self.db_session.add(category)
            await self.db_session.flush()

        # Batch load all sizes for this category
        sizes_query = select(Size).where(
            and_(
                Size.value.is_not(None),
                Size.value.in_(size_values),
                Size.category_id == category.id,
                Size.region == "US",
            )
        )
        sizes_result = await self.db_session.execute(sizes_query)
        existing_sizes = {size.value: size for size in sizes_result.scalars().all()}

        return {
            "brands": existing_brands,
            "products": existing_products,
            "category": category,
            "sizes": existing_sizes,
        }

    async def _process_listings_batch(
        self, listings: List[Dict], entities: Dict[str, Any], stats: Dict[str, int]
    ) -> Dict[str, int]:
        """Process listings in optimized batches"""
        new_brands = []
        new_products = []
        new_sizes = []
        new_inventory_items = []

        for listing in listings:
            listing_id = listing.get("listingId")
            if not listing_id:
                stats["skipped"] += 1
                continue

            try:
                # Skip duplicate detection for now to avoid Boolean errors
                # TODO: Fix boolean clause issues in duplicate detection
                # has_duplicates, duplicate_matches = await self.detect_duplicate_listings(listing)
                #
                # if has_duplicates:
                #     duplicate_handled = self._handle_duplicates(listing_id, duplicate_matches, stats)
                #     if duplicate_handled:
                #         continue

                # Extract listing data
                product_info = listing.get("product", {})
                variant_info = listing.get("variant", {})
                product_name = product_info.get("productName", "Unknown Product")
                size_value = variant_info.get("variantValue", "Unknown Size")
                brand_name = listing.get("brand", "Unknown")

                # Get or create brand
                brand = await self._get_or_prepare_brand(brand_name, entities["brands"], new_brands)

                # Get or create product
                product_sku = f"stockx-{listing_id}"
                product = await self._get_or_prepare_product(
                    product_sku,
                    product_name,
                    brand,
                    entities["category"],
                    entities["products"],
                    new_products,
                )

                # Get or create size (use fallback for null/unknown sizes)
                normalized_size = (
                    size_value if size_value and size_value.strip() else "Unknown Size"
                )
                size_obj = await self._get_or_prepare_size(
                    normalized_size, entities["category"], entities["sizes"], new_sizes
                )

                # Prepare inventory item
                new_inventory_items.append(
                    {
                        "product_id": product.id,
                        "size_id": size_obj.id,
                        "quantity": 1,
                        "status": "listed_stockx",
                        "external_ids": {
                            "stockx_listing_id": listing_id,
                            "created_from_sync": True,
                        },
                    }
                )
                stats["created"] += 1

            except Exception as e:
                self.logger.error(f"Failed to prepare inventory item for listing {listing_id}: {e}")
                stats["skipped"] += 1

        # Batch insert all new entities
        await self._batch_insert_entities(new_brands, new_products, new_sizes, new_inventory_items)

        return stats

    def _handle_duplicates(
        self, listing_id: str, duplicate_matches: List[Dict], stats: Dict[str, int]
    ) -> bool:
        """Handle duplicate detection results"""
        self.logger.info(
            f"Duplicate detected for listing {listing_id}",
            duplicate_count=len(duplicate_matches),
            match_types=[match["match_type"] for match in duplicate_matches],
        )
        stats["duplicates_detected"] += 1

        # Handle high-confidence exact matches automatically
        exact_matches = [match for match in duplicate_matches if match["confidence"] >= 1.0]
        if exact_matches:
            stats["matched"] += 1
            return True

        # For other duplicates, log and potentially merge based on business rules
        high_confidence_matches = [
            match for match in duplicate_matches if match["confidence"] >= 0.9
        ]
        if high_confidence_matches:
            primary_match = high_confidence_matches[0]
            existing_item = primary_match["item"]

            # Update external IDs to include this listing ID
            if not existing_item.external_ids:
                existing_item.external_ids = {}
            existing_item.external_ids["stockx_listing_id"] = listing_id

            stats["duplicates_merged"] += 1
            stats["matched"] += 1
            return True

        return False

    async def _get_or_prepare_brand(
        self, brand_name: str, existing_brands: Dict, new_brands: List
    ) -> Brand:
        """Get existing brand or prepare new one for batch insert"""
        if brand_name in existing_brands:
            return existing_brands[brand_name]

        # Check if already prepared for creation
        for brand in new_brands:
            if brand.name == brand_name:
                return brand

        # Create new brand for batch insert
        from shared.database.models import Brand

        new_brand = Brand(name=brand_name, slug=brand_name.lower().replace(" ", "-"))
        new_brands.append(new_brand)
        existing_brands[brand_name] = new_brand  # Add to cache to avoid duplicates
        return new_brand

    async def _get_or_prepare_product(
        self,
        sku: str,
        name: str,
        brand: Brand,
        category: Category,
        existing_products: Dict,
        new_products: List,
    ) -> Product:
        """Get existing product or prepare new one for batch insert"""
        if sku in existing_products:
            return existing_products[sku]

        # Check if already prepared for creation
        for product in new_products:
            if product.sku == sku:
                return product

        # Create new product for batch insert
        from shared.database.models import Product

        new_product = Product(sku=sku, name=name, brand_id=brand.id, category_id=category.id)
        new_products.append(new_product)
        existing_products[sku] = new_product  # Add to cache
        return new_product

    async def _get_or_prepare_size(
        self, size_value: str, category: Category, existing_sizes: Dict, new_sizes: List
    ) -> Size:
        """Get existing size or prepare new one for batch insert"""
        if size_value in existing_sizes:
            return existing_sizes[size_value]

        # Check if already prepared for creation
        for size in new_sizes:
            if size.value == size_value:
                return size

        # Create new size for batch insert
        from shared.database.models import Size

        new_size = Size(value=size_value, category_id=category.id, region="US")
        new_sizes.append(new_size)
        existing_sizes[size_value] = new_size  # Add to cache
        return new_size

    async def _batch_insert_entities(
        self, brands: List, products: List, sizes: List, inventory_items: List
    ):
        """Batch insert all new entities to minimize database round trips"""
        # Insert brands first (no dependencies)
        if brands:
            self.db_session.add_all(brands)
            await self.db_session.flush()  # Get IDs for dependent entities

        # Insert sizes (depends on category, already exists)
        if sizes:
            self.db_session.add_all(sizes)
            await self.db_session.flush()

        # Insert products (depends on brands)
        if products:
            self.db_session.add_all(products)
            await self.db_session.flush()

        # Insert inventory items (depends on products and sizes)
        if inventory_items:
            inventory_objects = []
            for item_data in inventory_items:
                inventory_objects.append(InventoryItem(**item_data))
            self.db_session.add_all(inventory_objects)

    async def create_product_with_inventory(
        self,
        product_request: ProductCreationRequest,
        inventory_requests: List[InventoryItemRequest],
    ) -> Dict[str, Any]:
        """Create a new product with initial inventory"""
        try:
            brand = await self.brand_repo.find_one_or_create(
                {"name": product_request.brand_name},
                slug=product_request.brand_name.lower().replace(" ", "-"),
            )
            category = await self.category_repo.find_one_or_create(
                {"name": product_request.category_name},
                slug=product_request.category_name.lower().replace(" ", "-"),
                path=product_request.category_name.lower(),
            )

            existing_product = await self.product_repo.find_by_sku(product_request.sku)
            if existing_product:
                raise ValueError(f"Product with SKU {product_request.sku} already exists")

            product_data = product_request.__dict__
            product_data["brand_id"] = brand.id
            product_data["category_id"] = category.id

            inventory_items_data = []
            for inv_request in inventory_requests:
                size = await self.size_repo.find_one_or_create(
                    {"value": inv_request.size_value, "region": inv_request.size_region},
                    category_id=category.id,
                )
                inventory_items_data.append(
                    {
                        "size_id": size.id,
                        "quantity": inv_request.quantity,
                        "purchase_price": inv_request.purchase_price,
                        "purchase_date": inv_request.purchase_date or datetime.now(timezone.utc),
                        "supplier": inv_request.supplier,
                        "status": "in_stock",
                    }
                )

            product = await self.product_repo.create_with_inventory(
                product_data, inventory_items_data
            )

            self.logger.info(
                "Created product with inventory",
                product_id=str(product.id),
                sku=product.sku,
                inventory_items=len(inventory_items_data),
            )

            return product.to_dict()

        except Exception as e:
            self.logger.error(
                "Failed to create product with inventory",
                sku=product_request.sku,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def update_inventory_status(
        self, inventory_id: UUID, new_status: str, notes: Optional[str] = None
    ) -> bool:
        """Update inventory item status with status history tracking (Phase 2)"""
        valid_statuses = [
            "in_stock",
            "listed_stockx",
            "listed_alias",
            "sold",
            "reserved",
            "error",
        ]
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status: {new_status}. Must be one of {valid_statuses}")

        # Get current item to track old status
        item = await self.inventory_repo.get_by_id(inventory_id)
        if not item:
            self.logger.warning(
                "Failed to update inventory status - item not found",
                inventory_id=str(inventory_id),
            )
            return False

        # Use model's helper method to add status change to history
        old_status = item.status
        item.add_status_change(old_status, new_status, notes)

        # Update the status
        success = await self.product_repo.update_inventory_status(inventory_id, new_status, notes)

        if success:
            self.logger.info(
                "Updated inventory status with history tracking",
                inventory_id=str(inventory_id),
                old_status=old_status,
                new_status=new_status,
            )
        return success

    async def update_item_status(self, item_id: UUID, status: str) -> bool:
        """Update inventory item status - alias for update_inventory_status with modern status names"""
        # Map modern status names to backend database status names
        status_mapping = {
            "in_stock": "in_stock",
            "listed": "listed_stockx",
            "sold": "sold",
            "presale": "in_stock",  # For presale, keep as in_stock until actually listed
            "preorder": "in_stock",  # For preorder, keep as in_stock until actually listed
            "listed_alias": "listed_alias",  # Alias listing
            "multi_platform": "listed_stockx",  # Listed on multiple platforms - default to stockx
            "reserved": "reserved",
            "error": "error",
        }

        mapped_status = status_mapping.get(status, status)
        return await self.update_inventory_status(item_id, mapped_status)

    async def update_item_fields(self, item_id: UUID, update_data: Dict[str, Any]) -> bool:
        """Update multiple fields of an inventory item"""
        try:
            # Handle status field with mapping if present
            if "status" in update_data:
                status = update_data["status"]
                status_mapping = {
                    "in_stock": "in_stock",
                    "listed": "listed_stockx",
                    "sold": "sold",
                    "presale": "presale",
                    "preorder": "preorder",
                    "canceled": "canceled",
                    "listed_alias": "listed_alias",
                }
                update_data["status"] = status_mapping.get(status, status)

            # Update the item using the inventory repository
            success = await self.inventory_repo.update(item_id, **update_data)

            if success:
                self.logger.info(
                    "Updated inventory item fields",
                    item_id=str(item_id),
                    fields=list(update_data.keys()),
                )
            else:
                self.logger.error("Failed to update inventory item fields", item_id=str(item_id))

            return success

        except Exception as e:
            self.logger.error(
                "Error updating inventory item fields", item_id=str(item_id), error=str(e)
            )
            return False

    async def get_multi_platform_items(self) -> List[Dict[str, Any]]:
        """Get items that could potentially be listed on multiple platforms"""
        try:
            # For demonstration, return items that are currently listed
            # In a real implementation, you'd track platform associations more explicitly
            items = await self.inventory_repo.get_all(filters={"status": "listed"})

            # Simulate multi-platform potential by checking if items have high value
            multi_platform_candidates = []
            for item in items:
                item_dict = item.to_dict()
                if item.purchase_price and item.purchase_price > 200:  # High-value items
                    item_dict["platforms"] = ["StockX"]  # Currently only on StockX
                    item_dict["potential_platforms"] = ["Alias", "GOAT"]  # Could be listed here
                    multi_platform_candidates.append(item_dict)

            return multi_platform_candidates

        except Exception as e:
            self.logger.error("Failed to get multi-platform items", error=str(e))
            return []

    async def get_low_stock_alert(self, threshold: int = 5) -> List[Dict[str, Any]]:
        """Get products with low stock levels"""
        low_stock_products = await self.product_repo.get_low_stock_products(threshold)
        self.logger.info(
            "Generated low stock alert",
            threshold=threshold,
            products_found=len(low_stock_products),
        )
        return low_stock_products

    async def search_products(
        self,
        search_term: Optional[str] = None,
        brand_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Search products with filters"""
        products = await self.product_repo.search(
            search_term=search_term,
            brand_filter=brand_filter,
            category_filter=category_filter,
            limit=limit,
            offset=offset,
        )
        return [p.to_dict() for p in products]

    async def get_product_details(self, product_id: UUID) -> Optional[Dict[str, Any]]:
        """Get detailed product information with inventory"""
        product = await self.product_repo.get_with_inventory(product_id)
        if not product:
            return None

        product_dict = product.to_dict()
        product_dict["inventory_items"] = [item.to_dict() for item in product.inventory_items]
        return product_dict

    async def sync_inventory_from_stockx(self, product_id: UUID) -> Dict[str, int]:
        """
        Synchronizes all inventory items for a given product with the variants from the StockX API.
        Performs an "upsert" logic: updates existing items, creates new ones.
        """
        self.logger.info(
            "Syncing inventory variants from StockX for product", product_id=str(product_id)
        )
        stats = {"created": 0, "updated": 0, "skipped": 0}

        # 1. Fetch our local product and all its current inventory items
        product = await self.product_repo.get_with_inventory(product_id)
        if not product:
            raise ValueError(f"Product with ID {product_id} not found.")

        if not product.sku:
            self.logger.warning(
                "Product has no SKU, cannot sync from StockX", product_id=str(product_id)
            )
            return stats

        # Create a map of existing items by their StockX variant ID for efficient lookup
        existing_items_map = {
            item.external_ids.get("stockx"): item
            for item in product.inventory_items
            if item.external_ids and "stockx" in item.external_ids
        }

        # 2. Fetch all variants for this product from the StockX API
        stockx_service = self.stockx_service
        if not stockx_service:
            from domains.integration.services.stockx_service import StockXService

            stockx_service = StockXService(self.db_session)

        stockx_variants = await stockx_service.get_all_product_variants(product.sku)

        if not stockx_variants:
            self.logger.info(
                "No variants found on StockX for product",
                product_id=str(product_id),
                sku=product.sku,
            )
            return stats

        # 3. Loop through StockX variants and perform upsert
        for variant in stockx_variants:
            variant_id = variant.get("variantId")
            if not variant_id:
                stats["skipped"] += 1
                continue

            # Check if we already have this item
            existing_item = existing_items_map.get(variant_id)

            if existing_item:
                # --- UPDATE ---
                # Here we would update any fields that might change.
                # For now, we just log it.
                self.logger.info(
                    "Updating existing inventory item from StockX variant",
                    item_id=str(existing_item.id),
                )
                # Example: existing_item.is_flex_eligible = variant.get('isFlexEligible')
                stats["updated"] += 1
            else:
                # --- CREATE ---
                self.logger.info(
                    "Creating new inventory item from StockX variant", variant_id=variant_id
                )

                # We need to find or create the Size object
                size_value = variant.get("variantValue", "Unknown")
                size = await self.size_repo.find_one_or_create(
                    {"value": size_value, "region": "US"},  # Assuming US region for StockX sizes
                    category_id=product.category_id,
                )

                new_item = InventoryItem(
                    product_id=product.id,
                    size_id=size.id,
                    quantity=0,  # New items from sync start with 0 quantity
                    status="in_stock",
                    external_ids={"stockx": variant_id},
                )
                self.db_session.add(new_item)
                stats["created"] += 1

        await self.db_session.commit()
        self.logger.info("Inventory sync from StockX complete", product_id=str(product_id), **stats)
        return stats

    async def get_items_paginated(
        self, skip: int = 0, limit: int = 100, filters: Optional[Dict[str, Any]] = None
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Get paginated inventory items with optional filters
        Returns (items, total_count)
        """
        import time

        try:
            # Performance monitoring: Track query execution time
            query_start = time.time()

            # Execute optimized database queries
            items = await self.inventory_repo.get_all_paginated(skip, limit, filters)
            query_time = (time.time() - query_start) * 1000

            count_start = time.time()
            total_count = await self.inventory_repo.count_all(filters)
            count_time = (time.time() - count_start) * 1000

            # Log query performance metrics
            self.logger.info(
                "Inventory pagination query performance",
                skip=skip,
                limit=limit,
                items_returned=len(items),
                total_count=total_count,
                query_time_ms=round(query_time, 2),
                count_time_ms=round(count_time, 2),
                total_time_ms=round(query_time + count_time, 2),
                filters=filters,
            )

            # Convert to dictionaries with related data
            transform_start = time.time()
            result_items = []
            for item in items:
                item_dict = item.to_dict()
                if item.product:
                    item_dict["product_name"] = item.product.name
                    item_dict["brand_name"] = (
                        item.product.brand.name if item.product.brand else "Unknown Brand"
                    )
                    item_dict["category_name"] = (
                        item.product.category.name if item.product.category else "Unknown Category"
                    )
                else:
                    item_dict["product_name"] = "Unknown Product"
                    item_dict["brand_name"] = "Unknown Brand"
                    item_dict["category_name"] = "Unknown Category"

                # Add size information
                if item.size:
                    item_dict["size_value"] = item.size.value
                else:
                    item_dict["size_value"] = "N/A"
                result_items.append(item_dict)

            transform_time = (time.time() - transform_start) * 1000

            # Log data transformation performance
            self.logger.debug(
                "Inventory data transformation performance",
                transform_time_ms=round(transform_time, 2),
                items_processed=len(result_items),
            )

            return result_items, total_count

        except Exception as e:
            self.logger.error("Failed to get paginated inventory items", error=str(e))
            raise

    async def get_detailed_summary(self) -> Dict[str, Any]:
        """
        Get high-level inventory statistics and summary
        """
        try:
            # Get basic stats
            stats = await self.get_inventory_overview()

            # Get additional summary data with error isolation
            # Each method uses isolated sessions and handles its own errors
            top_brands = await self._get_top_brands()
            status_breakdown = await self._get_status_breakdown()
            recent_activity = await self._get_recent_activity()

            return {
                "total_items": stats.total_items,
                "items_in_stock": stats.in_stock,
                "items_sold": stats.sold,
                "items_listed": stats.listed,
                "total_inventory_value": float(stats.total_value),
                "average_purchase_price": float(stats.avg_purchase_price),
                "top_brands": top_brands,
                "status_breakdown": status_breakdown,
                "recent_activity": recent_activity,
            }
        except Exception as e:
            self.logger.error("Failed to get inventory summary", error=str(e))
            # Return partial data instead of raising to ensure dashboard still loads
            return {
                "total_items": 0,
                "items_in_stock": 0,
                "items_sold": 0,
                "items_listed": 0,
                "total_inventory_value": 0.0,
                "average_purchase_price": 0.0,
                "top_brands": [],
                "status_breakdown": {},
                "recent_activity": [],
            }

    async def _get_top_brands(self) -> List[Dict[str, Any]]:
        """Get top brands by inventory count"""
        from sqlalchemy import text

        from shared.database.connection import get_db_session

        # Use isolated session to prevent transaction cascade failures
        async with get_db_session() as isolated_session:
            try:
                brands_query = text(
                    """
                    SELECT 
                        b.name as brand_name,
                        COUNT(i.id) as item_count,
                        SUM(i.quantity) as total_quantity,
                        AVG(i.purchase_price) as avg_price,
                        SUM(i.purchase_price * i.quantity) as total_value
                    FROM inventory.stock i
                    JOIN catalog.product p ON i.product_id = p.id
                    LEFT JOIN catalog.brand b ON p.brand_id = b.id
                    WHERE i.purchase_price IS NOT NULL
                    GROUP BY b.name
                    ORDER BY item_count DESC
                    LIMIT 5
                    """
                )

                result = await isolated_session.execute(brands_query)
                top_brands = []

                for row in result.fetchall():
                    brand = {
                        "name": row.brand_name or "Unknown Brand",
                        "item_count": int(row.item_count or 0),
                        "total_quantity": int(row.total_quantity or 0),
                        "avg_price": float(row.avg_price or 0),
                        "total_value": float(row.total_value or 0),
                    }
                    top_brands.append(brand)

                return top_brands

            except Exception as e:
                self.logger.error("Failed to get top brands", error=str(e), exc_info=True)
                await isolated_session.rollback()
                return []

    async def _get_status_breakdown(self) -> Dict[str, int]:
        """Get breakdown of items by status"""
        from sqlalchemy import text

        from shared.database.connection import get_db_session

        # Use isolated session to prevent transaction cascade failures
        async with get_db_session() as isolated_session:
            try:
                status_query = text(
                    """
                    SELECT 
                        status,
                        COUNT(*) as count
                    FROM inventory.stock
                    GROUP BY status
                    ORDER BY count DESC
                    """
                )

                result = await isolated_session.execute(status_query)
                status_breakdown = {}

                for row in result.fetchall():
                    status_breakdown[row.status] = int(row.count)

                return status_breakdown

            except Exception as e:
                self.logger.error("Failed to get status breakdown", error=str(e), exc_info=True)
                await isolated_session.rollback()
                return {}

    async def _get_recent_activity(self) -> List[Dict[str, Any]]:
        """Get recent inventory activity"""
        from sqlalchemy import text

        from shared.database.connection import get_db_session

        # Use isolated session to prevent transaction cascade failures
        async with get_db_session() as isolated_session:
            try:
                # Query for recent inventory updates
                recent_query = text(
                    """
                    SELECT 
                        i.updated_at,
                        i.status,
                        i.quantity,
                        i.purchase_price,
                        p.name as product_name,
                        b.name as brand_name,
                        s.value as size_value,
                        'status_change' as activity_type
                    FROM inventory.stock i
                    JOIN catalog.product p ON i.product_id = p.id
                    LEFT JOIN catalog.brand b ON p.brand_id = b.id
                    LEFT JOIN core.sizes s ON i.size_id = s.id
                    WHERE i.updated_at > CURRENT_TIMESTAMP - INTERVAL '30 days'
                    ORDER BY i.updated_at DESC
                    LIMIT 10
                    """
                )

                result = await isolated_session.execute(recent_query)
                recent_activity = []

                for row in result.fetchall():
                    activity = {
                        "date": row.updated_at.isoformat() if row.updated_at else None,
                        "activity_type": row.activity_type,
                        "product_name": row.product_name or "Unknown Product",
                        "brand_name": row.brand_name or "Unknown Brand",
                        "size": row.size_value or "N/A",
                        "status": row.status or "unknown",
                        "quantity": int(row.quantity or 0),
                        "purchase_price": float(row.purchase_price or 0),
                        "description": self._format_activity_description(row),
                    }
                    recent_activity.append(activity)

                return recent_activity

            except Exception as e:
                self.logger.error(
                    "Failed to get recent inventory activity", error=str(e), exc_info=True
                )
                await isolated_session.rollback()
                return []

    def _format_activity_description(self, row) -> str:
        """Format activity description based on the row data"""
        if row.status == "listed":
            return f"Listed {row.product_name} (Size {row.size_value}) on marketplace"
        elif row.status == "sold":
            return f"Sold {row.product_name} (Size {row.size_value})"
        elif row.status == "in_stock":
            return f"Added {row.product_name} (Size {row.size_value}) to inventory"
        else:
            return f"Status updated to {row.status}"

    async def get_item_detailed(self, item_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get detailed inventory item by ID with all related data
        """
        try:
            item = await self.inventory_repo.get_by_id_with_related(
                item_id, related=["product", "product.brand", "product.category", "size"]
            )

            if not item:
                return None

            item_dict = item.to_dict()
            if item.product:
                item_dict["product_name"] = item.product.name
                item_dict["brand_name"] = item.product.brand.name if item.product.brand else None
                item_dict["category_name"] = (
                    item.product.category.name if item.product.category else None
                )
            else:
                item_dict["product_name"] = "Unknown"
                item_dict["brand_name"] = None
                item_dict["category_name"] = "Unknown"

            return item_dict

        except Exception as e:
            self.logger.error("Failed to get item details", item_id=str(item_id), error=str(e))
            raise

    async def sync_item_from_stockx(self, item_id: UUID) -> Dict[str, Any]:
        """
        Sync single inventory item from StockX
        """
        try:
            item = await self.get_item_detailed(item_id)
            if not item:
                raise ValueError(f"Inventory item with ID {item_id} not found")

            # Placeholder implementation for now
            self.logger.info("Syncing item from StockX", item_id=str(item_id))
            return {"status": "synced", "item_id": str(item_id)}

        except Exception as e:
            self.logger.error("Failed to sync item from StockX", item_id=str(item_id), error=str(e))
            raise

    async def detect_duplicate_listings(
        self, listing_data: Dict[str, Any]
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Comprehensive duplicate detection for StockX listings
        Returns (has_duplicates, list_of_duplicate_items)
        """
        listing_id = listing_data.get("listingId")
        product_info = listing_data.get("product", {})
        variant_info = listing_data.get("variant", {})

        product_name = product_info.get("productName", "")
        size = variant_info.get("variantValue", "")
        brand_name = listing_data.get("brand", "")

        potential_duplicates = []

        # Check 1: Exact StockX listing ID match
        existing_by_listing_id = await self._find_by_stockx_listing_id(listing_id)
        if existing_by_listing_id:
            potential_duplicates.append(
                {
                    "item": existing_by_listing_id,
                    "match_type": "exact_listing_id",
                    "confidence": 1.0,
                }
            )
            return True, potential_duplicates

        # Check 2: Product name + size combination
        similar_by_name_size = await self._find_similar_by_name_size(product_name, size, brand_name)
        for item in similar_by_name_size:
            potential_duplicates.append(
                {"item": item, "match_type": "name_size_match", "confidence": 0.9}
            )

        # Check 3: SKU-based matching (if StockX product ID exists)
        stockx_product_id = product_info.get("productId")
        if stockx_product_id:
            similar_by_sku = await self._find_by_stockx_product_id(stockx_product_id, size)
            for item in similar_by_sku:
                if item not in [d["item"] for d in potential_duplicates]:
                    potential_duplicates.append(
                        {"item": item, "match_type": "product_id_match", "confidence": 0.8}
                    )

        # Check 4: Fuzzy text matching for product names
        fuzzy_matches = await self._fuzzy_match_products(product_name, size, brand_name)
        for item, similarity_score in fuzzy_matches:
            if item not in [d["item"] for d in potential_duplicates] and similarity_score > 0.85:
                potential_duplicates.append(
                    {"item": item, "match_type": "fuzzy_name_match", "confidence": similarity_score}
                )

        return len(potential_duplicates) > 0, potential_duplicates

    async def _find_by_stockx_listing_id(self, listing_id: str) -> Optional[Any]:
        """Find inventory item by exact StockX listing ID"""
        try:
            from shared.database.models import InventoryItem

            stmt = select(InventoryItem).where(
                and_(
                    InventoryItem.external_ids.is_not(None),
                    InventoryItem.external_ids["stockx_listing_id"].astext == listing_id,
                )
            )
            result = await self.db_session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            self.logger.error(f"Error finding item by listing ID: {e}")
            return None

    async def _find_similar_by_name_size(
        self, product_name: str, size: str, brand_name: str
    ) -> List[Any]:
        """Find items with similar product name and exact size match"""
        try:
            from shared.database.models import Brand, InventoryItem, Product, Size

            # Normalize product name for comparison
            normalized_name = product_name.lower().strip()

            stmt = (
                select(InventoryItem)
                .join(Product)
                .join(Brand, isouter=True)
                .join(Size, isouter=True)
                .where(
                    and_(
                        func.lower(Product.name).like(f"%{normalized_name}%"),
                        or_(
                            and_(Size.value.is_not(None), Size.value == size),
                            and_(Size.value.is_(None), size in [None, "", "Unknown Size"]),
                        ),
                        or_(
                            and_(Brand.name.is_not(None), Brand.name.ilike(f"%{brand_name}%")),
                            brand_name == "",  # Handle cases where brand is not specified
                        ),
                    )
                )
            )
            result = await self.db_session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Error finding similar items by name/size: {e}")
            return []

    async def _find_by_stockx_product_id(self, product_id: str, size: str) -> List[Any]:
        """Find items by StockX product ID and size"""
        try:
            from shared.database.models import InventoryItem, Size

            stmt = (
                select(InventoryItem)
                .join(Size, isouter=True)
                .where(
                    and_(
                        InventoryItem.external_ids.is_not(None),
                        InventoryItem.external_ids["stockx_product_id"].astext == product_id,
                        or_(
                            and_(Size.value.is_not(None), Size.value == size),
                            and_(Size.value.is_(None), size in [None, "", "Unknown Size"]),
                        ),
                    )
                )
            )
            result = await self.db_session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Error finding items by product ID: {e}")
            return []

    async def _fuzzy_match_products(
        self, product_name: str, size: str, brand_name: str
    ) -> List[Tuple[Any, float]]:
        """Perform fuzzy text matching on product names"""
        try:
            from shared.database.models import Brand, InventoryItem, Product, Size

            # Get all inventory items with the same size and similar brand
            stmt = (
                select(InventoryItem, Product, Brand)
                .join(Product)
                .join(Brand, isouter=True)
                .join(Size, isouter=True)
                .where(
                    and_(
                        or_(
                            and_(Size.value.is_not(None), Size.value == size),
                            and_(Size.value.is_(None), size in [None, "", "Unknown Size"]),
                        ),
                        or_(
                            and_(Brand.name.is_not(None), Brand.name.ilike(f"%{brand_name}%")),
                            brand_name == "",
                        ),
                    )
                )
            )
            result = await self.db_session.execute(stmt)
            items_with_details = result.all()

            fuzzy_matches = []
            for item, product, brand in items_with_details:
                if product and product.name:
                    similarity = self._calculate_text_similarity(
                        product_name.lower(), product.name.lower()
                    )
                    if similarity > 0.7:  # Only include reasonably similar items
                        fuzzy_matches.append((item, similarity))

            # Sort by similarity descending
            fuzzy_matches.sort(key=lambda x: x[1], reverse=True)
            return fuzzy_matches[:5]  # Return top 5 matches

        except Exception as e:
            self.logger.error(f"Error in fuzzy matching: {e}")
            return []

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using Jaccard similarity of word sets"""
        try:
            # Simple tokenization and normalization
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())

            # Remove common stop words that don't help with matching
            stop_words = {
                "the",
                "and",
                "or",
                "but",
                "in",
                "on",
                "at",
                "to",
                "for",
                "of",
                "with",
                "by",
            }
            words1 = words1 - stop_words
            words2 = words2 - stop_words

            # Jaccard similarity
            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))

            if union == 0:
                return 0.0

            return intersection / union
        except Exception:
            return 0.0

    async def merge_duplicate_inventory_items(
        self, primary_item_id: UUID, duplicate_item_ids: List[UUID]
    ) -> Dict[str, Any]:
        """
        Merge duplicate inventory items into a primary item
        """
        try:
            from shared.database.models import InventoryItem

            # Get primary item
            primary_item = await self.db_session.get(InventoryItem, primary_item_id)
            if not primary_item:
                raise ValueError(f"Primary item {primary_item_id} not found")

            merge_stats = {
                "primary_item_id": str(primary_item_id),
                "merged_items": 0,
                "total_quantity_added": 0,
                "external_ids_merged": 0,
            }

            # PERFORMANCE OPTIMIZATION: Batch load all duplicate items at once
            from sqlalchemy import select

            duplicate_items_result = await self.db_session.execute(
                select(InventoryItem).where(InventoryItem.id.in_(duplicate_item_ids))
            )
            duplicate_items = duplicate_items_result.scalars().all()

            # Process merging in memory first
            items_to_delete = []
            for duplicate_item in duplicate_items:
                # Merge quantity
                if duplicate_item.quantity:
                    primary_item.quantity = (primary_item.quantity or 0) + duplicate_item.quantity
                    merge_stats["total_quantity_added"] += duplicate_item.quantity

                # Merge external IDs
                if duplicate_item.external_ids:
                    if not primary_item.external_ids:
                        primary_item.external_ids = {}
                    primary_item.external_ids.update(duplicate_item.external_ids)
                    merge_stats["external_ids_merged"] += len(duplicate_item.external_ids)

                # Keep the earliest purchase date
                if duplicate_item.purchase_date and (
                    not primary_item.purchase_date
                    or duplicate_item.purchase_date < primary_item.purchase_date
                ):
                    primary_item.purchase_date = duplicate_item.purchase_date

                # Keep the lowest purchase price (assuming it's more accurate)
                if duplicate_item.purchase_price and (
                    not primary_item.purchase_price
                    or duplicate_item.purchase_price < primary_item.purchase_price
                ):
                    primary_item.purchase_price = duplicate_item.purchase_price

                items_to_delete.append(duplicate_item.id)
                merge_stats["merged_items"] += 1

            # PERFORMANCE OPTIMIZATION: Bulk delete all duplicates in one query
            if items_to_delete:
                await self.db_session.execute(
                    InventoryItem.__table__.delete().where(InventoryItem.id.in_(items_to_delete))
                )

            await self.db_session.commit()

            self.logger.info(
                "Successfully merged duplicate inventory items",
                primary_item_id=str(primary_item_id),
                merged_count=merge_stats["merged_items"],
            )

            return merge_stats

        except Exception as e:
            await self.db_session.rollback()
            self.logger.error(f"Failed to merge duplicate items: {e}")
            raise

    async def run_duplicate_detection_scan(self) -> Dict[str, Any]:
        """
        Run a comprehensive scan for duplicate inventory items across the entire inventory
        """
        self.logger.info("Starting comprehensive duplicate detection scan")

        scan_results = {
            "total_items_scanned": 0,
            "duplicate_groups_found": 0,
            "total_duplicates": 0,
            "auto_merged": 0,
            "require_manual_review": 0,
            "duplicate_groups": [],
        }

        try:
            # Get all inventory items with related data
            from sqlalchemy.orm import selectinload

            from shared.database.models import InventoryItem, Product

            stmt = select(InventoryItem).options(
                # Include related objects for comparison
                selectinload(InventoryItem.product).selectinload(Product.brand),
                selectinload(InventoryItem.product).selectinload(Product.category),
                selectinload(InventoryItem.size),
            )
            result = await self.db_session.execute(stmt)
            all_items = result.scalars().all()

            scan_results["total_items_scanned"] = len(all_items)

            # Group items by potential duplicate criteria
            processed_items = set()

            for item in all_items:
                if item.id in processed_items:
                    continue

                # Find all potential duplicates for this item
                duplicates = await self._find_all_duplicates_for_item(item, all_items)

                if duplicates:
                    duplicate_group = {
                        "primary_item_id": str(item.id),
                        "duplicates": [
                            {"item_id": str(dup.id), "confidence": 0.9} for dup in duplicates
                        ],
                        "can_auto_merge": self._can_auto_merge_group([item] + duplicates),
                    }

                    scan_results["duplicate_groups"].append(duplicate_group)
                    scan_results["duplicate_groups_found"] += 1
                    scan_results["total_duplicates"] += len(duplicates)

                    if duplicate_group["can_auto_merge"]:
                        scan_results["auto_merged"] += 1
                    else:
                        scan_results["require_manual_review"] += 1

                    # Mark all items in this group as processed
                    processed_items.add(item.id)
                    for dup in duplicates:
                        processed_items.add(dup.id)

            self.logger.info("Duplicate detection scan completed", results=scan_results)
            return scan_results

        except Exception as e:
            self.logger.error(f"Failed to run duplicate detection scan: {e}")
            return {"error": str(e)}

    async def _find_all_duplicates_for_item(self, item: Any, all_items: List[Any]) -> List[Any]:
        """Find all duplicate items for a given inventory item"""
        duplicates = []

        if not item.product:
            return duplicates

        item_name = item.product.name.lower() if item.product.name else ""
        item_size = item.size.value if item.size else ""
        item_brand = item.product.brand.name.lower() if item.product.brand else ""

        for other_item in all_items:
            if other_item.id == item.id or not other_item.product:
                continue

            other_name = other_item.product.name.lower() if other_item.product.name else ""
            other_size = other_item.size.value if other_item.size else ""
            other_brand = other_item.product.brand.name.lower() if other_item.product.brand else ""

            # Check for exact matches
            if item_name == other_name and item_size == other_size and item_brand == other_brand:
                duplicates.append(other_item)
                continue

            # Check for high similarity matches
            name_similarity = self._calculate_text_similarity(item_name, other_name)
            if name_similarity > 0.9 and item_size == other_size and item_brand == other_brand:
                duplicates.append(other_item)

        return duplicates

    def _can_auto_merge_group(self, items: List[Any]) -> bool:
        """Determine if a group of duplicate items can be automatically merged"""
        try:
            # Auto-merge if all items have the same status and no conflicting external IDs
            statuses = {item.status for item in items if item.status}
            if len(statuses) > 1:
                return False  # Different statuses require manual review

            # Check for conflicting external listing IDs
            all_external_ids = {}
            for item in items:
                if item.external_ids:
                    for key, value in item.external_ids.items():
                        if key in all_external_ids and all_external_ids[key] != value:
                            return False  # Conflicting external IDs
                        all_external_ids[key] = value

            return True

        except Exception as e:
            self.logger.error(f"Error determining auto-merge eligibility: {e}")
            return False

    async def _get_or_create_stockx_platform(self) -> Platform:
        """Get or create the StockX platform entry"""
        result = await self.db_session.execute(select(Platform).where(Platform.slug == "stockx"))
        platform = result.scalar_one_or_none()

        if not platform:
            platform = Platform(
                name="StockX",
                slug="stockx",
                fee_percentage=10.0,  # StockX typical 10% seller fee
                supports_fees=True,
                active=True,
            )
            self.db_session.add(platform)
            await self.db_session.flush()

        return platform

    async def _create_or_update_marketplace_data(
        self, inventory_item: InventoryItem, listing: dict, platform: Platform
    ):
        """Create or update marketplace data for the inventory item"""
        try:
            # Check if marketplace data already exists for this item and platform
            existing_result = await self.db_session.execute(
                select(MarketplaceData).where(
                    and_(
                        MarketplaceData.inventory_item_id == inventory_item.id,
                        MarketplaceData.platform_id == platform.id,
                    )
                )
            )
            existing_data = existing_result.scalar_one_or_none()

            # Extract pricing data from listing
            ask_info = listing.get("ask", {})

            # Get the ask price - this is our listing price
            ask_price = listing.get("amount")
            if ask_price:
                ask_price = Decimal(str(ask_price))

            # Create platform-specific data
            platform_specific = {
                "askId": ask_info.get("askId"),
                "variantId": listing.get("variant", {}).get("variantId"),
                "authentication": "required",  # StockX always requires authentication
                "condition_grade": "new",  # StockX typically deals with new items
                "processing_time_days": 3,  # Typical StockX processing time
                "currency_code": listing.get("currencyCode", "EUR"),
                "listing_status": listing.get("status", "ACTIVE"),
            }

            if existing_data:
                # Update existing marketplace data
                existing_data.marketplace_listing_id = listing.get("listingId")
                existing_data.ask_price = ask_price
                existing_data.fees_percentage = Decimal("0.095")  # StockX typically charges 9.5%
                existing_data.platform_specific = platform_specific
                # Keep updated_at as automatic

                self.logger.debug(
                    "Updated marketplace data",
                    inventory_item_id=str(inventory_item.id),
                    platform=platform.slug,
                    ask_price=float(ask_price) if ask_price else None,
                )
            else:
                # Create new marketplace data
                marketplace_data = MarketplaceData(
                    inventory_item_id=inventory_item.id,
                    platform_id=platform.id,
                    marketplace_listing_id=listing.get("listingId"),
                    ask_price=ask_price,
                    fees_percentage=Decimal("0.095"),  # StockX typically charges 9.5%
                    platform_specific=platform_specific,
                )

                self.db_session.add(marketplace_data)

                self.logger.debug(
                    "Created marketplace data",
                    inventory_item_id=str(inventory_item.id),
                    platform=platform.slug,
                    ask_price=float(ask_price) if ask_price else None,
                )

        except Exception as e:
            self.logger.error(
                "Failed to create/update marketplace data",
                inventory_item_id=str(inventory_item.id),
                platform=platform.slug,
                error=str(e),
            )

    async def enrich_inventory_items_batch(
        self,
        filters: Optional[Dict[str, Any]] = None,
        batch_size: int = 50,
        enrich_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Batch enrich inventory items with missing metadata

        Args:
            filters: Optional filters (e.g., {"missing_brand": True, "missing_size": True})
            batch_size: Number of items to process in one batch
            enrich_types: List of enrichment types to apply (e.g., ["brand", "size"])

        Returns:
            Statistics about the enrichment operation
        """
        from domains.products.services.brand_service import BrandExtractorService

        self.logger.info(
            "Starting batch enrichment",
            filters=filters,
            batch_size=batch_size,
            enrich_types=enrich_types,
        )

        stats = {
            "processed": 0,
            "brands_enriched": 0,
            "sizes_enriched": 0,
            "skipped": 0,
            "errors": 0,
        }

        try:
            # Import Size model
            from shared.database.models import Size

            # Build query with filters
            query = (
                select(InventoryItem)
                .join(Product, InventoryItem.product_id == Product.id)
                .join(Brand, Product.brand_id == Brand.id, isouter=True)
                .join(Size, InventoryItem.size_id == Size.id, isouter=True)
            )

            # Apply filters
            conditions = []
            if filters:
                if filters.get("missing_brand"):
                    conditions.append(Brand.name == "Unknown Brand")
                if filters.get("missing_size"):
                    conditions.append(or_(Size.value.is_(None), Size.value == ""))
                if filters.get("status"):
                    conditions.append(InventoryItem.status == filters["status"])

            if conditions:
                query = query.where(and_(*conditions))

            # Limit batch size
            query = query.limit(batch_size)

            result = await self.db_session.execute(query)
            items = result.scalars().all()

            self.logger.info(f"Found {len(items)} items to enrich")

            if not items:
                return stats

            # Initialize brand extractor
            brand_extractor = BrandExtractorService(self.db_session)

            # Get StockX listings for size data
            stockx_listings = {}
            if not enrich_types or "size" in enrich_types:
                try:
                    stockx_service = self.stockx_service
                    if not stockx_service:
                        from domains.integration.services.stockx_service import StockXService

                        stockx_service = StockXService(self.db_session)

                    all_listings = await stockx_service.get_all_listings()
                    # Index by listing_id for fast lookup
                    for listing in all_listings:
                        listing_id = listing.get("listingId")
                        if listing_id:
                            stockx_listings[listing_id] = listing

                    self.logger.info(
                        f"Loaded {len(stockx_listings)} StockX listings for size matching"
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to load StockX listings: {e}")

            # Process each item
            for item in items:
                try:
                    stats["processed"] += 1
                    enriched = False

                    # Load relationships
                    await self.db_session.refresh(item, ["product"])
                    product = item.product

                    # Enrich brand
                    # TODO: Known issue - SQLAlchemy "SQL expression element or literal value expected" error
                    # occurs intermittently during brand enrichment. Requires further investigation.
                    if not enrich_types or "brand" in enrich_types:
                        # Get the "Unknown Brand" ID for comparison
                        unknown_brand_result = await self.db_session.execute(
                            select(Brand.id).where(Brand.name == "Unknown Brand")
                        )
                        unknown_brand_id = unknown_brand_result.scalar_one_or_none()

                        # Check if product currently has "Unknown Brand"
                        if unknown_brand_id and product.brand_id == unknown_brand_id:
                            # Extract brand from product name
                            brand_name = await brand_extractor.extract_brand_from_name(product.name)

                            if brand_name and brand_name != "Unknown Brand":
                                # Find or create brand
                                brand_result = await self.db_session.execute(
                                    select(Brand).where(Brand.name == brand_name)
                                )
                                brand = brand_result.scalar_one_or_none()

                                if not brand:
                                    # Create new brand
                                    from shared.utils.slugify import slugify

                                    brand = Brand(name=brand_name, slug=slugify(brand_name))
                                    self.db_session.add(brand)
                                    await self.db_session.flush()

                                # Clear any cached brand relationship before updating
                                if "brand" in product.__dict__:
                                    delattr(product, "brand")

                                # Update product brand_id
                                product.brand_id = brand.id
                                stats["brands_enriched"] += 1
                                enriched = True

                                self.logger.debug(
                                    "Enriched brand",
                                    item_id=str(item.id),
                                    product_name=product.name,
                                    brand=brand_name,
                                )

                    # Enrich size
                    if not enrich_types or "size" in enrich_types:
                        # Check if item has size by querying directly
                        current_size = None
                        if item.size_id:
                            current_size_result = await self.db_session.execute(
                                select(Size).where(Size.id == item.size_id)
                            )
                            current_size = current_size_result.scalar_one_or_none()

                        if not current_size or not current_size.value:
                            # Try to get size from StockX listing
                            stockx_listing_id = None
                            if item.external_ids:
                                stockx_listing_id = item.external_ids.get("stockx_listing_id")

                            if stockx_listing_id and stockx_listing_id in stockx_listings:
                                listing = stockx_listings[stockx_listing_id]
                                variant = listing.get("variant", {})
                                size_value = variant.get("variantValue") or listing.get("size")

                                if size_value:
                                    # Find or create Size record
                                    size_result = await self.db_session.execute(
                                        select(Size).where(
                                            and_(
                                                Size.value == str(size_value),
                                                Size.category_id == product.category_id,
                                            )
                                        )
                                    )
                                    size = size_result.scalar_one_or_none()

                                    if not size:
                                        # Create new size
                                        size = Size(
                                            value=str(size_value),
                                            category_id=product.category_id,
                                            region="US",  # Default to US region
                                        )
                                        self.db_session.add(size)
                                        await self.db_session.flush()

                                    # Update item size_id directly (avoid relationship confusion)
                                    item.size_id = size.id
                                    stats["sizes_enriched"] += 1
                                    enriched = True

                                    self.logger.debug(
                                        "Enriched size",
                                        item_id=str(item.id),
                                        size=size_value,
                                    )

                    if not enriched:
                        stats["skipped"] += 1

                except Exception as e:
                    stats["errors"] += 1
                    self.logger.error(
                        "Failed to enrich item",
                        item_id=str(item.id) if item else None,
                        error=str(e),
                    )

            # Commit all changes
            await self.db_session.commit()

            self.logger.info(
                "Batch enrichment completed",
                stats=stats,
            )

            return stats

        except Exception as e:
            await self.db_session.rollback()
            self.logger.error(
                "Batch enrichment failed",
                error=str(e),
                exc_info=True,
            )
            raise

    async def reserve_inventory_stock(
        self, item_id: UUID, quantity: int, reason: Optional[str] = None
    ) -> bool:
        """
        Reserve stock for an order or listing (Phase 2)

        Args:
            item_id: Inventory item UUID
            quantity: Quantity to reserve
            reason: Optional reason for reservation

        Returns:
            True if reservation successful, False otherwise
        """
        try:
            success = await self.inventory_repo.reserve_stock(item_id, quantity, reason)

            if success:
                self.logger.info(
                    "Reserved inventory stock",
                    item_id=str(item_id),
                    quantity=quantity,
                    reason=reason,
                )
            else:
                self.logger.warning(
                    "Failed to reserve stock - insufficient available quantity",
                    item_id=str(item_id),
                    requested_quantity=quantity,
                )

            return success
        except Exception as e:
            self.logger.error(
                "Error reserving inventory stock",
                item_id=str(item_id),
                quantity=quantity,
                error=str(e),
            )
            return False

    async def release_inventory_reservation(
        self, item_id: UUID, quantity: int, reason: Optional[str] = None
    ) -> bool:
        """
        Release reserved stock (Phase 2)

        Args:
            item_id: Inventory item UUID
            quantity: Quantity to release
            reason: Optional reason for release

        Returns:
            True if release successful, False otherwise
        """
        try:
            success = await self.inventory_repo.release_reservation(item_id, quantity, reason)

            if success:
                self.logger.info(
                    "Released inventory reservation",
                    item_id=str(item_id),
                    quantity=quantity,
                    reason=reason,
                )
            else:
                self.logger.warning(
                    "Failed to release reservation",
                    item_id=str(item_id),
                    quantity=quantity,
                )

            return success
        except Exception as e:
            self.logger.error(
                "Error releasing inventory reservation",
                item_id=str(item_id),
                quantity=quantity,
                error=str(e),
            )
            return False

    async def get_stock_metrics_summary(self) -> Dict[str, Any]:
        """
        Get stock metrics from materialized view (Phase 2)

        Returns:
            Dictionary with stock metrics including available quantities
        """
        try:
            metrics = await self.inventory_repo.get_stock_metrics()

            self.logger.info(
                "Retrieved stock metrics",
                total_metrics=len(metrics),
            )

            # Convert to dict format
            return {
                "metrics": [
                    {
                        "product_id": str(m.product_id),
                        "product_name": m.product_name,
                        "total_quantity": m.total_quantity,
                        "reserved_quantity": m.reserved_quantity,
                        "available_quantity": m.available_quantity,
                        "total_value": float(m.total_value) if m.total_value else 0.0,
                        "status_distribution": m.status_distribution,
                    }
                    for m in metrics
                ],
                "total_products": len(metrics),
            }
        except Exception as e:
            self.logger.error("Failed to get stock metrics", error=str(e))
            return {"metrics": [], "total_products": 0, "error": str(e)}

    async def get_low_stock_items_with_reservations(
        self, threshold: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get items with low available stock (Phase 2 - considers reservations)

        Args:
            threshold: Minimum available quantity threshold

        Returns:
            List of items with low available stock
        """
        try:
            items = await self.inventory_repo.get_low_stock_items_with_reservations(threshold)

            self.logger.info(
                "Retrieved low stock items with reservations",
                threshold=threshold,
                items_found=len(items),
            )

            return [item.to_dict() for item in items]
        except Exception as e:
            self.logger.error(
                "Failed to get low stock items with reservations",
                threshold=threshold,
                error=str(e),
            )
            return []

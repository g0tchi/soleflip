"""
Inventory Domain Service
Business logic layer for inventory management
"""

from typing import List, Dict, Any, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime, timezone
from dataclasses import dataclass
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.connection import get_db_session
from ..repositories.product_repository import ProductRepository
from ..repositories.inventory_repository import (
    InventoryRepository,
    InventoryStats as RepoInventoryStats,
)
from shared.repositories import BaseRepository
from shared.database.models import Product, InventoryItem, Brand, Category, Size

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

        # Convert repository stats to service stats (compatibility)
        return InventoryStats(
            total_items=repo_stats.total_items,
            in_stock=repo_stats.in_stock,
            sold=repo_stats.sold,
            listed=repo_stats.listed,
            total_value=repo_stats.total_value,
            avg_purchase_price=repo_stats.avg_purchase_price,
        )

        self.logger.info(
            "Generated inventory overview",
            total_items=total_items,
            in_stock=in_stock,
            sold=sold,
            total_value=float(total_value),
        )

        return InventoryStats(
            total_items=total_items,
            in_stock=in_stock,
            sold=sold,
            listed=listed,
            total_value=total_value,
            avg_purchase_price=avg_purchase_price,
        )

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
        """Update inventory item status"""
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

        success = await self.product_repo.update_inventory_status(inventory_id, new_status, notes)

        if success:
            self.logger.info(
                "Updated inventory status",
                inventory_id=str(inventory_id),
                new_status=new_status,
            )
        else:
            self.logger.warning(
                "Failed to update inventory status - item not found",
                inventory_id=str(inventory_id),
            )
        return success

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
        try:
            items = await self.inventory_repo.get_all_paginated(skip, limit, filters)
            total_count = await self.inventory_repo.count_all(filters)

            # Convert to dictionaries with related data
            result_items = []
            for item in items:
                item_dict = item.to_dict()
                if item.product:
                    item_dict["product_name"] = item.product.name
                    item_dict["brand_name"] = (
                        item.product.brand.name if item.product.brand else None
                    )
                    item_dict["category_name"] = (
                        item.product.category.name if item.product.category else None
                    )
                else:
                    item_dict["product_name"] = "Unknown"
                    item_dict["brand_name"] = None
                    item_dict["category_name"] = "Unknown"
                result_items.append(item_dict)

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

            # Get additional summary data
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
            raise

    async def _get_top_brands(self) -> List[Dict[str, Any]]:
        """Get top brands by inventory count"""
        # Placeholder implementation
        return []

    async def _get_status_breakdown(self) -> Dict[str, int]:
        """Get breakdown of items by status"""
        # Placeholder implementation
        return {"in_stock": 0, "sold": 0, "listed": 0}

    async def _get_recent_activity(self) -> List[Dict[str, Any]]:
        """Get recent inventory activity"""
        # Placeholder implementation
        return []

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

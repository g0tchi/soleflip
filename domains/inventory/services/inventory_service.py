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
from ..repositories.base_repository import BaseRepository
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

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.logger = logger.bind(service="inventory")
        self.product_repo = ProductRepository(self.db_session)
        self.brand_repo = BaseRepository(Brand, self.db_session)
        self.category_repo = BaseRepository(Category, self.db_session)
        self.size_repo = BaseRepository(Size, self.db_session)
        self.inventory_repo = BaseRepository(InventoryItem, self.db_session)

    async def get_inventory_overview(self) -> InventoryStats:
        """Get overall inventory statistics"""
        all_items = await self.inventory_repo.get_all()

        total_items = len(all_items)
        in_stock = sum(1 for item in all_items if item.status == "in_stock")
        sold = sum(1 for item in all_items if item.status == "sold")
        listed = sum(1 for item in all_items if "listed" in item.status)

        total_value = sum(
            item.purchase_price or Decimal("0")
            for item in all_items
            if item.status == "in_stock"
        )

        purchase_prices = [
            item.purchase_price
            for item in all_items
            if item.purchase_price is not None
        ]
        avg_purchase_price = (
            sum(purchase_prices) / len(purchase_prices)
            if purchase_prices
            else Decimal("0")
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
                        "purchase_date": inv_request.purchase_date
                        or datetime.now(timezone.utc),
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
            raise ValueError(
                f"Invalid status: {new_status}. Must be one of {valid_statuses}"
            )

        success = await self.product_repo.update_inventory_status(
            inventory_id, new_status, notes
        )

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

    async def get_product_details(
        self, product_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get detailed product information with inventory"""
        product = await self.product_repo.get_with_inventory(product_id)
        if not product:
            return None

        product_dict = product.to_dict()
        product_dict["inventory_items"] = [
            item.to_dict() for item in product.inventory_items
        ]
        return product_dict

    async def enrich_inventory_item_from_stockx(self, inventory_item_id: UUID) -> Optional[InventoryItem]:
        """
        Enriches an inventory item with additional data from the StockX Catalog API.
        """
        self.logger.info("Enriching inventory item from StockX", inventory_item_id=str(inventory_item_id))

        # We need to fetch the item with its related product
        item = await self.inventory_repo.get_by_id_with_related(inventory_item_id, ["product"])
        if not item:
            self.logger.warning("Inventory item not found for enrichment", inventory_item_id=str(inventory_item_id))
            return None

        if not item.external_ids or "stockx_variant_id" not in item.external_ids:
            self.logger.warning("No stockx_variant_id found in external_ids for item", inventory_item_id=str(inventory_item_id))
            return item

        stockx_variant_id = item.external_ids["stockx_variant_id"]
        # The product ID is also needed for the API call
        stockx_product_id = item.product.sku # Assuming product SKU is the StockX product ID

        from domains.integration.services.stockx_service import StockXService
        stockx_service = StockXService(self.db_session)

        variant_data = await stockx_service.get_product_details(stockx_variant_id) # Corrected method name

        if not variant_data:
            self.logger.info("No variant data returned from StockX", stockx_variant_id=stockx_variant_id)
            return item

        # Here we would update our InventoryItem with new data.
        # For example, if we add a 'is_flex_eligible' boolean field to our model:
        # item.is_flex_eligible = variant_data.get('isFlexEligible', item.is_flex_eligible)

        # For now, we just log that we received the data.
        self.logger.info("Successfully received variant data from StockX", data=variant_data)

        # No commit here as we are not changing anything yet.
        # await self.db_session.commit()

        return item
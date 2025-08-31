"""
Product Repository - Clean Data Access Layer
Replaces direct SQL queries with maintainable repository pattern
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.database.models import Brand, Category, InventoryItem, Product, Size

from .base_repository import BaseRepository


class ProductRepository(BaseRepository[Product]):
    """Repository for product-related data operations"""

    def __init__(self, db_session: AsyncSession):
        super().__init__(Product, db_session)

    async def find_by_sku(self, sku: str) -> Optional[Product]:
        """Find product by SKU"""
        query = select(Product).where(Product.sku == sku)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def find_by_brand(self, brand_name: str) -> List[Product]:
        """Find all products by brand name"""
        query = (
            select(Product)
            .join(Brand)
            .where(Brand.name.ilike(f"%{brand_name}%"))
            .options(selectinload(Product.brand))
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def find_by_category(self, category_path: str) -> List[Product]:
        """Find products by category path (hierarchical)"""
        query = (
            select(Product)
            .join(Category)
            .where(Category.path.op("<@")(category_path))
            .options(selectinload(Product.category))
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def search(
        self,
        search_term: str,
        brand_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Product]:
        """Full-text search across products"""
        query = select(Product).options(selectinload(Product.brand), selectinload(Product.category))

        # Build search conditions
        conditions = []

        # Text search in name and description
        if search_term:
            text_search = or_(
                Product.name.ilike(f"%{search_term}%"),
                Product.description.ilike(f"%{search_term}%"),
                Product.sku.ilike(f"%{search_term}%"),
            )
            conditions.append(text_search)

        # Brand filter
        if brand_filter:
            brand_condition = select(Brand.id).where(Brand.name.ilike(f"%{brand_filter}%"))
            conditions.append(Product.brand_id.in_(brand_condition))

        # Category filter
        if category_filter:
            category_condition = select(Category.id).where(Category.path.op("<@")(category_filter))
            conditions.append(Product.category_id.in_(category_condition))

        # Apply conditions
        if conditions:
            query = query.where(and_(*conditions))

        # Apply pagination
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_with_inventory(self, product_id: UUID) -> Optional[Product]:
        """Get product with all inventory items"""
        query = (
            select(Product)
            .where(Product.id == product_id)
            .options(
                selectinload(Product.brand),
                selectinload(Product.category),
                selectinload(Product.inventory_items).selectinload(InventoryItem.size),
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_inventory_summary(self) -> List[Dict[str, Any]]:
        """Get inventory summary by product"""
        query = (
            select(
                Product.id,
                Product.name,
                Product.sku,
                Brand.name.label("brand_name"),
                func.count(InventoryItem.id).label("total_items"),
                func.count(InventoryItem.id)
                .filter(InventoryItem.status == "in_stock")
                .label("in_stock"),
                func.count(InventoryItem.id).filter(InventoryItem.status == "sold").label("sold"),
                func.avg(InventoryItem.purchase_price).label("avg_purchase_price"),
            )
            .join(Brand)
            .outerjoin(InventoryItem)
            .group_by(Product.id, Product.name, Product.sku, Brand.name)
            .order_by(desc(func.count(InventoryItem.id)))
        )

        result = await self.db.execute(query)
        rows = result.fetchall()

        return [
            {
                "product_id": str(row.id),
                "name": row.name,
                "sku": row.sku,
                "brand_name": row.brand_name,
                "total_items": row.total_items or 0,
                "in_stock": row.in_stock or 0,
                "sold": row.sold or 0,
                "avg_purchase_price": (
                    float(row.avg_purchase_price) if row.avg_purchase_price else None
                ),
            }
            for row in rows
        ]

    async def create_with_inventory(
        self, product_data: Dict[str, Any], inventory_items: List[Dict[str, Any]]
    ) -> Product:
        """Create product with initial inventory items"""
        # Create product
        product = Product(**product_data)
        self.db.add(product)
        await self.db.flush()  # Get the ID

        # Create inventory items
        for item_data in inventory_items:
            item_data["product_id"] = product.id
            inventory_item = InventoryItem(**item_data)
            self.db.add(inventory_item)

        await self.db.commit()
        await self.db.refresh(product)

        return product

    async def update_inventory_status(
        self, inventory_id: UUID, new_status: str, notes: Optional[str] = None
    ) -> bool:
        """Update inventory item status"""
        query = select(InventoryItem).where(InventoryItem.id == inventory_id)
        result = await self.db.execute(query)
        inventory_item = result.scalar_one_or_none()

        if not inventory_item:
            return False

        inventory_item.status = new_status
        if notes:
            inventory_item.notes = notes

        await self.db.commit()
        return True

    async def get_low_stock_products(self, threshold: int = 5) -> List[Dict[str, Any]]:
        """Get products with low stock levels"""
        query = (
            select(
                Product.id,
                Product.name,
                Product.sku,
                Brand.name.label("brand_name"),
                func.count(InventoryItem.id)
                .filter(InventoryItem.status == "in_stock")
                .label("stock_count"),
            )
            .join(Brand)
            .outerjoin(InventoryItem)
            .group_by(Product.id, Product.name, Product.sku, Brand.name)
            .having(
                func.count(InventoryItem.id).filter(InventoryItem.status == "in_stock") <= threshold
            )
            .order_by("stock_count")
        )

        result = await self.db.execute(query)
        rows = result.fetchall()

        return [
            {
                "product_id": str(row.id),
                "name": row.name,
                "sku": row.sku,
                "brand_name": row.brand_name,
                "stock_count": row.stock_count or 0,
            }
            for row in rows
        ]

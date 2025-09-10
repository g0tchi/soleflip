"""
Inventory Repository
Typed repository for inventory operations with domain-specific methods.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.database.models import Brand, InventoryItem, Product
from shared.repositories import BaseRepository


@dataclass
class InventoryStats:
    """Inventory statistics result"""

    total_items: int
    in_stock: int
    sold: int
    listed: int
    total_value: Decimal
    avg_purchase_price: Decimal


class InventoryRepository(BaseRepository[InventoryItem]):
    """Typed repository for inventory operations"""

    def __init__(self, db_session: AsyncSession):
        super().__init__(InventoryItem, db_session)

    async def get_inventory_stats(self) -> InventoryStats:
        """Get inventory statistics using efficient aggregation query"""
        query = select(
            func.count(InventoryItem.id).label("total_items"),
            func.count(case((InventoryItem.status == "in_stock", 1))).label("in_stock"),
            func.count(case((InventoryItem.status == "sold", 1))).label("sold"),
            func.count(case((InventoryItem.status == "listed", 1))).label("listed"),
            func.coalesce(
                func.sum(
                    case(
                        (InventoryItem.status == "in_stock", InventoryItem.purchase_price), else_=0
                    )
                ),
                0,
            ).label("total_value"),
            func.coalesce(func.avg(InventoryItem.purchase_price), 0).label("avg_purchase_price"),
        )

        result = await self.db.execute(query)
        row = result.first()

        return InventoryStats(
            total_items=row.total_items or 0,
            in_stock=row.in_stock or 0,
            sold=row.sold or 0,
            listed=row.listed or 0,
            total_value=Decimal(str(row.total_value or 0)),
            avg_purchase_price=Decimal(str(row.avg_purchase_price or 0)),
        )

    async def get_by_status(self, status: str, limit: Optional[int] = None) -> List[InventoryItem]:
        """Get inventory items by status"""
        return await self.find_many(status=status, limit=limit)

    async def get_with_product_details(self, item_id: UUID) -> Optional[InventoryItem]:
        """Get inventory item with full product details"""
        query = (
            select(InventoryItem)
            .options(
                selectinload(InventoryItem.product).selectinload(Product.brand),
                selectinload(InventoryItem.product).selectinload(Product.category),
                selectinload(InventoryItem.size),
            )
            .where(InventoryItem.id == item_id)
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_sku(self, sku: str) -> List[InventoryItem]:
        """Get inventory items by product SKU"""
        query = select(InventoryItem).join(Product).where(Product.sku == sku)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_by_brand(
        self, brand_name: str, limit: Optional[int] = None
    ) -> List[InventoryItem]:
        """Get inventory items by brand name"""
        query = select(InventoryItem).join(Product).join(Brand).where(Brand.name == brand_name)

        if limit:
            query = query.limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_low_stock_items(self, threshold: int = 1) -> List[InventoryItem]:
        """Get items with low stock (quantity below threshold)"""
        return await self.find_many(**{"quantity__lt": threshold, "status": "in_stock"})

    async def update_status(self, item_id: UUID, status: str) -> Optional[InventoryItem]:
        """Update item status"""
        return await self.update(item_id, status=status)

    async def get_items_by_date_range(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> List[InventoryItem]:
        """Get items by purchase date range"""
        query = select(InventoryItem)

        conditions = []
        if start_date:
            conditions.append(InventoryItem.purchase_date >= start_date)
        if end_date:
            conditions.append(InventoryItem.purchase_date <= end_date)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_all_paginated(
        self, skip: int = 0, limit: int = 100, filters: Optional[Dict[str, Any]] = None
    ) -> List[InventoryItem]:
        """Get paginated list of inventory items with eager loaded relationships"""
        query = (
            select(InventoryItem)
            .options(
                selectinload(InventoryItem.product).selectinload(Product.brand),
                selectinload(InventoryItem.product).selectinload(Product.category),
                selectinload(InventoryItem.size),
            )
        )

        # Apply filters if provided
        if filters:
            for field, value in filters.items():
                if value is not None:
                    if hasattr(InventoryItem, field):
                        query = query.where(getattr(InventoryItem, field) == value)

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

#!/usr/bin/env python3
"""
Script to add test inventory items to the database
"""

import asyncio
import uuid
from decimal import Decimal
from datetime import datetime, timezone

from shared.database.connection import db_manager
from shared.database.models import Brand, Category, Product, Size, InventoryItem


async def add_test_data():
    """Add test inventory items to the database"""
    
    await db_manager.initialize()
    
    async with db_manager.get_session() as session:
        # Create test brand
        test_brand = Brand(
            id=uuid.uuid4(),
            name="Nike",
            description="Nike sneakers"
        )
        session.add(test_brand)
        
        # Create test category
        test_category = Category(
            id=uuid.uuid4(),
            name="Sneakers",
            description="Athletic footwear"
        )
        session.add(test_category)
        
        # Create test size
        test_size = Size(
            id=uuid.uuid4(),
            name="US 10",
            category="shoe",
            sort_order=10
        )
        session.add(test_size)
        
        # Create test product
        test_product = Product(
            id=uuid.uuid4(),
            name="Air Jordan 1 Retro High OG",
            sku="AJ1-RETRO-HIGH-001",
            brand_id=test_brand.id,
            category_id=test_category.id,
            description="Classic Air Jordan 1 in Chicago colorway",
            retail_price=Decimal("170.00")
        )
        session.add(test_product)
        
        # Create test inventory items with different statuses
        inventory_items = [
            InventoryItem(
                id=uuid.uuid4(),
                product_id=test_product.id,
                size_id=test_size.id,
                quantity=1,
                purchase_price=Decimal("120.00"),
                purchase_date=datetime.now(timezone.utc),
                status="in_stock",
                notes="Perfect condition, never worn"
            ),
            InventoryItem(
                id=uuid.uuid4(),
                product_id=test_product.id,
                size_id=test_size.id,
                quantity=1,
                purchase_price=Decimal("130.00"),
                purchase_date=datetime.now(timezone.utc),
                status="presale",
                notes="Pre-order item, ships next month"
            ),
            InventoryItem(
                id=uuid.uuid4(),
                product_id=test_product.id,
                size_id=test_size.id,
                quantity=1,
                purchase_price=Decimal("140.00"),
                purchase_date=datetime.now(timezone.utc),
                status="preorder",
                notes="Limited release pre-order"
            ),
            InventoryItem(
                id=uuid.uuid4(),
                product_id=test_product.id,
                size_id=test_size.id,
                quantity=1,
                purchase_price=Decimal("110.00"),
                purchase_date=datetime.now(timezone.utc),
                status="sold",
                notes="Sold on StockX"
            ),
        ]
        
        for item in inventory_items:
            session.add(item)
        
        await session.commit()
        print(f"✅ Added {len(inventory_items)} test inventory items!")
        print("Items with statuses:")
        for item in inventory_items:
            print(f"  - {item.status}: ${item.purchase_price}")


if __name__ == "__main__":
    asyncio.run(add_test_data())
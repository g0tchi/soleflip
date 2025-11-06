# Repository Pattern Guide

**Pattern**: Data Access Layer
**Location**: `shared/repositories/base_repository.py`
**Last Updated**: 2025-11-06

---

## Table of Contents

1. [Overview](#overview)
2. [BaseRepository Architecture](#baserepository-architecture)
3. [Creating Domain Repositories](#creating-domain-repositories)
4. [CRUD Operations](#crud-operations)
5. [Query Patterns](#query-patterns)
6. [Performance Optimization](#performance-optimization)
7. [Testing Repositories](#testing-repositories)
8. [Best Practices](#best-practices)

---

## Overview

The Repository Pattern provides a standardized interface for data access, decoupling business logic from database implementation. All domain repositories inherit from `BaseRepository`, ensuring consistent CRUD operations across the codebase.

### Why Use Repository Pattern?

✅ **Separation of Concerns**: Business logic separated from data access
✅ **Testability**: Easy to mock repositories for unit testing
✅ **Consistency**: Standardized CRUD interface across all domains
✅ **Type Safety**: Generic typing with `TypeVar` for model inference
✅ **Maintainability**: Database queries centralized in repositories

### Architecture Diagram

```
┌────────────────────────────────────────────────────────────┐
│                     Service Layer                          │
│         (Business Logic - No Direct DB Access)             │
├────────────────────────────────────────────────────────────┤
│                          ▼                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            Repository Layer                           │  │
│  │  (Data Access - All Database Interactions)           │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │                                                       │  │
│  │  ┌──────────────────┐     ┌──────────────────┐      │  │
│  │  │  BaseRepository  │────▶│ Domain Repos     │      │  │
│  │  │  (Generic CRUD)  │     │ (Specific Queries)│     │  │
│  │  └──────────────────┘     └──────────────────┘      │  │
│  │                                  │                   │  │
│  └──────────────────────────────────┼───────────────────┘  │
│                                     ▼                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Database Layer                           │  │
│  │        (SQLAlchemy Async ORM + PostgreSQL)           │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

---

## BaseRepository Architecture

### Location

**File**: `shared/repositories/base_repository.py`

### Generic Type System

```python
from typing import Generic, TypeVar

T = TypeVar("T")  # Model type variable

class BaseRepository(Generic[T]):
    """
    Generic base repository with comprehensive CRUD operations.
    Type-safe interface for all domain repositories.
    """

    def __init__(self, model_class: Type[T], db_session: AsyncSession):
        self.model_class = model_class
        self.db = db_session
        self._logger = logger.bind(
            repository=self.__class__.__name__,
            model=model_class.__name__
        )
```

**Benefits of Generic Typing**:
- IDE autocomplete for model attributes
- Type checking with mypy
- Prevents type errors at compile time
- Clear return type inference

---

## Creating Domain Repositories

### Step 1: Define Repository Class

Create a new repository in `domains/{domain}/repositories/{repository_name}_repository.py`:

```python
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.database.models import YourModel
from shared.repositories import BaseRepository


class YourRepository(BaseRepository[YourModel]):
    """Repository for YourModel operations"""

    def __init__(self, db_session: AsyncSession):
        super().__init__(YourModel, db_session)

    # Add domain-specific methods here
    async def find_by_custom_field(self, value: str) -> List[YourModel]:
        """Custom query method"""
        query = select(YourModel).where(YourModel.custom_field == value)
        result = await self.db.execute(query)
        return result.scalars().all()
```

### Step 2: Use in Service Layer

```python
from domains.your_domain.repositories.your_repository import YourRepository


class YourService:
    def __init__(self, db_session: AsyncSession):
        self.repository = YourRepository(db_session)

    async def get_items(self):
        """Service method using repository"""
        return await self.repository.get_all(limit=100)
```

### Step 3: Inject in API Endpoints

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from shared.database.connection import get_db_session


router = APIRouter()


@router.get("/items")
async def list_items(db: AsyncSession = Depends(get_db_session)):
    repository = YourRepository(db)
    items = await repository.get_all(limit=100)
    return items
```

---

## CRUD Operations

### Create Operations

#### Single Entity Creation

```python
# Create single entity
product = await product_repo.create(
    name="Nike Air Jordan 1",
    brand_id=brand.id,
    sku="554724-062",
    price=Decimal("159.99")
)

print(f"Created product: {product.id}")
```

**Behind the Scenes**:
1. Creates model instance: `Product(**kwargs)`
2. Adds to session: `db.add(entity)`
3. Commits transaction: `db.commit()`
4. Refreshes entity to get generated fields: `db.refresh(entity)`
5. Returns persisted entity

#### Batch Creation

```python
# Create multiple entities efficiently
products_data = [
    {"name": "Nike Air Max 97", "sku": "921826-101", "price": Decimal("179.99")},
    {"name": "Adidas Yeezy Boost 350", "sku": "FU9006", "price": Decimal("220.00")},
    {"name": "Jordan 4 Retro", "sku": "308497-060", "price": Decimal("189.99")},
]

products = await product_repo.create_batch(products_data)
print(f"Created {len(products)} products")
```

**Performance**: Batch creation is ~10x faster than individual creates for large datasets.

---

### Read Operations

#### Get by ID

```python
# Simple ID lookup
product = await product_repo.get_by_id(product_id)

if product:
    print(f"Found: {product.name}")
else:
    print("Product not found")
```

#### Get with Related Models (Eager Loading)

```python
# Load product with related brand and category
product = await product_repo.get_by_id_with_related(
    entity_id=product_id,
    related=["brand", "category", "sizes"]
)

# Access related data without additional queries
print(f"Brand: {product.brand.name}")
print(f"Category: {product.category.name}")
print(f"Sizes: {[s.value for s in product.sizes]}")
```

**Performance**: Eager loading prevents N+1 query problems.

#### Get All with Filtering

```python
# Get all Nike products, ordered by price descending
products = await product_repo.get_all(
    filters={"brand_id": nike_brand_id, "status": "active"},
    order_by="-price",  # Prefix with '-' for descending
    limit=50,
    offset=0
)
```

**Filtering Options**:
- **Equality**: `{"field": value}` → `field == value`
- **IN clause**: `{"field": [val1, val2]}` → `field IN (val1, val2)`
- **Ordering**: `order_by="field"` (asc) or `order_by="-field"` (desc)

#### Pagination

```python
# Get paginated results
page_1 = await product_repo.get_all_paginated(
    skip=0,
    limit=50,
    filters={"brand_id": nike_brand_id}
)

page_2 = await product_repo.get_all_paginated(
    skip=50,
    limit=50,
    filters={"brand_id": nike_brand_id}
)

# Count total for pagination metadata
total_count = await product_repo.count_all(
    filters={"brand_id": nike_brand_id}
)

total_pages = (total_count + 49) // 50  # Ceiling division
```

#### Find Single Entity

```python
# Find by unique field (e.g., SKU)
product = await product_repo.find_one(sku="554724-062")

if not product:
    raise ResourceNotFoundException("Product not found")
```

#### Check Existence

```python
# Check if product exists (efficient - only queries ID)
exists = await product_repo.exists(sku="554724-062")

if not exists:
    # Create new product
    product = await product_repo.create(sku="554724-062", ...)
```

---

### Update Operations

```python
# Update entity by ID
updated_product = await product_repo.update(
    entity_id=product.id,
    price=Decimal("179.99"),
    status="active"
)

if updated_product:
    print(f"Updated price to €{updated_product.price}")
else:
    print("Product not found")
```

**Features**:
- Automatically filters out `None` values (no accidental null overwrites)
- Auto-updates `updated_at` timestamp if model has this field
- Returns updated entity or `None` if not found

---

### Delete Operations

```python
# Delete entity by ID
deleted = await product_repo.delete(product.id)

if deleted:
    print("Product deleted successfully")
else:
    print("Product not found")
```

**Returns**: `bool` (True if deleted, False if not found)

---

### Count Operations

```python
# Count all entities
total_products = await product_repo.count()

# Count with filters
nike_products = await product_repo.count(
    filters={"brand_id": nike_brand_id, "status": "active"}
)

print(f"Total products: {total_products}")
print(f"Nike products: {nike_products}")
```

---

## Query Patterns

### Pattern 1: Simple Queries (Use BaseRepository)

For basic CRUD, use inherited methods directly:

```python
# No custom repository needed
async def get_active_products():
    repo = BaseRepository(Product, db_session)
    return await repo.get_all(filters={"status": "active"}, limit=100)
```

---

### Pattern 2: Domain-Specific Queries (Extend BaseRepository)

For complex queries, create custom methods:

```python
class ProductRepository(BaseRepository[Product]):

    async def get_by_brand_and_category(
        self,
        brand_id: UUID,
        category_id: UUID,
        min_price: Optional[Decimal] = None
    ) -> List[Product]:
        """Get products by brand and category with optional price filter"""
        query = select(Product).where(
            and_(
                Product.brand_id == brand_id,
                Product.category_id == category_id
            )
        )

        if min_price:
            query = query.where(Product.price >= min_price)

        result = await self.db.execute(query)
        return result.scalars().all()
```

---

### Pattern 3: Aggregation Queries

For statistics and analytics:

```python
from sqlalchemy import func, case


class InventoryRepository(BaseRepository[InventoryItem]):

    async def get_inventory_stats(self) -> InventoryStats:
        """Efficient aggregation query for dashboard"""
        query = select(
            func.count(InventoryItem.id).label("total_items"),
            func.count(
                case((InventoryItem.status == "in_stock", 1))
            ).label("in_stock"),
            func.sum(InventoryItem.purchase_price).label("total_value"),
            func.avg(InventoryItem.purchase_price).label("avg_price")
        )

        result = await self.db.execute(query)
        row = result.first()

        return InventoryStats(
            total_items=row.total_items or 0,
            in_stock=row.in_stock or 0,
            total_value=Decimal(str(row.total_value or 0)),
            avg_price=Decimal(str(row.avg_price or 0))
        )
```

**Benefits**:
- Single database query (not N queries)
- Efficient aggregation in database
- Type-safe result via dataclass

---

### Pattern 4: Join Queries

For cross-table queries:

```python
class InventoryRepository(BaseRepository[InventoryItem]):

    async def get_by_sku(self, sku: str) -> List[InventoryItem]:
        """Get inventory items by product SKU (requires join)"""
        query = (
            select(InventoryItem)
            .join(Product)
            .where(Product.sku == sku)
        )

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_by_brand(self, brand_name: str) -> List[InventoryItem]:
        """Get inventory by brand name (requires multiple joins)"""
        query = (
            select(InventoryItem)
            .join(Product)
            .join(Brand)
            .where(Brand.name == brand_name)
        )

        result = await self.db.execute(query)
        return result.scalars().all()
```

---

### Pattern 5: Eager Loading (N+1 Prevention)

Load related models efficiently:

```python
from sqlalchemy.orm import selectinload


class InventoryRepository(BaseRepository[InventoryItem]):

    async def get_with_product_details(
        self,
        item_id: UUID
    ) -> Optional[InventoryItem]:
        """Get inventory item with all related data in single query"""
        query = (
            select(InventoryItem)
            .options(
                selectinload(InventoryItem.product)
                    .selectinload(Product.brand),
                selectinload(InventoryItem.product)
                    .selectinload(Product.category),
                selectinload(InventoryItem.size)
            )
            .where(InventoryItem.id == item_id)
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()
```

**Performance**: 1 query instead of 4 separate queries.

---

## Performance Optimization

### 1. Use Batch Operations

**Bad** (N queries):
```python
for product_data in products_data:
    await product_repo.create(**product_data)  # 1000 queries
```

**Good** (1 query):
```python
await product_repo.create_batch(products_data)  # 1 query
```

**Performance**: 10-50x faster for large datasets.

---

### 2. Use Eager Loading

**Bad** (N+1 queries):
```python
products = await product_repo.get_all()  # 1 query

for product in products:
    print(product.brand.name)  # N additional queries
```

**Good** (2 queries):
```python
# Use custom method with eager loading
products = await product_repo.get_all_with_brands()  # 2 queries total

for product in products:
    print(product.brand.name)  # No additional queries
```

---

### 3. Use Aggregation Queries

**Bad** (Multiple queries + Python processing):
```python
all_items = await inventory_repo.get_all()  # 1 query
in_stock = [i for i in all_items if i.status == "in_stock"]
total_value = sum(i.purchase_price for i in in_stock)  # Python loop
```

**Good** (Single efficient query):
```python
stats = await inventory_repo.get_inventory_stats()  # 1 query
total_value = stats.total_value  # Calculated in database
```

---

### 4. Use Pagination

**Bad** (Loads entire table into memory):
```python
all_products = await product_repo.get_all()  # 100,000 rows
```

**Good** (Load only needed rows):
```python
page_1 = await product_repo.get_all_paginated(skip=0, limit=50)
```

---

### 5. Use count() Efficiently

**Bad** (Loads all data to count):
```python
products = await product_repo.get_all()
count = len(products)  # Loads all rows
```

**Good** (Count in database):
```python
count = await product_repo.count()  # SELECT COUNT(*) query
```

---

## Testing Repositories

### Unit Testing with Mocks

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_create_product(mock_db_session):
    """Test product creation"""
    # Arrange
    repo = ProductRepository(mock_db_session)
    product_data = {
        "name": "Test Product",
        "sku": "TEST-001",
        "price": Decimal("99.99")
    }

    # Mock commit and refresh
    mock_db_session.commit = AsyncMock()
    mock_db_session.refresh = AsyncMock()

    # Act
    product = await repo.create(**product_data)

    # Assert
    assert product.name == "Test Product"
    assert product.sku == "TEST-001"
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
```

---

### Integration Testing with Test Database

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.integration
@pytest.mark.asyncio
async def test_product_repository_integration(test_db_session: AsyncSession):
    """Test product repository with real database"""
    # Arrange
    repo = ProductRepository(test_db_session)

    # Act - Create product
    product = await repo.create(
        name="Nike Air Jordan 1",
        sku="554724-062",
        price=Decimal("159.99")
    )

    # Assert - Verify creation
    assert product.id is not None
    assert product.name == "Nike Air Jordan 1"

    # Act - Retrieve product
    retrieved = await repo.get_by_id(product.id)

    # Assert - Verify retrieval
    assert retrieved is not None
    assert retrieved.id == product.id
    assert retrieved.sku == "554724-062"

    # Act - Update product
    updated = await repo.update(product.id, price=Decimal("179.99"))

    # Assert - Verify update
    assert updated.price == Decimal("179.99")

    # Act - Delete product
    deleted = await repo.delete(product.id)

    # Assert - Verify deletion
    assert deleted is True

    # Verify product no longer exists
    not_found = await repo.get_by_id(product.id)
    assert not_found is None
```

---

## Best Practices

### ✅ DO: Keep Business Logic in Services

**Good**:
```python
class ProductService:
    def __init__(self, db_session: AsyncSession):
        self.product_repo = ProductRepository(db_session)
        self.inventory_repo = InventoryRepository(db_session)

    async def create_product_with_inventory(self, product_data, inventory_data):
        """Business logic in service"""
        # Create product
        product = await self.product_repo.create(**product_data)

        # Create inventory
        inventory_data["product_id"] = product.id
        inventory = await self.inventory_repo.create(**inventory_data)

        return product, inventory
```

**Bad**:
```python
class ProductRepository(BaseRepository[Product]):
    async def create_with_inventory(self, product_data, inventory_data):
        """DON'T: Business logic in repository"""
        product = await self.create(**product_data)
        # Mixing concerns - repository shouldn't know about inventory
```

---

### ✅ DO: Use Type Hints

**Good**:
```python
async def get_by_sku(self, sku: str) -> List[Product]:
    """Returns list of Product objects"""
    ...
```

**Bad**:
```python
async def get_by_sku(self, sku):  # No type hints
    ...
```

---

### ✅ DO: Log Repository Operations

```python
async def create(self, **kwargs) -> T:
    self._logger.debug("Creating entity", fields=list(kwargs.keys()))
    entity = self.model_class(**kwargs)
    # ... creation logic
    self._logger.info("Entity created", entity_id=entity.id)
    return entity
```

---

### ❌ DON'T: Execute Raw SQL Directly

**Bad**:
```python
async def get_products():
    result = await db.execute(text("SELECT * FROM products"))  # Unsafe
```

**Good**:
```python
async def get_products():
    query = select(Product)
    result = await db.execute(query)  # Type-safe
```

---

### ❌ DON'T: Mix Repository and Service Concerns

**Bad**:
```python
class ProductRepository(BaseRepository[Product]):
    async def create_and_send_email(self, product_data):
        product = await self.create(**product_data)
        send_email(...)  # DON'T: Email logic in repository
        return product
```

**Good**:
```python
class ProductService:
    async def create_product(self, product_data):
        product = await self.product_repo.create(**product_data)
        await self.email_service.send_welcome_email(product)  # Service layer
        return product
```

---

### ❌ DON'T: Forget to Handle None Results

**Bad**:
```python
product = await product_repo.get_by_id(product_id)
print(product.name)  # May crash if product is None
```

**Good**:
```python
product = await product_repo.get_by_id(product_id)
if not product:
    raise ResourceNotFoundException(f"Product {product_id} not found")
print(product.name)
```

---

## Example: Complete Repository Implementation

Here's a complete example of a domain-specific repository:

```python
"""
Order Repository
Domain-specific repository for order operations.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.database.models import Order, Product, Brand
from shared.repositories import BaseRepository


class OrderRepository(BaseRepository[Order]):
    """Repository for order operations with domain-specific queries"""

    def __init__(self, db_session: AsyncSession):
        super().__init__(Order, db_session)

    async def get_active_orders(
        self,
        limit: Optional[int] = None
    ) -> List[Order]:
        """Get all active orders (not completed/cancelled)"""
        return await self.get_all(
            filters={"status": ["pending", "processing", "shipped"]},
            order_by="-created_at",
            limit=limit
        )

    async def get_orders_by_date_range(
        self,
        from_date: date,
        to_date: date
    ) -> List[Order]:
        """Get orders within date range"""
        query = (
            select(Order)
            .where(
                and_(
                    Order.order_date >= from_date,
                    Order.order_date <= to_date
                )
            )
            .order_by(Order.order_date.desc())
        )

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_with_product_details(
        self,
        order_id: UUID
    ) -> Optional[Order]:
        """Get order with full product details (eager loading)"""
        query = (
            select(Order)
            .options(
                selectinload(Order.product)
                    .selectinload(Product.brand),
                selectinload(Order.product)
                    .selectinload(Product.category)
            )
            .where(Order.id == order_id)
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_revenue_by_brand(
        self,
        from_date: date,
        to_date: date
    ) -> List[dict]:
        """Get revenue aggregated by brand (analytics query)"""
        query = (
            select(
                Brand.name.label("brand"),
                func.sum(Order.price).label("total_revenue"),
                func.count(Order.id).label("order_count")
            )
            .join(Product)
            .join(Brand)
            .where(
                and_(
                    Order.order_date >= from_date,
                    Order.order_date <= to_date,
                    Order.status == "completed"
                )
            )
            .group_by(Brand.name)
            .order_by(func.sum(Order.price).desc())
        )

        result = await self.db.execute(query)
        return [
            {
                "brand": row.brand,
                "total_revenue": Decimal(str(row.total_revenue or 0)),
                "order_count": row.order_count or 0
            }
            for row in result
        ]

    async def get_by_order_number(
        self,
        order_number: str
    ) -> Optional[Order]:
        """Get order by unique order number"""
        return await self.find_one(order_number=order_number)
```

**Usage in Service**:
```python
class OrderService:
    def __init__(self, db_session: AsyncSession):
        self.order_repo = OrderRepository(db_session)

    async def get_monthly_revenue_report(
        self,
        year: int,
        month: int
    ) -> dict:
        """Generate monthly revenue report"""
        from_date = date(year, month, 1)
        to_date = date(year, month + 1, 1) if month < 12 else date(year + 1, 1, 1)

        revenue_by_brand = await self.order_repo.get_revenue_by_brand(
            from_date=from_date,
            to_date=to_date
        )

        total_revenue = sum(b["total_revenue"] for b in revenue_by_brand)
        total_orders = sum(b["order_count"] for b in revenue_by_brand)

        return {
            "period": f"{year}-{month:02d}",
            "total_revenue": total_revenue,
            "total_orders": total_orders,
            "revenue_by_brand": revenue_by_brand
        }
```

---

## See Also

- [Integration Domain Guide](../domains/INTEGRATION_DOMAIN.md) - Example repository usage
- [Pricing Domain Guide](../domains/PRICING_DOMAIN.md) - Example repository usage
- [API Endpoints Reference](../API_ENDPOINTS.md) - API patterns using repositories
- [Testing Documentation](../testing/TESTING_GUIDE.md) - Repository testing patterns
- [CLAUDE.md](../../CLAUDE.md) - Architecture overview

---

**Last Updated**: 2025-11-06
**Maintainer**: SoleFlipper Development Team
**Status**: ✅ Production Ready

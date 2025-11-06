# Testing Guide

**Testing Framework**: pytest + pytest-asyncio
**Coverage Tool**: pytest-cov
**Factory Library**: Factory Boy
**Last Updated**: 2025-11-06

---

## Table of Contents

1. [Overview](#overview)
2. [Test Organization](#test-organization)
3. [Running Tests](#running-tests)
4. [Test Fixtures](#test-fixtures)
5. [Factory Patterns](#factory-patterns)
6. [Unit Testing](#unit-testing)
7. [Integration Testing](#integration-testing)
8. [API Testing](#api-testing)
9. [Mocking Strategies](#mocking-strategies)
10. [Coverage Requirements](#coverage-requirements)
11. [Best Practices](#best-practices)

---

## Overview

The SoleFlipper testing strategy follows a 3-tier approach:

```
┌─────────────────────────────────────────────────────────────┐
│                      Test Pyramid                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                    ┌───────────────┐                        │
│                    │  API Tests    │  (Slow, Few)           │
│                    │  End-to-End   │                        │
│                    └───────────────┘                        │
│                ┌───────────────────────┐                    │
│                │  Integration Tests    │  (Medium)          │
│                │  Database + Services  │                    │
│                └───────────────────────┘                    │
│        ┌───────────────────────────────────────┐            │
│        │        Unit Tests                     │  (Fast)    │
│        │  Isolated, Mocked Dependencies        │  (Many)    │
│        └───────────────────────────────────────┘            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Test Distribution

- **Unit Tests** (70%): Fast, isolated, extensive coverage
- **Integration Tests** (25%): Database interactions, service integration
- **API Tests** (5%): Full HTTP request/response cycle

---

## Test Organization

### Directory Structure

```
tests/
├── conftest.py                    # Root fixtures and configuration
├── fixtures/                      # Reusable test fixtures
│   ├── __init__.py
│   ├── database_fixtures.py       # Database session fixtures
│   ├── model_factories.py         # Factory Boy factories
│   └── api_fixtures.py            # API client fixtures
├── unit/                          # Unit tests (isolated, mocked)
│   ├── services/
│   │   ├── test_stockx_service.py
│   │   ├── test_pricing_service.py
│   │   └── test_brand_service.py
│   ├── repositories/
│   │   └── test_import_repository.py
│   ├── middleware/
│   │   └── test_etag_middleware.py
│   ├── test_validators.py
│   └── test_database_models.py
├── integration/                   # Integration tests (database + services)
│   ├── test_import_pipeline.py
│   ├── test_comprehensive_fixtures.py
│   └── api/
│       ├── test_products_api.py
│       ├── test_orders_api.py
│       └── test_stockx_webhook.py
└── load_testing.py                # Performance/load tests
```

### Test Categories (Markers)

```python
# Unit tests (fast, isolated)
@pytest.mark.unit
async def test_function():
    ...

# Integration tests (database required)
@pytest.mark.integration
async def test_database_interaction():
    ...

# API tests (full HTTP cycle)
@pytest.mark.api
async def test_api_endpoint():
    ...

# Slow tests (performance, load)
@pytest.mark.slow
async def test_performance():
    ...

# Database-dependent tests
@pytest.mark.database
async def test_with_database():
    ...
```

---

## Running Tests

### Quick Start

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/services/test_stockx_service.py

# Run specific test function
pytest tests/unit/services/test_stockx_service.py::test_get_active_orders
```

### Run by Category

```bash
# Unit tests only (fast)
pytest -m unit

# Integration tests only
pytest -m integration

# API tests only
pytest -m api

# All except slow tests
pytest -m "not slow"

# Combine markers
pytest -m "unit or integration"
```

### Coverage Reports

```bash
# Run tests with coverage
pytest --cov=domains --cov=shared --cov-report=html --cov-report=term-missing

# View HTML coverage report
open htmlcov/index.html

# Coverage summary in terminal
pytest --cov=domains --cov=shared --cov-report=term

# Show missing lines
pytest --cov=domains --cov=shared --cov-report=term-missing
```

### Watch Mode (Auto-Rerun)

```bash
# Install pytest-watch
pip install pytest-watch

# Run tests on file changes
make test-watch
# or
ptw -- -v
```

### Makefile Shortcuts

```bash
make test               # Run all tests
make test-unit          # Unit tests only
make test-integration   # Integration tests only
make test-api           # API tests only
make test-cov           # Tests with coverage report
make test-watch         # Watch mode
```

---

## Test Fixtures

### Database Fixtures

**Location**: `tests/fixtures/database_fixtures.py`

#### Session-Scoped Database (Fast)

```python
@pytest.fixture(scope="session")
async def initialize_db_for_session():
    """
    Initialize in-memory SQLite database for entire test session.
    Tables created once, used by all tests.
    """
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    os.environ["FIELD_ENCRYPTION_KEY"] = Fernet.generate_key().decode()

    await db_manager.initialize()

    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    await db_manager.close()
```

**Usage**: Automatic (session-scoped).

---

#### Function-Scoped Database Session (Isolated)

```python
@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Database session with transaction rollback for test isolation.
    Each test gets clean database state.
    """
    async with session_factory() as session:
        async with session.begin():
            yield session
            await session.rollback()  # Rollback after test
```

**Usage**:
```python
@pytest.mark.asyncio
async def test_create_product(db_session):
    # Create product in test
    product_repo = ProductRepository(db_session)
    product = await product_repo.create(name="Test Product")

    # Verify creation
    assert product.id is not None
    # Automatically rolled back after test
```

---

### API Client Fixtures

**Location**: `tests/fixtures/api_fixtures.py`

```python
@pytest.fixture
def test_client() -> TestClient:
    """Synchronous test client for simple API tests"""
    return TestClient(app)


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async test client for async API tests"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
```

**Usage**:
```python
@pytest.mark.api
async def test_api_endpoint(async_client):
    response = await async_client.get("/api/products")
    assert response.status_code == 200
```

---

## Factory Patterns

### Factory Boy Factories

**Location**: `tests/fixtures/model_factories.py`

Factories provide clean, reusable test data generation using Factory Boy.

#### BrandFactory

```python
class BrandFactory(factory.Factory):
    class Meta:
        model = Brand

    id = factory.LazyFunction(uuid.uuid4)
    name = factory.Sequence(lambda n: f"Brand {n}")
    slug = factory.LazyAttribute(lambda obj: obj.name.lower().replace(" ", "-"))
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
```

**Usage**:
```python
# Create brand with default values
brand = BrandFactory()
print(brand.name)  # "Brand 1"

# Create with custom values
nike = BrandFactory(name="Nike", slug="nike")
print(nike.name)  # "Nike"

# Create multiple brands
brands = BrandFactory.create_batch(10)
```

---

#### ProductFactory

```python
class ProductFactory(factory.Factory):
    class Meta:
        model = Product

    id = factory.LazyFunction(uuid.uuid4)
    name = factory.Sequence(lambda n: f"Product {n}")
    sku = factory.Sequence(lambda n: f"SKU-{n:04d}")
    price = factory.LazyFunction(lambda: Decimal("99.99"))
    brand_id = factory.LazyFunction(uuid.uuid4)
    category_id = factory.LazyFunction(uuid.uuid4)
```

**Usage**:
```python
# Create product with brand relationship
brand = BrandFactory()
product = ProductFactory(
    name="Nike Air Jordan 1",
    sku="554724-062",
    brand_id=brand.id,
    price=Decimal("159.99")
)
```

---

#### InventoryItemFactory

```python
class InventoryItemFactory(factory.Factory):
    class Meta:
        model = InventoryItem

    id = factory.LazyFunction(uuid.uuid4)
    product_id = factory.LazyFunction(uuid.uuid4)
    size_id = factory.LazyFunction(uuid.uuid4)
    condition = "new"
    status = InventoryStatus.IN_STOCK
    purchase_price = Decimal("100.00")
    location = "Warehouse A"
```

**Usage**:
```python
# Create inventory item
inventory = InventoryItemFactory(
    condition="new",
    status=InventoryStatus.IN_STOCK,
    purchase_price=Decimal("120.00")
)
```

---

### Using Factories in Tests

```python
@pytest.mark.unit
async def test_product_service(db_session):
    """Example: Using factories in unit tests"""
    # Arrange - Create test data with factories
    brand = BrandFactory(name="Nike")
    category = CategoryFactory(name="Sneakers")

    product = ProductFactory(
        name="Nike Air Max 97",
        brand_id=brand.id,
        category_id=category.id,
        price=Decimal("179.99")
    )

    # Act - Test product service logic
    product_service = ProductService(db_session)
    result = await product_service.calculate_discount(product)

    # Assert
    assert result.discounted_price < product.price
```

---

## Unit Testing

Unit tests are **fast**, **isolated**, and test **single units** of code (functions, methods, classes).

### Key Principles

✅ **Isolated**: No database, no external APIs (use mocks)
✅ **Fast**: Should run in milliseconds
✅ **Focused**: Test one thing per test
✅ **Deterministic**: Same input = same output

### Example: Testing Repository Methods

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4


@pytest.mark.unit
@pytest.mark.asyncio
async def test_product_repository_get_by_id():
    """Test repository get_by_id method (mocked database)"""
    # Arrange - Create mocks
    mock_session = AsyncMock()
    product_id = uuid4()

    mock_product = ProductFactory(id=product_id, name="Test Product")
    mock_session.get = AsyncMock(return_value=mock_product)

    # Act - Call repository method
    repo = ProductRepository(mock_session)
    result = await repo.get_by_id(product_id)

    # Assert
    assert result.id == product_id
    assert result.name == "Test Product"
    mock_session.get.assert_called_once_with(Product, product_id)
```

---

### Example: Testing Service Logic

```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_pricing_engine_cost_plus_strategy():
    """Test pricing engine cost-plus calculation"""
    # Arrange
    mock_session = AsyncMock()
    engine = PricingEngine(mock_session)

    product = ProductFactory(name="Test Product")
    inventory = InventoryItemFactory(
        product_id=product.id,
        purchase_price=Decimal("100.00")
    )

    context = PricingContext(
        product=product,
        inventory_item=inventory,
        target_margin=Decimal("25.0")  # 25% margin
    )

    # Act
    result = await engine._calculate_cost_plus_price(context, rules=[])

    # Assert
    assert result.suggested_price == Decimal("133.33")  # €100 / 0.75 = €133.33
    assert result.margin_percent == Decimal("25.0")
    assert result.strategy_used == PricingStrategy.COST_PLUS
```

---

### Example: Testing Validators

```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_stockx_validator_valid_data():
    """Test StockX validator with valid data"""
    # Arrange
    mock_session = AsyncMock()
    validator = StockXValidator(mock_session)

    valid_data = [
        {
            "order_number": "ORDER-123",
            "product_name": "Nike Air Jordan 1",
            "order_date": "2025-11-06",
            "price": "159.99",
            "status": "completed"
        }
    ]

    # Act
    result = await validator.validate(valid_data)

    # Assert
    assert result.is_valid is True
    assert len(result.errors) == 0
    assert len(result.normalized_data) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stockx_validator_invalid_date():
    """Test StockX validator with invalid date format"""
    # Arrange
    mock_session = AsyncMock()
    validator = StockXValidator(mock_session)

    invalid_data = [
        {
            "order_number": "ORDER-123",
            "product_name": "Nike Air Jordan 1",
            "order_date": "invalid-date",  # Invalid format
            "price": "159.99",
            "status": "completed"
        }
    ]

    # Act
    result = await validator.validate(invalid_data)

    # Assert
    assert result.is_valid is False
    assert len(result.errors) > 0
    assert "order_date" in result.errors[0]["field"]
```

---

## Integration Testing

Integration tests verify **component interactions** with real database and services.

### Key Principles

✅ **Database Required**: Uses real SQLite test database
✅ **Service Integration**: Tests multiple components together
✅ **Realistic**: Close to production behavior
✅ **Slower**: Can take seconds per test

### Example: Testing Import Pipeline

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_complete_import_pipeline(db_session):
    """Test complete CSV import workflow"""
    # Arrange - Create test CSV file
    csv_content = """order_number,product_name,order_date,price,status
ORDER-001,Nike Air Jordan 1,2025-11-06,159.99,completed
ORDER-002,Adidas Yeezy Boost 350,2025-11-06,220.00,completed
"""
    csv_path = "/tmp/test_import.csv"
    with open(csv_path, "w") as f:
        f.write(csv_content)

    # Act - Run import processor
    processor = ImportProcessor(db_session)
    batch = await processor.create_initial_batch(
        source_type=SourceType.STOCKX,
        filename="test_import.csv"
    )

    result = await processor.process_import(
        batch_id=batch.id,
        file_path=csv_path,
        source_type=SourceType.STOCKX
    )

    # Assert - Verify import results
    assert result.successful_records == 2
    assert result.failed_records == 0

    # Verify database records
    orders = await db_session.execute(select(Transaction))
    order_list = orders.scalars().all()
    assert len(order_list) == 2

    # Verify order details
    order_1 = order_list[0]
    assert order_1.order_number == "ORDER-001"
    assert order_1.product_name == "Nike Air Jordan 1"
    assert order_1.price == Decimal("159.99")
```

---

### Example: Testing Service with Database

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_inventory_service_get_stats(db_session):
    """Test inventory service statistics calculation"""
    # Arrange - Create test inventory data
    brand = BrandFactory()
    product = ProductFactory(brand_id=brand.id)

    # Create inventory items with different statuses
    in_stock_items = [
        InventoryItemFactory(
            product_id=product.id,
            status=InventoryStatus.IN_STOCK,
            purchase_price=Decimal("100.00")
        )
        for _ in range(5)
    ]

    sold_items = [
        InventoryItemFactory(
            product_id=product.id,
            status=InventoryStatus.SOLD,
            purchase_price=Decimal("120.00")
        )
        for _ in range(3)
    ]

    # Save to database
    db_session.add_all(in_stock_items + sold_items)
    await db_session.commit()

    # Act - Get inventory stats
    inventory_service = InventoryService(db_session)
    stats = await inventory_service.get_inventory_stats()

    # Assert
    assert stats.total_items == 8
    assert stats.in_stock == 5
    assert stats.sold == 3
    assert stats.total_value == Decimal("500.00")  # 5 * €100
    assert stats.avg_purchase_price == Decimal("107.50")  # (500 + 360) / 8
```

---

## API Testing

API tests verify **HTTP endpoints** with full request/response cycle.

### Key Principles

✅ **Full Stack**: Tests entire API layer
✅ **HTTP Requests**: Uses test client
✅ **Response Validation**: Checks status codes, JSON structure
✅ **Authentication**: Tests with/without auth

### Example: Testing GET Endpoint

```python
@pytest.mark.api
@pytest.mark.asyncio
async def test_get_products_endpoint(async_client, db_session):
    """Test GET /api/products endpoint"""
    # Arrange - Create test products
    brand = BrandFactory(name="Nike")
    products = [
        ProductFactory(
            name=f"Product {i}",
            brand_id=brand.id,
            price=Decimal(f"{100 + i}.00")
        )
        for i in range(5)
    ]

    db_session.add_all(products)
    await db_session.commit()

    # Act - Make API request
    response = await async_client.get("/api/products?limit=10")

    # Assert - Verify response
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert len(data["items"]) == 5

    # Verify first product
    first_product = data["items"][0]
    assert "id" in first_product
    assert "name" in first_product
    assert "price" in first_product
```

---

### Example: Testing POST Endpoint

```python
@pytest.mark.api
@pytest.mark.asyncio
async def test_create_product_endpoint(async_client, db_session):
    """Test POST /api/products endpoint"""
    # Arrange
    brand = BrandFactory()
    category = CategoryFactory()

    db_session.add_all([brand, category])
    await db_session.commit()

    product_data = {
        "name": "Nike Air Jordan 1",
        "sku": "554724-062",
        "brand_id": str(brand.id),
        "category_id": str(category.id),
        "price": 159.99
    }

    # Act
    response = await async_client.post(
        "/api/products",
        json=product_data
    )

    # Assert
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == "Nike Air Jordan 1"
    assert data["sku"] == "554724-062"

    # Verify database creation
    product = await db_session.get(Product, data["id"])
    assert product is not None
    assert product.name == "Nike Air Jordan 1"
```

---

### Example: Testing Error Responses

```python
@pytest.mark.api
@pytest.mark.asyncio
async def test_get_product_not_found(async_client):
    """Test GET /api/products/{id} with non-existent ID"""
    # Act
    non_existent_id = uuid4()
    response = await async_client.get(f"/api/products/{non_existent_id}")

    # Assert
    assert response.status_code == 404

    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()
```

---

## Mocking Strategies

### Mocking External APIs (StockX)

```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_stockx_service_with_mocked_api(monkeypatch):
    """Test StockX service with mocked HTTP client"""
    # Arrange - Mock HTTP response
    mock_response = {
        "data": [
            {
                "id": "product-123",
                "name": "Nike Air Jordan 1",
                "sku": "554724-062"
            }
        ]
    }

    async def mock_get(*args, **kwargs):
        return MockResponse(json_data=mock_response, status_code=200)

    # Patch httpx.AsyncClient.get
    monkeypatch.setattr("httpx.AsyncClient.get", mock_get)

    # Act
    service = StockXService(mock_session)
    results = await service.search_stockx_catalog("Jordan 1")

    # Assert
    assert len(results) == 1
    assert results[0]["name"] == "Nike Air Jordan 1"
```

---

### Mocking Database Queries

```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_product_service_with_mocked_repository():
    """Test product service with mocked repository"""
    # Arrange
    mock_repo = AsyncMock(spec=ProductRepository)
    mock_product = ProductFactory()

    mock_repo.get_by_id.return_value = mock_product

    # Create service with mocked repo
    service = ProductService(mock_repo)

    # Act
    result = await service.get_product(mock_product.id)

    # Assert
    assert result.id == mock_product.id
    mock_repo.get_by_id.assert_called_once_with(mock_product.id)
```

---

## Coverage Requirements

### Current Coverage

```
Module-level docstrings:    100% ✅
API endpoint docs:           95% ✅
Overall documentation:       85.6% ✅
Test coverage:               80%+ (target)
```

### Coverage Goals

- **Minimum**: 80% overall coverage
- **Target**: 90% for critical domains (integration, pricing, orders)
- **Focus Areas**:
  - Business logic in `domains/*/services/`
  - Repository methods in `domains/*/repositories/`
  - API endpoints in `domains/*/api/`

### Excluded from Coverage

- `main.py` - Application entry point
- `migrations/` - Alembic migrations
- `tests/` - Test code itself
- `conftest.py` - Test configuration

### Checking Coverage

```bash
# Generate coverage report
pytest --cov=domains --cov=shared --cov-report=html

# View report
open htmlcov/index.html

# View missing lines in terminal
pytest --cov=domains --cov=shared --cov-report=term-missing
```

---

## Best Practices

### ✅ DO: Follow AAA Pattern

```python
async def test_example():
    # Arrange - Set up test data
    product = ProductFactory()

    # Act - Execute the code being tested
    result = await service.process(product)

    # Assert - Verify the results
    assert result.status == "success"
```

---

### ✅ DO: Use Descriptive Test Names

```python
# Good - Clear what is being tested
async def test_pricing_engine_applies_cost_plus_with_25_percent_margin():
    ...

# Bad - Vague test name
async def test_pricing():
    ...
```

---

### ✅ DO: Test Edge Cases

```python
# Test happy path
async def test_create_product_success():
    ...

# Test error cases
async def test_create_product_with_invalid_price():
    ...

async def test_create_product_with_missing_required_field():
    ...

async def test_create_product_with_duplicate_sku():
    ...
```

---

### ✅ DO: Keep Tests Independent

```python
# Good - Each test is independent
@pytest.mark.asyncio
async def test_create_product(db_session):
    product = await product_repo.create(name="Test")
    assert product.id is not None
    # db_session rolls back after test

@pytest.mark.asyncio
async def test_update_product(db_session):
    product = await product_repo.create(name="Test")
    updated = await product_repo.update(product.id, name="Updated")
    assert updated.name == "Updated"
    # Independent of previous test
```

---

### ❌ DON'T: Share State Between Tests

```python
# Bad - Tests depend on shared state
global_product = None

async def test_create():
    global global_product
    global_product = await repo.create(...)  # DON'T

async def test_update():
    await repo.update(global_product.id, ...)  # Depends on test_create
```

---

### ❌ DON'T: Test Implementation Details

```python
# Bad - Testing implementation
async def test_repository_uses_sqlalchemy_select():
    # Tests how it works, not what it does
    assert isinstance(repo.query, select)

# Good - Testing behavior
async def test_repository_returns_products():
    # Tests what it does
    products = await repo.get_all()
    assert len(products) > 0
```

---

### ❌ DON'T: Write Slow Unit Tests

```python
# Bad - Unit test with database
@pytest.mark.unit
async def test_with_real_database(db_session):  # DON'T - use @pytest.mark.integration
    product = await repo.create(...)

# Good - Unit test with mocks
@pytest.mark.unit
async def test_with_mocked_database():
    mock_repo = AsyncMock()
    mock_repo.create.return_value = ProductFactory()
    ...
```

---

## See Also

- [Repository Pattern Guide](../patterns/REPOSITORY_PATTERN.md) - Testing repositories
- [Integration Domain Guide](../domains/INTEGRATION_DOMAIN.md) - Integration testing examples
- [API Endpoints Reference](../API_ENDPOINTS.md) - API testing reference
- [CLAUDE.md](../../CLAUDE.md) - Testing commands

---

**Last Updated**: 2025-11-06
**Maintainer**: SoleFlipper Development Team
**Status**: ✅ Production Ready

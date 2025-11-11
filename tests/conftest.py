"""
Test Configuration and Fixtures
Provides reusable test fixtures for database, API client, and test data
Integrates with the new fixture infrastructure in tests.fixtures
"""

import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, AsyncGenerator, Dict
from uuid import uuid4

import pytest
import structlog
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from main import app
from shared.database.connection import db_manager
from shared.database.models import Base

# Import comprehensive fixtures from new fixture infrastructure
from tests.fixtures import *  # noqa: F403

# Configure logging for tests to ensure compatibility with pytest's capture
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Test database configuration
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
async def initialize_db_for_session():
    """
    Initializes the database for the entire test session.
    Sets environment variables, initializes the db_manager, and creates tables.
    """
    from cryptography.fernet import Fernet

    original_db_url = os.environ.get("DATABASE_URL")
    original_key = os.environ.get("FIELD_ENCRYPTION_KEY")

    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    # Use a valid 32-byte key for Fernet encryption in tests
    os.environ["FIELD_ENCRYPTION_KEY"] = Fernet.generate_key().decode()

    await db_manager.initialize()

    # Create tables using the initialized engine
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    await db_manager.close()

    # Restore original environment
    if original_db_url:
        os.environ["DATABASE_URL"] = original_db_url
    else:
        os.environ.pop("DATABASE_URL", None)

    if original_key:
        os.environ["FIELD_ENCRYPTION_KEY"] = original_key
    else:
        os.environ.pop("FIELD_ENCRYPTION_KEY", None)


# Note: db_session fixture is now provided by tests.fixtures.database_fixtures
# This legacy fixture is kept for backward compatibility with existing tests
@pytest.fixture(scope="function")
async def legacy_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Legacy database session fixture for backward compatibility"""
    # Create session factory
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        # Start transaction
        transaction = await session.begin()

        try:
            yield session
        finally:
            # Rollback transaction to clean up
            if transaction.is_active:
                await transaction.rollback()

    await engine.dispose()


# Note: async_client and client fixtures are now provided by tests.fixtures.api_fixtures
# These legacy fixtures are kept for backward compatibility
@pytest.fixture
async def test_client() -> AsyncGenerator[AsyncClient, None]:
    """Legacy test HTTP client fixture for backward compatibility"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def sync_client() -> TestClient:
    """Legacy synchronous test client for backward compatibility"""
    return TestClient(app)


# Test data factories
@pytest.fixture
def sample_brand_data() -> Dict[str, Any]:
    """Sample brand data for testing"""
    return {"name": "Nike", "slug": "nike"}


@pytest.fixture
def sample_category_data() -> Dict[str, Any]:
    """Sample category data for testing"""
    return {"name": "Sneakers", "slug": "sneakers", "path": "sneakers"}


@pytest.fixture
def sample_size_data(sample_category_data) -> Dict[str, Any]:
    """Sample size data for testing"""
    return {
        "category_id": str(uuid4()),
        "value": "US 9",
        "standardized_value": Decimal("9.0"),
        "region": "US",
    }


@pytest.fixture
def sample_product_data(sample_brand_data, sample_category_data) -> Dict[str, Any]:
    """Sample product data for testing"""
    return {
        "sku": "TEST-001",
        "brand_id": str(uuid4()),
        "category_id": str(uuid4()),
        "name": "Test Sneaker",
        "description": "A test sneaker for unit testing",
        "retail_price": Decimal("150.00"),
        "release_date": datetime.now(timezone.utc),
    }


@pytest.fixture
def sample_inventory_data(sample_product_data, sample_size_data) -> Dict[str, Any]:
    """Sample inventory data for testing"""
    return {
        "product_id": str(uuid4()),
        "size_id": str(uuid4()),
        "quantity": 1,
        "purchase_price": Decimal("120.00"),
        "purchase_date": datetime.now(timezone.utc),
        "supplier": "Test Supplier",
        "status": "in_stock",
    }


@pytest.fixture
def sample_platform_data() -> Dict[str, Any]:
    """Sample platform data for testing"""
    return {"name": "StockX", "slug": "stockx", "fee_percentage": Decimal("9.5"), "active": True}


@pytest.fixture
def sample_transaction_data() -> Dict[str, Any]:
    """Sample transaction data for testing"""
    return {
        "inventory_id": str(uuid4()),
        "platform_id": str(uuid4()),
        "transaction_date": datetime.now(timezone.utc),
        "sale_price": Decimal("200.00"),
        "platform_fee": Decimal("19.00"),
        "shipping_cost": Decimal("15.00"),
        "net_profit": Decimal("46.00"),
        "status": "completed",
        "external_id": "TEST-TXN-001",
    }


@pytest.fixture
def sample_stockx_csv_data() -> list[Dict[str, Any]]:
    """Sample StockX CSV data for import testing"""
    return [
        {
            "Order Number": "SX-ORDER-001",
            "Sale Date": "2024-01-15 10:30:00",
            "Item": "Nike Air Jordan 1 High OG Chicago",
            "SKU": "555088-101",
            "Size": "9",
            "Listing Price": "180.00",
            "Seller Fee": "17.10",
            "Payment Processing": "5.40",
            "Shipping Fee": "13.95",
            "Total Payout": "143.55",
            "Seller Name": "TestSeller",
            "Buyer Country": "United States",
            "Invoice Number": "INV-001",
        },
        {
            "Order Number": "SX-ORDER-002",
            "Sale Date": "2024-01-16 14:20:00",
            "Item": "Adidas Yeezy Boost 350 V2",
            "SKU": "FY2903",
            "Size": "10.5",
            "Listing Price": "250.00",
            "Seller Fee": "23.75",
            "Payment Processing": "7.50",
            "Shipping Fee": "13.95",
            "Total Payout": "204.80",
            "Seller Name": "TestSeller",
            "Buyer Country": "Canada",
            "Invoice Number": "INV-002",
        },
    ]


@pytest.fixture
def sample_notion_json_data() -> list[Dict[str, Any]]:
    """Sample Notion JSON data for import testing"""
    return [
        {
            "id": "page-id-001",
            "database_id": "db-id-001",
            "name": "Nike Air Jordan 1",
            "properties": {
                "brand": {"rich_text": [{"text": {"content": "Nike"}}]},
                "size": {"rich_text": [{"text": {"content": "US 9"}}]},
                "purchase_price": {"number": 120.00},
                "target_price": {"number": 180.00},
                "status": {"select": {"name": "In Stock"}},
                "stockx_order": {"rich_text": [{"text": {"content": "SX-ORDER-001"}}]},
            },
            "last_edited_time": "2024-01-15T10:30:00.000Z",
        },
        {
            "id": "page-id-002",
            "database_id": "db-id-001",
            "name": "Adidas Yeezy 350",
            "properties": {
                "brand": {"rich_text": [{"text": {"content": "Adidas"}}]},
                "size": {"rich_text": [{"text": {"content": "US 10.5"}}]},
                "purchase_price": {"number": 200.00},
                "target_price": {"number": 250.00},
                "status": {"select": {"name": "Listed"}},
                "alias_order": {"rich_text": [{"text": {"content": "AL-ORDER-001"}}]},
            },
            "last_edited_time": "2024-01-16T14:20:00.000Z",
        },
    ]


@pytest.fixture
def sample_import_batch_data() -> Dict[str, Any]:
    """Sample import batch data for testing"""
    return {
        "source_type": "stockx",
        "source_file": "test_stockx_export.csv",
        "total_records": 2,
        "processed_records": 0,
        "error_records": 0,
        "status": "pending",
    }


@pytest.fixture
def sample_import_record_data() -> Dict[str, Any]:
    """Sample import record data for testing"""
    return {
        "batch_id": str(uuid4()),
        "raw_data": {"test": "data"},
        "normalized_data": {"normalized": "data"},
        "processed": False,
    }


# Mock fixtures for external dependencies
@pytest.fixture
def mock_n8n_webhook(monkeypatch):
    """Mock n8n webhook calls"""

    async def mock_webhook_call(*args, **kwargs):
        return {"status": "success", "message": "mocked"}

    monkeypatch.setattr("httpx.AsyncClient.post", mock_webhook_call)


@pytest.fixture
def mock_metabase_api(monkeypatch):
    """Mock Metabase API calls"""

    async def mock_api_call(*args, **kwargs):
        return {"data": "mocked_metabase_response"}

    monkeypatch.setattr("httpx.AsyncClient.get", mock_api_call)


# Note: override_get_db fixture is now provided by tests.fixtures.api_fixtures
# This legacy fixture is kept for backward compatibility
@pytest.fixture
async def override_db_dependency(legacy_db_session):
    """Legacy database dependency override for backward compatibility"""

    async def get_test_db():
        yield legacy_db_session

    from shared.database.connection import get_db_session

    app.dependency_overrides[get_db_session] = get_test_db

    yield

    # Clean up
    app.dependency_overrides.clear()


# Performance test fixtures
@pytest.fixture
def performance_timer():
    """Timer fixture for performance tests"""
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.perf_counter()

        def stop(self):
            self.end_time = time.perf_counter()

        @property
        def elapsed_ms(self):
            if self.start_time and self.end_time:
                return (self.end_time - self.start_time) * 1000
            return None

    return Timer()


# Test markers and utilities
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "unit: marks tests as unit tests (fast, isolated)")
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (slower, with dependencies)"
    )
    config.addinivalue_line("markers", "api: marks tests as API endpoint tests")
    config.addinivalue_line("markers", "slow: marks tests as slow running")
    config.addinivalue_line("markers", "database: marks tests that require database access")

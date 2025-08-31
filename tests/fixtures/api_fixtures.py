"""
API fixtures for testing FastAPI endpoints
"""

from typing import Any, AsyncGenerator, Dict, Optional
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from main import app
from shared.config.settings import TestingSettings, get_settings
from shared.database.connection import get_db_session

from .database_fixtures import db_session, test_engine
from .model_factories import FactoryHelper


@pytest.fixture
def test_app() -> FastAPI:
    """Get test FastAPI application"""
    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create synchronous test client"""
    return TestClient(test_app)


@pytest.fixture
async def async_client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create asynchronous test client"""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def authenticated_client(async_client: AsyncClient, db_session) -> AsyncClient:
    """Create authenticated test client with mock user"""
    # Mock authentication for testing
    async_client.headers.update({"Authorization": "Bearer test-token"})
    return async_client


@pytest.fixture
def api_headers() -> Dict[str, str]:
    """Standard API headers for testing"""
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "SoleFlipper-Test-Client/1.0",
    }


@pytest.fixture
def mock_settings():
    """Mock application settings for testing"""
    return TestingSettings()


@pytest.fixture
def override_get_db(db_session):
    """Override database dependency for testing"""

    def _get_test_db():
        return db_session

    app.dependency_overrides[get_db_session] = _get_test_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def sample_product_data() -> Dict[str, Any]:
    """Sample product data for API testing"""
    return {
        "sku": "TEST-001",
        "name": "Test Product",
        "description": "A test product for API testing",
        "retail_price": "199.99",
        "avg_resale_price": "249.99",
        "release_date": "2024-01-15T00:00:00Z",
        "brand_id": None,  # Will be set in tests
        "category_id": None,  # Will be set in tests
        "status": "active",
    }


@pytest.fixture
def sample_inventory_data() -> Dict[str, Any]:
    """Sample inventory data for API testing"""
    return {
        "quantity": 5,
        "purchase_price": "180.00",
        "purchase_date": "2024-01-10T00:00:00Z",
        "supplier": "Test Supplier",
        "status": "in_stock",
        "notes": "Test inventory item",
        "external_ids": {"stockx": "test-stockx-id"},
    }


@pytest.fixture
def sample_order_data() -> Dict[str, Any]:
    """Sample order data for API testing"""
    return {
        "sale_price": "249.99",
        "platform_fee": "21.25",
        "shipping_cost": "15.00",
        "buyer_destination_country": "Germany",
        "buyer_destination_city": "Berlin",
        "status": "pending",
        "external_id": "TEST-ORDER-001",
        "notes": "Test order",
    }


@pytest.fixture
def sample_upload_data() -> Dict[str, Any]:
    """Sample CSV upload data for testing"""
    return {
        "source_type": "csv_upload",
        "total_records": 10,
        "processed_records": 8,
        "error_records": 2,
        "status": "completed",
    }


class APITestHelper:
    """Helper class for API testing operations"""

    def __init__(self, client: AsyncClient, db_session):
        self.client = client
        self.db_session = db_session

    async def create_test_scenario(self) -> Dict[str, Any]:
        """Create a complete test scenario with all related objects"""
        scenario = FactoryHelper.create_test_scenario()

        # Commit all objects to database
        for brand in scenario["brands"]:
            self.db_session.add(brand)
        for category in scenario["categories"]:
            self.db_session.add(category)
        for supplier in scenario["suppliers"]:
            self.db_session.add(supplier)
        for platform in scenario["platforms"]:
            self.db_session.add(platform)
        for product in scenario["products"]:
            self.db_session.add(product)

        await self.db_session.commit()

        return scenario

    async def assert_response_structure(
        self, response_data: Dict[str, Any], expected_keys: list, response_type: str = "success"
    ):
        """Assert that response has expected structure"""
        if response_type == "success":
            assert "success" in response_data
            assert response_data["success"] is True
            assert "data" in response_data
        elif response_type == "error":
            assert "success" in response_data
            assert response_data["success"] is False
            assert "error" in response_data
        elif response_type == "paginated":
            assert "data" in response_data
            assert "pagination" in response_data
            pagination = response_data["pagination"]
            assert "page" in pagination
            assert "per_page" in pagination
            assert "total" in pagination
            assert "pages" in pagination

        if expected_keys:
            data = response_data.get("data", response_data)
            for key in expected_keys:
                assert key in data, f"Missing expected key: {key}"

    async def post_json(
        self,
        url: str,
        data: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        expected_status: int = 200,
    ):
        """Helper for POST requests with JSON data"""
        response = await self.client.post(url, json=data, headers=headers or {})
        assert (
            response.status_code == expected_status
        ), f"Expected {expected_status}, got {response.status_code}: {response.text}"
        return response.json()

    async def get_json(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        expected_status: int = 200,
    ):
        """Helper for GET requests expecting JSON response"""
        response = await self.client.get(url, params=params or {}, headers=headers or {})
        assert (
            response.status_code == expected_status
        ), f"Expected {expected_status}, got {response.status_code}: {response.text}"
        return response.json()

    async def put_json(
        self,
        url: str,
        data: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        expected_status: int = 200,
    ):
        """Helper for PUT requests with JSON data"""
        response = await self.client.put(url, json=data, headers=headers or {})
        assert (
            response.status_code == expected_status
        ), f"Expected {expected_status}, got {response.status_code}: {response.text}"
        return response.json()

    async def delete_json(
        self, url: str, headers: Optional[Dict[str, str]] = None, expected_status: int = 200
    ):
        """Helper for DELETE requests"""
        response = await self.client.delete(url, headers=headers or {})
        assert (
            response.status_code == expected_status
        ), f"Expected {expected_status}, got {response.status_code}: {response.text}"
        return response.json() if response.content else {}


@pytest.fixture
def api_helper(async_client, db_session) -> APITestHelper:
    """API testing helper fixture"""
    return APITestHelper(async_client, db_session)


@pytest.fixture
def mock_external_services():
    """Mock external services for testing"""
    mocks = {}

    # Mock StockX API
    with patch("domains.integration.services.stockx_service.StockXService") as mock_stockx:
        mock_instance = AsyncMock()
        mock_instance.get_product_data.return_value = {
            "id": "test-stockx-id",
            "name": "Test Product",
            "retail_price": 199.99,
            "market_price": 249.99,
        }
        mock_instance.submit_listing.return_value = {"listing_id": "test-listing-123"}
        mock_stockx.return_value = mock_instance
        mocks["stockx"] = mock_instance

        # Mock email service
        with patch("shared.utils.email_service.EmailService") as mock_email:
            email_instance = AsyncMock()
            email_instance.send_notification.return_value = True
            mock_email.return_value = email_instance
            mocks["email"] = email_instance

            # Mock file upload service
            with patch("shared.utils.file_service.FileService") as mock_file:
                file_instance = AsyncMock()
                file_instance.upload_file.return_value = {
                    "file_id": "test-file-123",
                    "url": "https://test.com/file.csv",
                }
                mock_file.return_value = file_instance
                mocks["file"] = file_instance

                yield mocks


@pytest.fixture
def mock_database_operations():
    """Mock database operations for specific test scenarios"""
    with patch(
        "shared.database.connection.DatabaseManager.execute_transaction"
    ) as mock_transaction:
        mock_transaction.return_value = True

        with patch(
            "shared.database.session_manager.SessionManager.cleanup_expired_sessions"
        ) as mock_cleanup:
            mock_cleanup.return_value = {"cleaned_sessions": 5}

            yield {"transaction": mock_transaction, "cleanup": mock_cleanup}


# Integration test fixtures
@pytest.fixture(scope="session")
def integration_test_data():
    """Shared data for integration tests"""
    return {
        "test_brand": {"name": "Integration Test Brand", "slug": "integration-test-brand"},
        "test_category": {
            "name": "Integration Test Category",
            "slug": "integration-test-category",
            "path": "integration-test-category",
        },
        "test_supplier": {
            "name": "Integration Test Supplier",
            "supplier_type": "retailer",
            "email": "test@integrationtest.com",
            "country": "Germany",
        },
    }


@pytest.fixture
async def setup_integration_environment(db_session, integration_test_data):
    """Setup complete environment for integration tests"""
    from .model_factories import BrandFactory, CategoryFactory, SupplierFactory

    # Create test data
    brand = BrandFactory(**integration_test_data["test_brand"])
    category = CategoryFactory(**integration_test_data["test_category"])
    supplier = SupplierFactory(**integration_test_data["test_supplier"])

    # Add to session
    db_session.add(brand)
    db_session.add(category)
    db_session.add(supplier)
    await db_session.commit()

    # Refresh to get IDs
    await db_session.refresh(brand)
    await db_session.refresh(category)
    await db_session.refresh(supplier)

    yield {"brand": brand, "category": category, "supplier": supplier}

    # Cleanup after test
    await db_session.delete(brand)
    await db_session.delete(category)
    await db_session.delete(supplier)
    await db_session.commit()


class ResponseValidator:
    """Validate API response formats and structures"""

    @staticmethod
    def validate_success_response(response_data: Dict[str, Any], expected_data_keys: list = None):
        """Validate standard success response format"""
        assert isinstance(response_data, dict), "Response should be a dictionary"
        assert "success" in response_data, "Response should have 'success' field"
        assert response_data["success"] is True, "Success should be True"
        assert "data" in response_data, "Response should have 'data' field"

        if expected_data_keys:
            data = response_data["data"]
            for key in expected_data_keys:
                assert key in data, f"Data should contain '{key}' field"

    @staticmethod
    def validate_error_response(response_data: Dict[str, Any], expected_error_code: str = None):
        """Validate standard error response format"""
        assert isinstance(response_data, dict), "Response should be a dictionary"
        assert "success" in response_data, "Response should have 'success' field"
        assert response_data["success"] is False, "Success should be False"
        assert "error" in response_data, "Response should have 'error' field"

        error = response_data["error"]
        assert "message" in error, "Error should have 'message' field"
        assert "type" in error, "Error should have 'type' field"

        if expected_error_code:
            assert (
                error.get("code") == expected_error_code
            ), f"Expected error code '{expected_error_code}'"

    @staticmethod
    def validate_paginated_response(response_data: Dict[str, Any], expected_item_keys: list = None):
        """Validate paginated response format"""
        assert isinstance(response_data, dict), "Response should be a dictionary"
        assert "data" in response_data, "Response should have 'data' field"
        assert "pagination" in response_data, "Response should have 'pagination' field"

        # Validate data is a list
        assert isinstance(response_data["data"], list), "Data should be a list"

        # Validate pagination structure
        pagination = response_data["pagination"]
        required_pagination_keys = ["page", "per_page", "total", "pages"]
        for key in required_pagination_keys:
            assert key in pagination, f"Pagination should contain '{key}' field"

        # Validate item structure if items exist
        if response_data["data"] and expected_item_keys:
            first_item = response_data["data"][0]
            for key in expected_item_keys:
                assert key in first_item, f"Items should contain '{key}' field"


@pytest.fixture
def response_validator() -> ResponseValidator:
    """Response validator fixture"""
    return ResponseValidator()

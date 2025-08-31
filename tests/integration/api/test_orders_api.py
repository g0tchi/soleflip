from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from main import app  # Import the app instance

# Mark all tests in this file as API and integration tests that require a DB
pytestmark = [pytest.mark.api, pytest.mark.integration, pytest.mark.database]


@pytest.fixture
def mock_stockx_service():
    """Fixture to create a mock StockxService."""
    service = AsyncMock()
    # The methods themselves need to be async mocks
    service.get_active_orders = AsyncMock()
    service.get_historical_orders = AsyncMock()
    return service


@pytest.fixture(autouse=True)
def override_dependencies(mock_stockx_service):
    """Fixture to automatically override the get_stockx_service dependency."""
    from domains.integration.api.webhooks import get_stockx_service

    app.dependency_overrides[get_stockx_service] = lambda: mock_stockx_service
    yield
    app.dependency_overrides.clear()


async def test_get_active_orders_success(
    test_client: AsyncClient, mock_stockx_service, override_db_dependency
):
    """
    Tests the happy path for the GET /orders/active endpoint.
    """
    # Arrange
    mock_stockx_service.get_active_orders.return_value = [
        {"id": "active_order_1", "status": "SHIPPED"}
    ]

    # Act
    response = await test_client.get("/api/v1/orders/active?orderStatus=SHIPPED")

    # Assert
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 1
    assert response_data[0]["id"] == "active_order_1"

    # Verify that the service was called with the correct parameters
    mock_stockx_service.get_active_orders.assert_awaited_once()
    call_args = mock_stockx_service.get_active_orders.call_args
    assert call_args.kwargs["orderStatus"] == "SHIPPED"


async def test_get_active_orders_no_params(
    test_client: AsyncClient, mock_stockx_service, override_db_dependency
):
    """
    Tests calling the endpoint with no query parameters.
    """
    # Arrange
    mock_stockx_service.get_active_orders.return_value = [{"id": "order_1"}, {"id": "order_2"}]

    # Act
    response = await test_client.get("/api/v1/orders/active")

    # Assert
    assert response.status_code == 200
    assert len(response.json()) == 2

    # Verify service was called with default/None values
    mock_stockx_service.get_active_orders.assert_awaited_once()
    call_args = mock_stockx_service.get_active_orders.call_args
    assert call_args.kwargs["orderStatus"] is None
    assert call_args.kwargs["productId"] is None


async def test_get_active_orders_service_error(
    test_client: AsyncClient, mock_stockx_service, override_db_dependency
):
    """
    Tests that a 500 error is returned if the service layer raises an exception.
    """
    # Arrange
    mock_stockx_service.get_active_orders.side_effect = Exception("A wild service error appeared!")

    # Act
    response = await test_client.get("/api/v1/orders/active")

    # Assert
    assert response.status_code == 500
    response_data = response.json()
    assert "error" in response_data
    assert "An unexpected error occurred" in response_data["error"]["message"]


async def test_get_historical_orders_success(test_client: AsyncClient, mock_stockx_service):
    """
    Tests the happy path for the GET /orders/stockx-history endpoint with all filters.
    """
    # Arrange
    mock_stockx_service.get_historical_orders.return_value = [{"id": "hist_order_1"}]

    # Act
    response = await test_client.get(
        "/api/v1/orders/stockx-history?fromDate=2024-01-01&toDate=2024-01-31&orderStatus=COMPLETED&productId=prod-123"
    )

    # Assert
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 1
    assert response_data[0]["id"] == "hist_order_1"

    # Verify that the service was called with the correct parameters
    mock_stockx_service.get_historical_orders.assert_awaited_once()
    call_args = mock_stockx_service.get_historical_orders.call_args
    assert call_args.kwargs["from_date"] == date(2024, 1, 1)
    assert call_args.kwargs["to_date"] == date(2024, 1, 31)
    assert call_args.kwargs["order_status"] == "COMPLETED"
    assert call_args.kwargs["product_id"] == "prod-123"


async def test_get_historical_orders_missing_dates(test_client: AsyncClient):
    """
    Tests that a 422 validation error is returned if required date params are missing.
    """
    # Act
    response = await test_client.get("/api/v1/orders/stockx-history?toDate=2024-01-31")

    # Assert
    assert response.status_code == 422  # Unprocessable Entity


async def test_get_historical_orders_service_error(test_client: AsyncClient, mock_stockx_service):
    """
    Tests that a 500 error is returned if the historical orders service raises an exception.
    """
    # Arrange
    mock_stockx_service.get_historical_orders.side_effect = Exception(
        "A wild historical error appeared!"
    )

    # Act
    response = await test_client.get(
        "/api/v1/orders/stockx-history?fromDate=2024-01-01&toDate=2024-01-31"
    )

    # Assert
    assert response.status_code == 500
    response_data = response.json()
    assert "error" in response_data
    assert "An unexpected error occurred" in response_data["error"]["message"]

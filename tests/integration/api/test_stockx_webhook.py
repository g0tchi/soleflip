import pytest
from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient
from main import app

pytestmark = [pytest.mark.api, pytest.mark.integration, pytest.mark.database]


@pytest.fixture
def mock_stockx_service():
    """Fixture to create a mock StockxService."""
    return AsyncMock()


@pytest.fixture(autouse=True)
def override_dependencies(mock_stockx_service):
    from domains.integration.api.webhooks import get_stockx_service
    app.dependency_overrides[get_stockx_service] = lambda: mock_stockx_service
    yield
    app.dependency_overrides.clear()


async def test_stockx_import_orders_webhook_success(
    test_client: AsyncClient, mock_stockx_service, override_db_dependency
):
    """
    Tests the happy path for the /stockx/import-orders webhook.
    It should accept a valid request, return a 202 status, and trigger the background task.
    """
    mock_stockx_service.get_historical_orders.return_value = [{"id": "some_order"}]

    response = await test_client.post(
        "/api/v1/integration/stockx/import-orders",
        json={"from_date": "2023-01-01", "to_date": "2023-01-31"},
    )

    assert response.status_code == 202
    response_data = response.json()
    assert response_data["status"] == "processing_started"
    mock_stockx_service.get_historical_orders.assert_called_once()


async def test_stockx_import_orders_webhook_invalid_date(
    test_client: AsyncClient, override_db_dependency
):
    """
    Tests that the endpoint returns a 422 Unprocessable Entity error
    if the date format in the request body is invalid.
    """
    response = await test_client.post(
        "/api/v1/integration/stockx/import-orders",
        json={"from_date": "not-a-date", "to_date": "2023-01-31"},
    )
    assert response.status_code == 422


async def test_stockx_import_orders_webhook_missing_field(
    test_client: AsyncClient, override_db_dependency
):
    """
    Tests that the endpoint returns a 422 Unprocessable Entity error
    if a required field is missing from the request body.
    """
    response = await test_client.post(
        "/api/v1/integration/stockx/import-orders",
        json={"from_date": "2023-01-01"},
    )
    assert response.status_code == 422

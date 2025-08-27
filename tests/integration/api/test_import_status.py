import pytest
import asyncio
from uuid import UUID
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

from main import app # Import the app instance

# Mark all tests in this file as API and integration tests that require a DB
pytestmark = [pytest.mark.api, pytest.mark.integration, pytest.mark.database]

@pytest.fixture
def mock_stockx_service():
    """Fixture to create a mock StockxService."""
    service = AsyncMock()
    service.get_historical_orders = AsyncMock()
    return service

@pytest.fixture(autouse=True)
def override_dependencies(mock_stockx_service):
    """Fixture to automatically override the get_stockx_service dependency."""
    from domains.integration.api.webhooks import get_stockx_service
    app.dependency_overrides[get_stockx_service] = lambda: mock_stockx_service
    yield
    app.dependency_overrides.clear()

async def test_import_trigger_and_status_check(
    test_client: AsyncClient,
    mock_stockx_service,
    override_db_dependency,
    sample_stockx_csv_data # Using this as sample API data
):
    """
    Tests the full flow:
    1. Trigger an import.
    2. Get the batch_id from the response.
    3. Wait for the background task to process.
    4. Poll the status endpoint to verify the result.
    """
    # Arrange
    # The service will return two valid orders
    mock_stockx_service.get_historical_orders.return_value = sample_stockx_csv_data

    # --- Act 1: Trigger the import ---
    response_trigger = await test_client.post(
        "/api/v1/integration/stockx/import-orders",
        json={"from_date": "2024-01-01", "to_date": "2024-01-31"}
    )

    # --- Assert 1: Check the trigger response ---
    assert response_trigger.status_code == 202
    trigger_data = response_trigger.json()
    assert "batch_id" in trigger_data
    batch_id = trigger_data["batch_id"]
    assert isinstance(UUID(batch_id), UUID)

    # --- Act 2: Wait for background task and check status ---
    # In a real app, you might poll, but for a test, a short sleep is sufficient
    # to let the async background task complete with the in-memory DB.
    await asyncio.sleep(0.1)

    response_status = await test_client.get(f"/api/v1/integration/import-status/{batch_id}")

    # --- Assert 2: Check the status response ---
    assert response_status.status_code == 200
    status_data = response_status.json()

    assert status_data["id"] == batch_id
    assert status_data["status"] == "completed"
    assert status_data["source_type"] == "stockx"
    assert status_data["total_records"] == 2
    assert status_data["processed_records"] == 2
    assert status_data["error_records"] == 0
    assert status_data["completed_at"] is not None

async def test_get_import_status_not_found(test_client: AsyncClient, override_db_dependency):
    """
    Tests that a 404 is returned for a non-existent batch ID.
    """
    # Arrange
    non_existent_id = UUID(int=0)

    # Act
    response = await test_client.get(f"/api/v1/integration/import-status/{non_existent_id}")

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Import batch not found"

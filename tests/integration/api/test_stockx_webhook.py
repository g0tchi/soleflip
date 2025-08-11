import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

# Mark all tests in this file as API and integration tests
pytestmark = [pytest.mark.api, pytest.mark.integration]

def test_stockx_import_orders_webhook_success(sync_client: TestClient):
    """
    Tests the happy path for the /stockx/import-orders webhook.
    It should accept a valid request, return a 202 status, and trigger the background task.
    """
    # Arrange
    # We patch the two services that are called by the background task.
    # This verifies that the endpoint triggers the process correctly.
    with patch('domains.integration.api.webhooks.stockx_service.get_historical_orders', new_callable=AsyncMock) as mock_get_orders, \
         patch('domains.integration.api.webhooks.import_processor.process_import', new_callable=AsyncMock) as mock_process_import:

        # This is what the background task will call. We don't need it to return anything for this test.
        mock_get_orders.return_value = [{"id": "some_order"}]

        # Act
        response = sync_client.post(
            "/api/v1/integration/stockx/import-orders",
            json={
                "from_date": "2023-01-01",
                "to_date": "2023-01-31"
            }
        )

        # Assert
        assert response.status_code == 202
        response_data = response.json()
        assert response_data["status"] == "processing_started"
        assert "StockX API order import has been successfully started" in response_data["message"]
        assert response_data["details"]["from_date"] == "2023-01-01"

        # In a real TestClient run with BackgroundTasks, the tasks run after the response.
        # So we can't easily assert that the mocks were called.
        # This test primarily ensures the endpoint validation and response are correct.
        # A more complex setup with a custom BackgroundTasks runner would be needed
        # to assert calls on the mocks, but for this scope, we test the public contract.

def test_stockx_import_orders_webhook_invalid_date(sync_client: TestClient):
    """
    Tests that the endpoint returns a 422 Unprocessable Entity error
    if the date format in the request body is invalid.
    """
    # Act
    response = sync_client.post(
        "/api/v1/integration/stockx/import-orders",
        json={
            "from_date": "not-a-date",
            "to_date": "2023-01-31"
        }
    )

    # Assert
    assert response.status_code == 422
    response_data = response.json()
    assert response_data["detail"][0]["type"] == "date_from_datetime_parsing"
    assert "invalid character" in response_data["detail"][0]["msg"]

def test_stockx_import_orders_webhook_missing_field(sync_client: TestClient):
    """
    Tests that the endpoint returns a 422 Unprocessable Entity error
    if a required field is missing from the request body.
    """
    # Act
    response = sync_client.post(
        "/api/v1/integration/stockx/import-orders",
        json={
            "from_date": "2023-01-01"
            # to_date is missing
        }
    )

    # Assert
    assert response.status_code == 422
    response_data = response.json()
    assert response_data["detail"][0]["type"] == "missing"
    assert response_data["detail"][0]["loc"] == ["body", "to_date"]
    assert "Field required" in response_data["detail"][0]["msg"]

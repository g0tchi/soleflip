import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

# Mark all tests in this file as API and integration tests
pytestmark = [pytest.mark.api, pytest.mark.integration]

def test_get_active_orders_success(sync_client: TestClient):
    """
    Tests the happy path for the GET /orders/active endpoint.
    """
    # Arrange
    # Mock the service layer to isolate the API endpoint logic
    with patch('domains.orders.api.router.stockx_service.get_active_orders', new_callable=AsyncMock) as mock_get_active_orders:

        mock_get_active_orders.return_value = [{"id": "active_order_1", "status": "SHIPPED"}]

        # Act
        response = sync_client.get(
            "/api/v1/orders/active?orderStatus=SHIPPED"
        )

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 1
        assert response_data[0]["id"] == "active_order_1"

        # Verify that the service was called with the correct parameters
        mock_get_active_orders.assert_called_once()
        call_args = mock_get_active_orders.call_args
        assert call_args.kwargs['orderStatus'] == "SHIPPED"

def test_get_active_orders_no_params(sync_client: TestClient):
    """
    Tests calling the endpoint with no query parameters.
    """
    with patch('domains.orders.api.router.stockx_service.get_active_orders', new_callable=AsyncMock) as mock_get_active_orders:

        mock_get_active_orders.return_value = [{"id": "order_1"}, {"id": "order_2"}]

        # Act
        response = sync_client.get("/api/v1/orders/active")

        # Assert
        assert response.status_code == 200
        assert len(response.json()) == 2

        # Verify service was called with default/None values
        mock_get_active_orders.assert_called_once()
        call_args = mock_get_active_orders.call_args
        assert call_args.kwargs['orderStatus'] is None
        assert call_args.kwargs['productId'] is None

def test_get_active_orders_service_error(sync_client: TestClient):
    """
    Tests that a 500 error is returned if the service layer raises an exception.
    """
    with patch('domains.orders.api.router.stockx_service.get_active_orders', new_callable=AsyncMock) as mock_get_active_orders:

        mock_get_active_orders.side_effect = Exception("A wild service error appeared!")

        # Act
        response = sync_client.get("/api/v1/orders/active")

        # Assert
        assert response.status_code == 500
        assert "An unexpected error occurred" in response.json()["detail"]

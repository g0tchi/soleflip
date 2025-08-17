import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

from main import app
from domains.integration.services.stockx_service import StockXService

client = TestClient(app)

@pytest.mark.usefixtures("override_db_dependency")
@pytest.mark.asyncio
async def test_get_stockx_product_details_success(mocker):
    """
    Test successful retrieval of product details from StockX via our API endpoint.
    """
    product_id = "test-product-123"
    mock_response_data = {
        "productId": product_id,
        "title": "Test Product",
        "brand": "Test Brand",
        "styleId": "TP-123"
    }

    # Mock the service method
    mocker.patch.object(
        StockXService,
        'get_product_details',
        new_callable=AsyncMock,
        return_value=mock_response_data
    )

    # Make the request to our API
    response = client.get(f"/api/v1/products/{product_id}/stockx-details")

    # Assertions
    assert response.status_code == 200
    assert response.json() == mock_response_data
    StockXService.get_product_details.assert_called_once_with(product_id)


@pytest.mark.usefixtures("override_db_dependency")
@pytest.mark.asyncio
async def test_get_stockx_product_details_not_found(mocker):
    """
    Test the case where the product is not found on StockX.
    """
    product_id = "non-existent-product"

    # Mock the service method to return None
    mocker.patch.object(
        StockXService,
        'get_product_details',
        new_callable=AsyncMock,
        return_value=None
    )

    # Make the request to our API
    response = client.get(f"/api/v1/products/{product_id}/stockx-details")

    # Assertions
    assert response.status_code == 404
    assert response.json() == {"detail": f"Product with ID '{product_id}' not found on StockX."}
    StockXService.get_product_details.assert_called_once_with(product_id)

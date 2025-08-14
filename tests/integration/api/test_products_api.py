import pytest
from httpx import AsyncClient
from uuid import uuid4
from unittest.mock import patch, MagicMock

from shared.database.models import Product, Category, SystemConfig

pytestmark = pytest.mark.asyncio

@pytest.mark.integration
async def test_enrich_product_endpoint_success(test_client: AsyncClient, db_session, override_db_dependency):
    """
    Tests the POST /products/{product_id}/enrich-from-stockx endpoint for the success case.
    """
    # Arrange: Create necessary data in the test database
    # 1. A category for the product
    category_id = uuid4()
    test_category = Category(id=category_id, name="Sneakers", slug="sneakers")
    db_session.add(test_category)

    # 2. The product to be enriched
    product_id = uuid4()
    test_product = Product(id=product_id, sku="TEST-SKU", name="Test Product", category_id=category_id)
    db_session.add(test_product)

    # 3. Mocked StockX credentials in the database
    keys = ["stockx_client_id", "stockx_client_secret", "stockx_refresh_token", "stockx_api_key"]
    for key in keys:
        config = SystemConfig(key=key)
        config.set_value(f"test_{key}")
        db_session.add(config)

    # Let the fixture handle the transaction

    # Mock the actual external HTTP calls to avoid hitting the real StockX API
    with patch('httpx.AsyncClient') as MockAsyncClient:
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Mock the token refresh response and the product details response
        mock_response.json.side_effect = [
            {"access_token": "mock_token", "expires_in": 3600}, # For token refresh
            {"title": "Enriched Product Name"} # For get_product_details
        ]

        mock_instance = MockAsyncClient.return_value.__aenter__.return_value
        mock_instance.post.return_value = mock_response
        mock_instance.get.return_value = mock_response

        # Act
        response = await test_client.post(f"/api/v1/products/{product_id}/enrich-from-stockx")

        # Assert
        assert response.status_code == 202
        assert response.json() == {"message": "Product enrichment has been queued."}

        # To fully test the background task, we would need a more complex setup.
        # For now, we confirm the endpoint is correctly set up and returns the expected response.

import pytest
from httpx import AsyncClient
from uuid import uuid4
from unittest.mock import patch, MagicMock

from shared.database.models import Product, Category, InventoryItem, SystemConfig, Size

pytestmark = pytest.mark.asyncio

@pytest.mark.integration
async def test_enrich_inventory_item_endpoint(test_client: AsyncClient, db_session, override_db_dependency):
    """
    Tests the POST /inventory/{item_id}/enrich-from-stockx endpoint.
    """
    # Arrange
    category = Category(id=uuid4(), name="Test Category", slug="test-category")
    product = Product(id=uuid4(), name="Test Product", sku="TEST-SKU", category_id=category.id)
    # A size is needed for the inventory item's foreign key
    size = Size(id=uuid4(), value="9", region="US", category_id=category.id)
    item = InventoryItem(
        id=uuid4(),
        product_id=product.id,
        size_id=size.id,
        external_ids={"stockx_variant_id": "variant-123", "stockx_product_id": "TEST-SKU"}
    )
    db_session.add_all([category, product, size, item])

    keys = ["stockx_client_id", "stockx_client_secret", "stockx_refresh_token", "stockx_api_key"]
    for key in keys:
        config = SystemConfig(key=key)
        config.set_value(f"test_{key}")
        db_session.add(config)

    # Let the fixture handle commit/rollback

    with patch('httpx.AsyncClient') as MockAsyncClient:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = [
            {"access_token": "mock_token", "expires_in": 3600},
            {"isFlexEligible": True}
        ]

        mock_instance = MockAsyncClient.return_value.__aenter__.return_value
        mock_instance.post.return_value = mock_response
        mock_instance.get.return_value = mock_response

        # Act
        response = await test_client.post(f"/api/v1/inventory/{item.id}/enrich-from-stockx")

        # Assert
        assert response.status_code == 202
        assert response.json() == {"message": "Inventory item enrichment has been queued."}

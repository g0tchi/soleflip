import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from domains.products.services.product_processor import ProductProcessor
from shared.database.models import Product

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_db_session():
    return AsyncMock(spec=AsyncSession)

@pytest.fixture
def product_processor(mock_db_session):
    return ProductProcessor(db_session=mock_db_session)

async def test_enrich_product_from_stockx_success(product_processor, mock_db_session):
    """
    Tests that a product is successfully enriched with data from StockX.
    """
    # Arrange
    product_id = uuid4()
    mock_product = Product(id=product_id, sku="123-ABC", name="Old Name")

    # Mock the return value of session.get
    mock_db_session.get.return_value = mock_product

    stockx_api_response = {
        "productId": "123-ABC",
        "title": "New Awesome Name from StockX",
        "styleId": "ABC-123"
    }

    # We need to patch the StockXService that is instantiated inside the method
    with patch('domains.products.services.product_processor.StockXService', new_callable=MagicMock) as MockStockXService:
        mock_stockx_instance = MockStockXService.return_value
        mock_stockx_instance.get_product_details = AsyncMock(return_value=stockx_api_response)

        # Act
        enriched_product = await product_processor.enrich_product_from_stockx(product_id)

        # Assert
        mock_db_session.get.assert_called_once_with(Product, product_id)
        mock_stockx_instance.get_product_details.assert_called_once_with("123-ABC")

        assert enriched_product is not None
        assert enriched_product.name == "New Awesome Name from StockX"
        mock_db_session.commit.assert_called_once()

async def test_enrich_product_not_found_in_db(product_processor, mock_db_session):
    """
    Tests that the function returns None if the product is not in our database.
    """
    # Arrange
    product_id = uuid4()
    mock_db_session.get.return_value = None # Simulate product not found

    # Act
    result = await product_processor.enrich_product_from_stockx(product_id)

    # Assert
    assert result is None
    mock_db_session.commit.assert_not_called()

async def test_enrich_product_no_data_from_stockx(product_processor, mock_db_session):
    """
    Tests that the product is not updated if StockX returns no data.
    """
    # Arrange
    product_id = uuid4()
    original_name = "Original Name"
    mock_product = Product(id=product_id, sku="123-ABC", name=original_name)
    mock_db_session.get.return_value = mock_product

    with patch('domains.products.services.product_processor.StockXService', new_callable=MagicMock) as MockStockXService:
        mock_stockx_instance = MockStockXService.return_value
        mock_stockx_instance.get_product_details = AsyncMock(return_value=None) # Simulate StockX not finding the product

        # Act
        result = await product_processor.enrich_product_from_stockx(product_id)

        # Assert
        assert result is not None
        assert result.name == original_name # Name should not have changed
        mock_db_session.commit.assert_not_called() # Nothing to commit

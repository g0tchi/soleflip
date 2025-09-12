from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from domains.integration.services.stockx_service import StockXService
from domains.inventory.services.inventory_service import InventoryService
from shared.database.models import Brand, Category, InventoryItem, Product, Size

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_db_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_stockx_service():
    return AsyncMock(spec=StockXService)


@pytest.fixture
def inventory_service(mock_db_session, mock_stockx_service):
    with (
        patch("domains.inventory.services.inventory_service.ProductRepository") as MockProductRepo,
        patch("domains.inventory.services.inventory_service.BaseRepository") as MockBaseRepo,
    ):

        service = InventoryService(db_session=mock_db_session, stockx_service=mock_stockx_service)
        service.product_repo = MockProductRepo.return_value
        service.product_repo.get_with_inventory = AsyncMock()
        service.brand_repo = MockBaseRepo.return_value
        service.category_repo = MockBaseRepo.return_value

        service.size_repo = MockBaseRepo.return_value
        service.inventory_repo = MockBaseRepo.return_value

        return service


async def test_sync_inventory_from_stockx_success(inventory_service, mock_stockx_service):
    """
    Tests successful sync: 1 new item created, 1 updated, 1 skipped.
    """
    product_id = uuid4()
    category_id = uuid4()

    # --- Arrange ---

    # 1. Mock existing product and its inventory
    existing_item = InventoryItem(id=uuid4(), external_ids={"stockx": "variant-existing"})
    product = Product(
        id=product_id, sku="TEST-SKU", category_id=category_id, inventory_items=[existing_item]
    )
    inventory_service.product_repo.get_with_inventory.return_value = product

    # 2. Mock StockX API response
    stockx_variants = [
        {"variantId": "variant-existing", "variantValue": "9"},  # Should be updated
        {"variantId": "variant-new", "variantValue": "10"},  # Should be created
        {"variantValue": "11"},  # No ID, should be skipped
    ]

    # 3. Mock Size repository
    inventory_service.size_repo.find_one_or_create = AsyncMock(return_value=Size(id=uuid4()))

    # 4. Configure the mock for StockXService
    mock_stockx_service.get_all_product_variants = AsyncMock(return_value=stockx_variants)

    # --- Act ---
    stats = await inventory_service.sync_inventory_from_stockx(product_id)

    # --- Assert ---
    inventory_service.product_repo.get_with_inventory.assert_called_once_with(product_id)
    mock_stockx_service.get_all_product_variants.assert_called_once_with("TEST-SKU")

    # Check that one new item was added to the session
    assert inventory_service.db_session.add.call_count == 1
    new_item_call = inventory_service.db_session.add.call_args[0][0]
    assert isinstance(new_item_call, InventoryItem)
    assert new_item_call.external_ids == {"stockx": "variant-new"}
    assert new_item_call.quantity == 0

    # Check that the size repo was called for the new item
    inventory_service.size_repo.find_one_or_create.assert_called_once_with(
        {"value": "10", "region": "US"}, category_id=category_id
    )

    # Check that the session was committed
    inventory_service.db_session.commit.assert_called_once()

    # Check the returned stats
    assert stats == {"created": 1, "updated": 1, "skipped": 1}


async def test_sync_inventory_from_stockx_update_existing(inventory_service, mock_stockx_service):
    """
    Tests that an existing inventory item is correctly updated.
    """
    product_id = uuid4()
    category_id = uuid4()

    # --- Arrange ---

    # 1. Mock existing product and its inventory
    existing_item = InventoryItem(
        id=uuid4(), external_ids={"stockx": "variant-existing"}, quantity=5
    )
    product = Product(
        id=product_id, sku="TEST-SKU", category_id=category_id, inventory_items=[existing_item]
    )
    inventory_service.product_repo.get_with_inventory.return_value = product

    # 2. Mock StockX API response
    stockx_variants = [
        {"variantId": "variant-existing", "variantValue": "9"},  # Should be updated
    ]

    # 3. Mock Size repository
    inventory_service.size_repo.find_one_or_create = AsyncMock(return_value=Size(id=uuid4()))

    # 4. Configure the mock for StockXService
    mock_stockx_service.get_all_product_variants = AsyncMock(return_value=stockx_variants)

    # --- Act ---
    stats = await inventory_service.sync_inventory_from_stockx(product_id)

    # --- Assert ---
    inventory_service.product_repo.get_with_inventory.assert_called_once_with(product_id)
    mock_stockx_service.get_all_product_variants.assert_called_once_with("TEST-SKU")

    # Check that no new item was added to the session
    inventory_service.db_session.add.assert_not_called()

    # Check that the session was committed
    inventory_service.db_session.commit.assert_called_once()

    # Check the returned stats
    assert stats == {"created": 0, "updated": 1, "skipped": 0}


async def test_get_inventory_overview(inventory_service):
    """
    Tests the get_inventory_overview method.
    """
    # Arrange
    inventory_service.inventory_repo.get_all = AsyncMock(
        return_value=[
            InventoryItem(status="in_stock", purchase_price=100),
            InventoryItem(status="in_stock", purchase_price=200),
            InventoryItem(status="sold", purchase_price=150),
            InventoryItem(status="listed_stockx", purchase_price=250),
        ]
    )

    # Act
    stats = await inventory_service.get_inventory_overview()

    # Assert
    assert stats.total_items == 4
    assert stats.in_stock == 2
    assert stats.sold == 1
    assert stats.listed == 1
    assert stats.total_value == 300
    assert stats.avg_purchase_price == 175


async def test_create_product_with_inventory(inventory_service):
    """
    Tests the create_product_with_inventory method.
    """
    # Arrange
    product_request = MagicMock()
    product_request.brand_name = "Test Brand"
    product_request.category_name = "Test Category"
    product_request.sku = "TEST-SKU"

    inventory_requests = [MagicMock()]

    inventory_service.brand_repo.find_one_or_create = AsyncMock(return_value=Brand(id=uuid4()))
    inventory_service.category_repo.find_one_or_create = AsyncMock(
        return_value=Category(id=uuid4())
    )
    inventory_service.product_repo.find_by_sku = AsyncMock(return_value=None)
    inventory_service.size_repo.find_one_or_create = AsyncMock(return_value=Size(id=uuid4()))
    inventory_service.product_repo.create_with_inventory = AsyncMock(
        return_value=Product(id=uuid4(), sku="TEST-SKU")
    )

    # Act
    product = await inventory_service.create_product_with_inventory(
        product_request, inventory_requests
    )

    # Assert
    assert product["sku"] == "TEST-SKU"
    inventory_service.product_repo.create_with_inventory.assert_called_once()


async def test_update_inventory_status(inventory_service):
    """
    Tests the update_inventory_status method.
    """
    # Arrange
    inventory_id = uuid4()
    new_status = "sold"
    inventory_service.product_repo.update_inventory_status = AsyncMock(return_value=True)

    # Act
    result = await inventory_service.update_inventory_status(inventory_id, new_status)

    # Assert
    assert result is True
    inventory_service.product_repo.update_inventory_status.assert_called_once_with(
        inventory_id, new_status, None
    )


async def test_get_low_stock_alert(inventory_service):
    """
    Tests the get_low_stock_alert method.
    """
    # Arrange
    inventory_service.product_repo.get_low_stock_products = AsyncMock(
        return_value=[{"name": "Test Product", "stock": 4}]
    )

    # Act
    low_stock_products = await inventory_service.get_low_stock_alert(threshold=5)

    # Assert
    assert len(low_stock_products) == 1
    assert low_stock_products[0]["name"] == "Test Product"
    inventory_service.product_repo.get_low_stock_products.assert_called_once_with(5)


async def test_search_products(inventory_service):
    """
    Tests the search_products method.
    """
    # Arrange
    inventory_service.product_repo.search = AsyncMock(return_value=[Product(name="Test Product")])

    # Act
    products = await inventory_service.search_products(search_term="Test")

    # Assert
    assert len(products) == 1
    assert products[0]["name"] == "Test Product"
    inventory_service.product_repo.search.assert_called_once()


async def test_sync_product_not_found(inventory_service):
    """
    Tests that the sync fails gracefully if the product is not found.
    """
    product_id = uuid4()
    inventory_service.product_repo.get_with_inventory.return_value = None

    with pytest.raises(ValueError, match=f"Product with ID {product_id} not found."):
        await inventory_service.sync_inventory_from_stockx(product_id)

    inventory_service.db_session.commit.assert_not_called()


async def test_sync_product_has_no_sku(inventory_service):
    """
    Tests that sync is skipped if the product has no SKU.
    """
    product_id = uuid4()
    product = Product(id=product_id, sku=None, inventory_items=[])
    inventory_service.product_repo.get_with_inventory.return_value = product

    stats = await inventory_service.sync_inventory_from_stockx(product_id)

    assert stats == {"created": 0, "updated": 0, "skipped": 0}
    inventory_service.db_session.commit.assert_not_called()


async def test_sync_no_variants_from_stockx(inventory_service, mock_stockx_service):
    """
    Tests that sync completes cleanly if StockX returns no variants.
    """
    product_id = uuid4()
    product = Product(id=product_id, sku="TEST-SKU", inventory_items=[])
    inventory_service.product_repo.get_with_inventory.return_value = product

    mock_stockx_service.get_all_product_variants = AsyncMock(return_value=[])

    stats = await inventory_service.sync_inventory_from_stockx(product_id)

    assert stats == {"created": 0, "updated": 0, "skipped": 0}
    inventory_service.db_session.commit.assert_not_called()

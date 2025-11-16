"""
Unit tests for InventoryRepository
Testing inventory domain-specific data access methods
"""

import uuid
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from domains.inventory.repositories.inventory_repository import (
    InventoryRepository,
    InventoryStats,
)


@pytest.fixture
def mock_db_session():
    """Create mock database session"""
    session = MagicMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    session.get = AsyncMock()
    return session


@pytest.fixture
def inventory_repo(mock_db_session):
    """Create InventoryRepository instance with mock session"""
    return InventoryRepository(mock_db_session)


class TestInventoryStats:
    """Test inventory statistics aggregation"""

    async def test_get_inventory_stats_with_data(self, inventory_repo, mock_db_session):
        """Test getting inventory statistics with data"""
        # Arrange
        mock_row = MagicMock()
        mock_row.total_items = 100
        mock_row.in_stock = 60
        mock_row.sold = 30
        mock_row.listed = 10
        mock_row.total_value = Decimal("15000.00")
        mock_row.avg_purchase_price = Decimal("150.00")

        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=mock_row)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await inventory_repo.get_inventory_stats()

        # Assert
        assert isinstance(result, InventoryStats)
        assert result.total_items == 100
        assert result.in_stock == 60
        assert result.sold == 30
        assert result.listed == 10
        assert result.total_value == Decimal("15000.00")
        assert result.avg_purchase_price == Decimal("150.00")
        mock_db_session.execute.assert_awaited_once()

    async def test_get_inventory_stats_empty(self, inventory_repo, mock_db_session):
        """Test getting inventory statistics with no data"""
        # Arrange
        mock_row = MagicMock()
        mock_row.total_items = None
        mock_row.in_stock = None
        mock_row.sold = None
        mock_row.listed = None
        mock_row.total_value = None
        mock_row.avg_purchase_price = None

        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=mock_row)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await inventory_repo.get_inventory_stats()

        # Assert
        assert result.total_items == 0
        assert result.in_stock == 0
        assert result.sold == 0
        assert result.listed == 0
        assert result.total_value == Decimal("0")
        assert result.avg_purchase_price == Decimal("0")


class TestStatusOperations:
    """Test status-related operations"""

    async def test_get_by_status_with_limit(self, inventory_repo, mock_db_session):
        """Test getting items by status with limit"""
        # Arrange
        mock_items = [
            MagicMock(id=uuid.uuid4(), status="in_stock"),
            MagicMock(id=uuid.uuid4(), status="in_stock"),
        ]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_items)
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await inventory_repo.get_by_status("in_stock", limit=10)

        # Assert
        assert len(result) == 2
        mock_db_session.execute.assert_awaited_once()

    async def test_get_by_status_no_limit(self, inventory_repo, mock_db_session):
        """Test getting items by status without limit"""
        # Arrange
        mock_items = []

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_items)
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await inventory_repo.get_by_status("sold")

        # Assert
        assert result == []

    async def test_update_status(self, inventory_repo, mock_db_session):
        """Test updating item status delegates to update method"""
        # Arrange
        item_id = uuid.uuid4()
        mock_item = MagicMock()
        mock_item.id = item_id

        # Mock the result of the update query (returns the updated entity)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_item)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await inventory_repo.update_status(item_id, "sold")

        # Assert - verify update was called and returned an item
        assert result is not None
        assert result.id == item_id
        mock_db_session.execute.assert_awaited()


class TestProductRelatedQueries:
    """Test queries involving product relationships"""

    async def test_get_with_product_details(self, inventory_repo, mock_db_session):
        """Test getting item with full product details and eager loading"""
        # Arrange
        item_id = uuid.uuid4()
        mock_item = MagicMock()
        mock_item.id = item_id
        mock_item.product = MagicMock()
        mock_item.product.brand = MagicMock()
        mock_item.product.category = MagicMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_item)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await inventory_repo.get_with_product_details(item_id)

        # Assert
        assert result == mock_item
        assert result.product is not None
        mock_db_session.execute.assert_awaited_once()

    async def test_get_with_product_details_not_found(self, inventory_repo, mock_db_session):
        """Test getting item with product details when item doesn't exist"""
        # Arrange
        item_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await inventory_repo.get_with_product_details(item_id)

        # Assert
        assert result is None

    async def test_get_by_sku(self, inventory_repo, mock_db_session):
        """Test getting items by product SKU"""
        # Arrange
        sku = "AIR-JORDAN-1"
        mock_items = [
            MagicMock(id=uuid.uuid4(), sku=sku),
            MagicMock(id=uuid.uuid4(), sku=sku),
        ]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_items)
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await inventory_repo.get_by_sku(sku)

        # Assert
        assert len(result) == 2
        mock_db_session.execute.assert_awaited_once()

    async def test_get_by_brand_with_limit(self, inventory_repo, mock_db_session):
        """Test getting items by brand name with limit"""
        # Arrange
        brand_name = "Nike"
        mock_items = [MagicMock(id=uuid.uuid4())]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_items)
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await inventory_repo.get_by_brand(brand_name, limit=5)

        # Assert
        assert len(result) == 1
        mock_db_session.execute.assert_awaited_once()

    async def test_get_by_brand_no_limit(self, inventory_repo, mock_db_session):
        """Test getting items by brand name without limit"""
        # Arrange
        brand_name = "Adidas"
        mock_items = []

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_items)
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await inventory_repo.get_by_brand(brand_name)

        # Assert
        assert result == []


class TestInventoryFiltering:
    """Test filtering and search operations"""

    async def test_get_low_stock_items_default_threshold(self, inventory_repo, mock_db_session):
        """Test getting low stock items with default threshold"""
        # Arrange
        mock_items = [MagicMock(id=uuid.uuid4(), quantity=0, status="in_stock")]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_items)
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await inventory_repo.get_low_stock_items()

        # Assert
        assert len(result) == 1
        mock_db_session.execute.assert_awaited_once()

    async def test_get_low_stock_items_custom_threshold(self, inventory_repo, mock_db_session):
        """Test getting low stock items with custom threshold"""
        # Arrange
        mock_items = []

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_items)
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await inventory_repo.get_low_stock_items(threshold=5)

        # Assert
        assert result == []

    async def test_get_items_by_date_range_both_dates(self, inventory_repo, mock_db_session):
        """Test getting items by date range with both start and end dates"""
        # Arrange
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)
        mock_items = [MagicMock(id=uuid.uuid4())]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_items)
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await inventory_repo.get_items_by_date_range(start_date, end_date)

        # Assert
        assert len(result) == 1
        mock_db_session.execute.assert_awaited_once()

    async def test_get_items_by_date_range_start_only(self, inventory_repo, mock_db_session):
        """Test getting items by date range with only start date"""
        # Arrange
        start_date = datetime(2024, 1, 1)
        mock_items = []

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_items)
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await inventory_repo.get_items_by_date_range(start_date=start_date)

        # Assert
        assert result == []

    async def test_get_items_by_date_range_end_only(self, inventory_repo, mock_db_session):
        """Test getting items by date range with only end date"""
        # Arrange
        end_date = datetime(2024, 12, 31)
        mock_items = [MagicMock(id=uuid.uuid4()), MagicMock(id=uuid.uuid4())]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_items)
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await inventory_repo.get_items_by_date_range(end_date=end_date)

        # Assert
        assert len(result) == 2

    async def test_get_items_by_date_range_no_dates(self, inventory_repo, mock_db_session):
        """Test getting items by date range with no dates (all items)"""
        # Arrange
        mock_items = [MagicMock(id=uuid.uuid4()) for _ in range(5)]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_items)
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await inventory_repo.get_items_by_date_range()

        # Assert
        assert len(result) == 5


class TestPagination:
    """Test pagination and filtering"""

    async def test_get_all_paginated_default_params(self, inventory_repo, mock_db_session):
        """Test paginated retrieval with default parameters"""
        # Arrange
        mock_items = [MagicMock(id=uuid.uuid4()) for _ in range(3)]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_items)
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await inventory_repo.get_all_paginated()

        # Assert
        assert len(result) == 3
        mock_db_session.execute.assert_awaited_once()

    async def test_get_all_paginated_with_skip_and_limit(self, inventory_repo, mock_db_session):
        """Test paginated retrieval with skip and limit"""
        # Arrange
        mock_items = [MagicMock(id=uuid.uuid4()) for _ in range(10)]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_items)
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await inventory_repo.get_all_paginated(skip=20, limit=10)

        # Assert
        assert len(result) == 10

    async def test_get_all_paginated_with_single_filter(self, inventory_repo, mock_db_session):
        """Test paginated retrieval with single filter"""
        # Arrange
        filters = {"status": "in_stock"}
        mock_items = [MagicMock(id=uuid.uuid4(), status="in_stock")]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_items)
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await inventory_repo.get_all_paginated(filters=filters)

        # Assert
        assert len(result) == 1

    async def test_get_all_paginated_with_list_filter(self, inventory_repo, mock_db_session):
        """Test paginated retrieval with list filter (IN clause)"""
        # Arrange
        filters = {"status": ["in_stock", "listed"]}
        mock_items = [MagicMock(id=uuid.uuid4()) for _ in range(2)]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_items)
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await inventory_repo.get_all_paginated(filters=filters)

        # Assert
        assert len(result) == 2

    async def test_get_all_paginated_with_multiple_filters(self, inventory_repo, mock_db_session):
        """Test paginated retrieval with multiple filters"""
        # Arrange
        filters = {"status": "in_stock", "condition": "new"}
        mock_items = []

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_items)
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await inventory_repo.get_all_paginated(filters=filters)

        # Assert
        assert result == []

    async def test_get_all_paginated_filters_none_values(self, inventory_repo, mock_db_session):
        """Test paginated retrieval ignoring None filter values"""
        # Arrange
        filters = {"status": "in_stock", "brand_id": None}
        mock_items = [MagicMock(id=uuid.uuid4())]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_items)
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await inventory_repo.get_all_paginated(filters=filters)

        # Assert
        assert len(result) == 1

    async def test_get_all_paginated_filters_invalid_field(self, inventory_repo, mock_db_session):
        """Test paginated retrieval ignoring invalid filter fields"""
        # Arrange
        filters = {"status": "in_stock", "invalid_field": "value"}
        mock_items = [MagicMock(id=uuid.uuid4())]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_items)
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await inventory_repo.get_all_paginated(filters=filters)

        # Assert
        assert len(result) == 1

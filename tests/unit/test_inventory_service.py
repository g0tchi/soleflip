"""
Unit Tests for Inventory Service
Tests business logic in isolation with mocked dependencies
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from decimal import Decimal
from datetime import datetime, timezone

from domains.inventory.services.inventory_service import (
    InventoryService,
    InventoryStats,
    ProductCreationRequest,
    InventoryItemRequest,
)
from domains.inventory.repositories.product_repository import ProductRepository
from domains.inventory.repositories.base_repository import BaseRepository
from shared.database.models import Product, InventoryItem, Brand, Category, Size


@pytest.mark.unit
class TestInventoryService:
    """Test suite for InventoryService"""

    @pytest.fixture
    def mock_db_session(self):
        """Provides a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def inventory_service(self, mock_db_session):
        """Create inventory service instance with mocked session."""
        service = InventoryService(mock_db_session)
        service.product_repo = AsyncMock(spec=ProductRepository)
        service.brand_repo = AsyncMock(spec=BaseRepository)
        service.category_repo = AsyncMock(spec=BaseRepository)
        service.size_repo = AsyncMock(spec=BaseRepository)
        service.inventory_repo = AsyncMock(spec=BaseRepository)
        return service

    @pytest.fixture
    def mock_inventory_items(self):
        """Mock inventory items for testing."""
        return [
            MagicMock(spec=InventoryItem, id=uuid4(), status='in_stock', purchase_price=Decimal('100.00')),
            MagicMock(spec=InventoryItem, id=uuid4(), status='sold', purchase_price=Decimal('120.00')),
            MagicMock(spec=InventoryItem, id=uuid4(), status='listed_stockx', purchase_price=Decimal('110.00')),
        ]

    async def test_get_inventory_overview_success(self, inventory_service, mock_inventory_items):
        """Test successful inventory overview generation."""
        inventory_service.inventory_repo.get_all.return_value = mock_inventory_items

        stats = await inventory_service.get_inventory_overview()

        assert isinstance(stats, InventoryStats)
        assert stats.total_items == 3
        assert stats.in_stock == 1
        assert stats.sold == 1
        assert stats.listed == 1
        assert stats.total_value == Decimal('100.00')
        avg_price = (Decimal('100.00') + Decimal('120.00') + Decimal('110.00')) / 3
        assert stats.avg_purchase_price == avg_price

    async def test_get_inventory_overview_empty(self, inventory_service):
        """Test inventory overview with no items."""
        inventory_service.inventory_repo.get_all.return_value = []

        stats = await inventory_service.get_inventory_overview()

        assert stats.total_items == 0
        assert stats.total_value == Decimal('0')
        assert stats.avg_purchase_price == Decimal('0')

    async def test_create_product_with_inventory_success(self, inventory_service):
        """Test successful product creation with inventory."""
        product_request = ProductCreationRequest(
            sku="TEST-001", name="Test Product", brand_name="Nike", category_name="Sneakers"
        )
        inventory_requests = [
            InventoryItemRequest(
                product_id=uuid4(), size_value="US 9", size_region="US", quantity=1
            )
        ]
        
        mock_product_instance = MagicMock(spec=Product)
        mock_product_instance.to_dict.return_value = {
            "sku": "TEST-001", "name": "Test Product"
        }

        inventory_service.brand_repo.find_one_or_create.return_value = Brand(id=uuid4(), name="Nike")
        inventory_service.category_repo.find_one_or_create.return_value = Category(id=uuid4(), name="Sneakers")
        inventory_service.product_repo.find_by_sku.return_value = None
        inventory_service.size_repo.find_one_or_create.return_value = Size(id=uuid4(), value="US 9")
        inventory_service.product_repo.create_with_inventory.return_value = mock_product_instance

        result = await inventory_service.create_product_with_inventory(
            product_request, inventory_requests
        )

        assert result['name'] == "Test Product"
        inventory_service.product_repo.create_with_inventory.assert_called_once()


    async def test_create_product_duplicate_sku(self, inventory_service):
        """Test product creation with duplicate SKU."""
        product_request = ProductCreationRequest(
            sku="DUPLICATE-001", name="Duplicate", brand_name="Nike", category_name="Sneakers"
        )
        
        inventory_service.brand_repo.find_one_or_create.return_value = Brand(id=uuid4(), name="Nike")
        inventory_service.category_repo.find_one_or_create.return_value = Category(id=uuid4(), name="Sneakers")
        inventory_service.product_repo.find_by_sku.return_value = Product(sku="DUPLICATE-001")

        with pytest.raises(ValueError, match="already exists"):
            await inventory_service.create_product_with_inventory(product_request, [])


    async def test_update_inventory_status_success(self, inventory_service):
        """Test successful inventory status update."""
        inventory_id = uuid4()
        inventory_service.product_repo.update_inventory_status.return_value = True

        result = await inventory_service.update_inventory_status(inventory_id, "sold", "note")

        assert result is True
        inventory_service.product_repo.update_inventory_status.assert_called_once_with(
            inventory_id, "sold", "note"
        )

    async def test_update_inventory_status_invalid_status(self, inventory_service):
        """Test inventory status update with invalid status."""
        with pytest.raises(ValueError, match="Invalid status"):
            await inventory_service.update_inventory_status(uuid4(), "invalid_status")

    def _create_mock_product(self, name: str, sku: str) -> MagicMock:
        """Helper to create a mock product with a to_dict method."""
        mock_product = MagicMock(spec=Product)
        mock_product.to_dict.return_value = {"name": name, "sku": sku}
        return mock_product

    async def test_search_products(self, inventory_service):
        """Test product search functionality."""
        mock_product = self._create_mock_product("Searchable Product", "SEARCH-001")
        inventory_service.product_repo.search.return_value = [mock_product]

        result = await inventory_service.search_products(search_term="Searchable")

        assert len(result) == 1
        assert result[0]['name'] == 'Searchable Product'
        inventory_service.product_repo.search.assert_called_once()

    async def test_get_product_details_success(self, inventory_service):
        """Test successful product details retrieval."""
        product_id = uuid4()
        
        mock_product = self._create_mock_product("Detailed Product", "DETAIL-001")
        
        mock_inventory_item = MagicMock(spec=InventoryItem)
        mock_inventory_item.to_dict.return_value = {"size": "9"}
        mock_product.inventory_items = [mock_inventory_item]

        inventory_service.product_repo.get_with_inventory.return_value = mock_product

        result = await inventory_service.get_product_details(product_id)

        assert result['name'] == 'Detailed Product'
        assert len(result['inventory_items']) == 1
        assert result['inventory_items'][0]['size'] == '9'
        inventory_service.product_repo.get_with_inventory.assert_called_once_with(product_id)

    async def test_get_product_details_not_found(self, inventory_service):
        """Test product details retrieval for non-existent product."""
        product_id = uuid4()
        inventory_service.product_repo.get_with_inventory.return_value = None

        result = await inventory_service.get_product_details(product_id)

        assert result is None
"""
Unit Tests for Inventory Service
Tests business logic in isolation with mocked dependencies
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from decimal import Decimal
from datetime import datetime, timezone

from domains.inventory.services.inventory_service import (
    InventoryService, 
    InventoryStats,
    ProductCreationRequest,
    InventoryItemRequest
)
from shared.error_handling.exceptions import (
    ValidationException,
    ResourceNotFoundException,
    DuplicateResourceException
)

@pytest.mark.unit
class TestInventoryService:
    """Test suite for InventoryService"""
    
    @pytest.fixture
    def inventory_service(self):
        """Create inventory service instance"""
        return InventoryService()
    
    @pytest.fixture
    def mock_inventory_items(self):
        """Mock inventory items for testing"""
        return [
            MagicMock(
                id=uuid4(),
                status='in_stock',
                purchase_price=Decimal('100.00')
            ),
            MagicMock(
                id=uuid4(),
                status='sold',
                purchase_price=Decimal('120.00')
            ),
            MagicMock(
                id=uuid4(),
                status='listed_stockx',
                purchase_price=Decimal('110.00')
            ),
        ]
    
    async def test_get_inventory_overview_success(self, inventory_service, mock_inventory_items):
        """Test successful inventory overview generation"""
        
        with patch('domains.inventory.services.inventory_service.get_db_session') as mock_db:
            # Setup mock
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            # Mock repository
            with patch('domains.inventory.services.inventory_service.BaseRepository') as mock_repo:
                mock_repo_instance = AsyncMock()
                mock_repo.return_value = mock_repo_instance
                mock_repo_instance.get_all.return_value = mock_inventory_items
                
                # Execute
                stats = await inventory_service.get_inventory_overview()
                
                # Assertions
                assert isinstance(stats, InventoryStats)
                assert stats.total_items == 3
                assert stats.in_stock == 1
                assert stats.sold == 1
                assert stats.listed == 1
                assert stats.total_value == Decimal('100.00')  # Only in_stock items
                assert stats.avg_purchase_price == Decimal('110.00')  # Average of all items
    
    async def test_get_inventory_overview_empty(self, inventory_service):
        """Test inventory overview with no items"""
        
        with patch('domains.inventory.services.inventory_service.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            with patch('domains.inventory.services.inventory_service.BaseRepository') as mock_repo:
                mock_repo_instance = AsyncMock()
                mock_repo.return_value = mock_repo_instance
                mock_repo_instance.get_all.return_value = []
                
                # Execute
                stats = await inventory_service.get_inventory_overview()
                
                # Assertions
                assert stats.total_items == 0
                assert stats.in_stock == 0
                assert stats.sold == 0
                assert stats.listed == 0
                assert stats.total_value == Decimal('0')
                assert stats.avg_purchase_price == Decimal('0')
    
    async def test_create_product_with_inventory_success(self, inventory_service):
        """Test successful product creation with inventory"""
        
        # Test data
        product_request = ProductCreationRequest(
            sku="TEST-001",
            name="Test Product",
            brand_name="Nike",
            category_name="Sneakers",
            retail_price=Decimal('150.00')
        )
        
        inventory_requests = [
            InventoryItemRequest(
                product_id=uuid4(),
                size_value="US 9",
                size_region="US",
                quantity=1,
                purchase_price=Decimal('120.00')
            )
        ]
        
        with patch('domains.inventory.services.inventory_service.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            # Mock repositories
            mock_product_repo = AsyncMock()
            mock_brand_repo = AsyncMock()
            mock_category_repo = AsyncMock()
            mock_size_repo = AsyncMock()
            
            # Mock brand creation
            mock_brand = MagicMock(id=uuid4(), name="Nike")
            mock_brand_repo.find_one_by_field.return_value = None
            mock_brand_repo.create.return_value = mock_brand
            
            # Mock category creation
            mock_category = MagicMock(id=uuid4(), name="Sneakers")
            mock_category_repo.find_one_by_field.return_value = None
            mock_category_repo.create.return_value = mock_category
            
            # Mock size creation
            mock_size = MagicMock(id=uuid4(), value="US 9")
            mock_size_repo.find_one_by_field.return_value = None
            mock_size_repo.create.return_value = mock_size
            
            # Mock product creation
            mock_product = MagicMock(id=uuid4(), sku="TEST-001", name="Test Product")
            mock_product_repo.find_by_sku.return_value = None
            mock_product_repo.create_with_inventory.return_value = mock_product
            
            with patch('domains.inventory.services.inventory_service.ProductRepository', return_value=mock_product_repo), \
                 patch('domains.inventory.services.inventory_service.BaseRepository') as mock_base_repo:
                
                # Setup BaseRepository mock to return different instances
                mock_base_repo.side_effect = [
                    mock_brand_repo,
                    mock_category_repo, 
                    mock_size_repo
                ]
                
                # Execute
                result = await inventory_service.create_product_with_inventory(
                    product_request, inventory_requests
                )
                
                # Assertions
                assert result['product_id'] == str(mock_product.id)
                assert result['sku'] == "TEST-001"
                assert result['name'] == "Test Product"
                assert result['brand'] == "Nike"
                assert result['category'] == "Sneakers"
                assert result['inventory_items_created'] == 1
                
                # Verify repository calls
                mock_brand_repo.create.assert_called_once()
                mock_category_repo.create.assert_called_once()
                mock_size_repo.create.assert_called_once()
                mock_product_repo.create_with_inventory.assert_called_once()
    
    async def test_create_product_duplicate_sku(self, inventory_service):
        """Test product creation with duplicate SKU"""
        
        product_request = ProductCreationRequest(
            sku="DUPLICATE-001",
            name="Duplicate Product",
            brand_name="Nike",
            category_name="Sneakers"
        )
        
        with patch('domains.inventory.services.inventory_service.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            # Mock existing product
            mock_existing_product = MagicMock(sku="DUPLICATE-001")
            
            with patch('domains.inventory.services.inventory_service.ProductRepository') as mock_repo:
                mock_repo_instance = AsyncMock()
                mock_repo.return_value = mock_repo_instance
                mock_repo_instance.find_by_sku.return_value = mock_existing_product
                
                # Execute and expect exception
                with pytest.raises(ValueError, match="already exists"):
                    await inventory_service.create_product_with_inventory(
                        product_request, []
                    )
    
    async def test_update_inventory_status_success(self, inventory_service):
        """Test successful inventory status update"""
        
        inventory_id = uuid4()
        new_status = "sold"
        notes = "Sold on StockX"
        
        with patch('domains.inventory.services.inventory_service.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            with patch('domains.inventory.services.inventory_service.ProductRepository') as mock_repo:
                mock_repo_instance = AsyncMock()
                mock_repo.return_value = mock_repo_instance
                mock_repo_instance.update_inventory_status.return_value = True
                
                # Execute
                result = await inventory_service.update_inventory_status(
                    inventory_id, new_status, notes
                )
                
                # Assertions
                assert result is True
                mock_repo_instance.update_inventory_status.assert_called_once_with(
                    inventory_id, new_status, notes
                )
    
    async def test_update_inventory_status_invalid_status(self, inventory_service):
        """Test inventory status update with invalid status"""
        
        inventory_id = uuid4()
        invalid_status = "invalid_status"
        
        # Execute and expect exception
        with pytest.raises(ValueError, match="Invalid status"):
            await inventory_service.update_inventory_status(
                inventory_id, invalid_status
            )
    
    async def test_update_inventory_status_not_found(self, inventory_service):
        """Test inventory status update for non-existent item"""
        
        inventory_id = uuid4()
        new_status = "sold"
        
        with patch('domains.inventory.services.inventory_service.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            with patch('domains.inventory.services.inventory_service.ProductRepository') as mock_repo:
                mock_repo_instance = AsyncMock()
                mock_repo.return_value = mock_repo_instance
                mock_repo_instance.update_inventory_status.return_value = False
                
                # Execute
                result = await inventory_service.update_inventory_status(
                    inventory_id, new_status
                )
                
                # Assertions
                assert result is False
    
    async def test_get_low_stock_alert(self, inventory_service):
        """Test low stock alert generation"""
        
        mock_low_stock_products = [
            {
                'product_id': str(uuid4()),
                'name': 'Low Stock Product',
                'sku': 'LOW-001',
                'brand_name': 'Nike',
                'stock_count': 2
            }
        ]
        
        with patch('domains.inventory.services.inventory_service.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            with patch('domains.inventory.services.inventory_service.ProductRepository') as mock_repo:
                mock_repo_instance = AsyncMock()
                mock_repo.return_value = mock_repo_instance
                mock_repo_instance.get_low_stock_products.return_value = mock_low_stock_products
                
                # Execute
                result = await inventory_service.get_low_stock_alert(threshold=5)
                
                # Assertions
                assert result == mock_low_stock_products
                mock_repo_instance.get_low_stock_products.assert_called_once_with(5)
    
    async def test_search_products(self, inventory_service):
        """Test product search functionality"""
        
        mock_products = [
            MagicMock(
                id=uuid4(),
                sku='SEARCH-001',
                name='Searchable Product',
                brand=MagicMock(name='Nike'),
                category=MagicMock(name='Sneakers'),
                retail_price=Decimal('150.00'),
                release_date=datetime.now(timezone.utc)
            )
        ]
        
        with patch('domains.inventory.services.inventory_service.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            with patch('domains.inventory.services.inventory_service.ProductRepository') as mock_repo:
                mock_repo_instance = AsyncMock()
                mock_repo.return_value = mock_repo_instance
                mock_repo_instance.search.return_value = mock_products
                
                # Execute
                result = await inventory_service.search_products(
                    search_term="Searchable",
                    brand_filter="Nike",
                    limit=10
                )
                
                # Assertions
                assert len(result) == 1
                assert result[0]['sku'] == 'SEARCH-001'
                assert result[0]['name'] == 'Searchable Product'
                assert result[0]['brand'] == 'Nike'
                assert result[0]['category'] == 'Sneakers'
                
                mock_repo_instance.search.assert_called_once_with(
                    search_term="Searchable",
                    brand_filter="Nike",
                    category_filter=None,
                    limit=10,
                    offset=0
                )
    
    async def test_get_product_details_success(self, inventory_service):
        """Test successful product details retrieval"""
        
        product_id = uuid4()
        mock_inventory_item = MagicMock(
            id=uuid4(),
            size=MagicMock(value="US 9", region="US"),
            quantity=1,
            status="in_stock",
            purchase_price=Decimal('120.00'),
            purchase_date=datetime.now(timezone.utc),
            supplier="Test Supplier",
            notes="Test notes"
        )
        
        mock_product = MagicMock(
            id=product_id,
            sku='DETAIL-001',
            name='Detailed Product',
            description='Product description',
            brand=MagicMock(name='Nike'),
            category=MagicMock(name='Sneakers'),
            retail_price=Decimal('150.00'),
            release_date=datetime.now(timezone.utc),
            inventory_items=[mock_inventory_item]
        )
        
        with patch('domains.inventory.services.inventory_service.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            with patch('domains.inventory.services.inventory_service.ProductRepository') as mock_repo:
                mock_repo_instance = AsyncMock()
                mock_repo.return_value = mock_repo_instance
                mock_repo_instance.get_with_inventory.return_value = mock_product
                
                # Execute
                result = await inventory_service.get_product_details(product_id)
                
                # Assertions
                assert result is not None
                assert result['id'] == str(product_id)
                assert result['sku'] == 'DETAIL-001'
                assert result['name'] == 'Detailed Product'
                assert result['brand'] == 'Nike'
                assert result['category'] == 'Sneakers'
                assert result['total_items'] == 1
                assert result['in_stock_count'] == 1
                assert len(result['inventory_items']) == 1
                
                inventory_item = result['inventory_items'][0]
                assert inventory_item['size'] == 'US 9'
                assert inventory_item['status'] == 'in_stock'
    
    async def test_get_product_details_not_found(self, inventory_service):
        """Test product details retrieval for non-existent product"""
        
        product_id = uuid4()
        
        with patch('domains.inventory.services.inventory_service.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            with patch('domains.inventory.services.inventory_service.ProductRepository') as mock_repo:
                mock_repo_instance = AsyncMock()
                mock_repo.return_value = mock_repo_instance
                mock_repo_instance.get_with_inventory.return_value = None
                
                # Execute
                result = await inventory_service.get_product_details(product_id)
                
                # Assertions
                assert result is None

@pytest.mark.unit
class TestInventoryServiceDataClasses:
    """Test data classes used by inventory service"""
    
    def test_inventory_stats_creation(self):
        """Test InventoryStats data class"""
        stats = InventoryStats(
            total_items=10,
            in_stock=5,
            sold=3,
            listed=2,
            total_value=Decimal('1000.00'),
            avg_purchase_price=Decimal('100.00')
        )
        
        assert stats.total_items == 10
        assert stats.in_stock == 5
        assert stats.sold == 3
        assert stats.listed == 2
        assert stats.total_value == Decimal('1000.00')
        assert stats.avg_purchase_price == Decimal('100.00')
    
    def test_product_creation_request(self):
        """Test ProductCreationRequest data class"""
        request = ProductCreationRequest(
            sku="TEST-001",
            name="Test Product",
            brand_name="Nike",
            category_name="Sneakers",
            description="Test description",
            retail_price=Decimal('150.00')
        )
        
        assert request.sku == "TEST-001"
        assert request.name == "Test Product"
        assert request.brand_name == "Nike"
        assert request.category_name == "Sneakers"
        assert request.description == "Test description"
        assert request.retail_price == Decimal('150.00')
    
    def test_inventory_item_request(self):
        """Test InventoryItemRequest data class"""
        product_id = uuid4()
        request = InventoryItemRequest(
            product_id=product_id,
            size_value="US 9",
            size_region="US",
            quantity=1,
            purchase_price=Decimal('120.00'),
            supplier="Test Supplier"
        )
        
        assert request.product_id == product_id
        assert request.size_value == "US 9"
        assert request.size_region == "US"
        assert request.quantity == 1
        assert request.purchase_price == Decimal('120.00')
        assert request.supplier == "Test Supplier"
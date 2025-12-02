"""
Tests for Phase 2 Inventory Features (Stock Reservations & Metrics)
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from domains.inventory.services.inventory_service import InventoryService
from shared.database.models import InventoryItem, Product, Size


@pytest.fixture
async def inventory_service(db_session: AsyncSession):
    """Create inventory service instance"""
    return InventoryService(db_session)


@pytest.fixture
async def sample_inventory_item(db_session: AsyncSession):
    """Create a sample inventory item for testing"""
    # Create category (required for Product)
    from shared.database.models import Category

    # Use unique slug for each test to avoid UNIQUE constraint violations
    unique_slug = f"test-category-{uuid4().hex[:8]}"
    category = Category(name="Test Category", slug=unique_slug)
    db_session.add(category)
    await db_session.flush()

    # Create product with unique SKU
    unique_sku = f"TEST-PRODUCT-{uuid4().hex[:8]}"
    product = Product(
        sku=unique_sku,
        name="Test Product",
        description="Test product for Phase 2 testing",
        category_id=category.id,
    )
    db_session.add(product)
    await db_session.flush()

    # Create size
    size = Size(value="10", region="US", category_id=category.id)
    db_session.add(size)
    await db_session.flush()

    # Create inventory item with Phase 2 fields
    item = InventoryItem(
        product_id=product.id,
        size_id=size.id,
        quantity=10,
        reserved_quantity=0,
        status="in_stock",
        purchase_price=Decimal("100.00"),
        location="Warehouse A",
        listed_on_platforms=[],  # Initialize empty
        status_history=[],  # Initialize empty
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)

    return item


@pytest.mark.unit
@pytest.mark.asyncio
class TestStockReservations:
    """Tests for stock reservation functionality"""

    async def test_reserve_stock_success(self, inventory_service, sample_inventory_item):
        """Test successful stock reservation"""
        item_id = sample_inventory_item.id
        quantity_to_reserve = 3

        # Reserve stock
        success = await inventory_service.reserve_inventory_stock(
            item_id, quantity_to_reserve, reason="Order #12345"
        )

        assert success is True

        # Verify reservation
        item = await inventory_service.inventory_repo.get_by_id(item_id)
        assert item.reserved_quantity == quantity_to_reserve
        assert item.available_quantity == 7  # 10 - 3

    async def test_reserve_stock_insufficient_quantity(
        self, inventory_service, sample_inventory_item
    ):
        """Test reservation with insufficient available quantity"""
        item_id = sample_inventory_item.id

        # Try to reserve more than available
        success = await inventory_service.reserve_inventory_stock(item_id, 15)

        assert success is False

        # Verify no reservation was made
        item = await inventory_service.inventory_repo.get_by_id(item_id)
        assert item.reserved_quantity == 0

    async def test_reserve_stock_multiple_times(self, inventory_service, sample_inventory_item):
        """Test multiple reservations"""
        item_id = sample_inventory_item.id

        # First reservation
        success1 = await inventory_service.reserve_inventory_stock(item_id, 3)
        assert success1 is True

        # Second reservation
        success2 = await inventory_service.reserve_inventory_stock(item_id, 2)
        assert success2 is True

        # Verify total reservations
        item = await inventory_service.inventory_repo.get_by_id(item_id)
        assert item.reserved_quantity == 5
        assert item.available_quantity == 5

    async def test_release_reservation_success(self, inventory_service, sample_inventory_item):
        """Test successful release of reservation"""
        item_id = sample_inventory_item.id

        # Reserve first
        await inventory_service.reserve_inventory_stock(item_id, 5)

        # Release
        success = await inventory_service.release_inventory_reservation(
            item_id, 3, reason="Order cancelled"
        )

        assert success is True

        # Verify release
        item = await inventory_service.inventory_repo.get_by_id(item_id)
        assert item.reserved_quantity == 2  # 5 - 3
        assert item.available_quantity == 8  # 10 - 2

    async def test_release_reservation_invalid_quantity(
        self, inventory_service, sample_inventory_item
    ):
        """Test release with quantity > reserved"""
        item_id = sample_inventory_item.id

        # Reserve 3 units
        await inventory_service.reserve_inventory_stock(item_id, 3)

        # Try to release more than reserved
        success = await inventory_service.release_inventory_reservation(item_id, 5)

        assert success is False

        # Verify reservation unchanged
        item = await inventory_service.inventory_repo.get_by_id(item_id)
        assert item.reserved_quantity == 3

    async def test_reserve_stock_nonexistent_item(self, inventory_service):
        """Test reservation for non-existent item"""
        fake_id = uuid4()
        success = await inventory_service.reserve_inventory_stock(fake_id, 1)

        assert success is False


@pytest.mark.unit
@pytest.mark.asyncio
class TestStatusHistory:
    """Tests for status history tracking"""

    async def test_status_change_tracking(self, inventory_service, sample_inventory_item):
        """Test that status changes are tracked in history"""
        item_id = sample_inventory_item.id

        # Update status
        await inventory_service.update_inventory_status(
            item_id, "listed_stockx", "Listed on StockX"
        )

        # Verify status history
        item = await inventory_service.inventory_repo.get_by_id(item_id)
        assert item.status == "listed_stockx"
        assert len(item.status_history) > 0

        # Check history entry
        latest_history = item.status_history[-1]
        assert latest_history["from_status"] == "in_stock"
        assert latest_history["to_status"] == "listed_stockx"
        assert latest_history["reason"] == "Listed on StockX"  # "reason" not "notes"
        assert "changed_at" in latest_history  # "changed_at" not "timestamp"

    async def test_multiple_status_changes(self, inventory_service, sample_inventory_item):
        """Test tracking multiple status changes"""
        item_id = sample_inventory_item.id

        # Make multiple status changes
        await inventory_service.update_inventory_status(item_id, "listed_stockx")
        await inventory_service.update_inventory_status(item_id, "sold", "Sold to customer")

        # Verify history
        item = await inventory_service.inventory_repo.get_by_id(item_id)
        assert len(item.status_history) >= 2
        assert item.status_history[-1]["to_status"] == "sold"


@pytest.mark.unit
@pytest.mark.asyncio
class TestPlatformListings:
    """Tests for platform listing tracking"""

    async def test_add_platform_listing(self, db_session, sample_inventory_item):
        """Test adding platform listing to item"""
        item = sample_inventory_item

        # Add StockX listing
        item.add_platform_listing(
            platform="stockx",
            listing_id="stockx-12345",
            ask_price=150.00,
            metadata={"currency": "EUR", "status": "ACTIVE"},
        )

        await db_session.commit()
        await db_session.refresh(item)

        # Verify listing was added
        assert len(item.listed_on_platforms) == 1
        listing = item.listed_on_platforms[0]
        assert listing["platform"] == "stockx"
        assert listing["listing_id"] == "stockx-12345"
        assert listing["ask_price"] == 150.00
        assert "timestamp" in listing

    async def test_multiple_platform_listings(self, db_session, sample_inventory_item):
        """Test tracking listings on multiple platforms"""
        item = sample_inventory_item

        # Add listings on different platforms
        item.add_platform_listing("stockx", "stockx-123", 150.00)
        item.add_platform_listing("ebay", "ebay-456", 145.00)
        item.add_platform_listing("alias", "alias-789", 155.00)

        await db_session.commit()
        await db_session.refresh(item)

        # Verify all listings
        assert len(item.listed_on_platforms) == 3
        platforms = {listing["platform"] for listing in item.listed_on_platforms}
        assert platforms == {"stockx", "ebay", "alias"}


@pytest.mark.unit
@pytest.mark.asyncio
class TestStockMetrics:
    """Tests for stock metrics functionality"""

    async def test_get_stock_metrics_summary(self, inventory_service, sample_inventory_item):
        """Test retrieving stock metrics summary"""
        # Reserve some stock
        await inventory_service.reserve_inventory_stock(sample_inventory_item.id, 3)

        # Get metrics
        metrics = await inventory_service.get_stock_metrics_summary()

        assert metrics is not None
        assert "total_items" in metrics
        assert "in_stock" in metrics
        assert "sold" in metrics
        assert "listed" in metrics
        assert "total_value" in metrics
        assert "avg_purchase_price" in metrics
        assert isinstance(metrics["total_items"], int)
        assert metrics["total_items"] >= 1  # At least our sample item

    async def test_get_low_stock_items(self, inventory_service, db_session):
        """Test retrieving items with low stock"""
        # Create category
        from shared.database.models import Category

        # Use unique slug to avoid UNIQUE constraint violations
        unique_slug = f"low-stock-category-{uuid4().hex[:8]}"
        category = Category(name="Low Stock Category", slug=unique_slug)
        db_session.add(category)
        await db_session.flush()

        # Create product with low stock and unique SKU
        unique_sku = f"LOW-STOCK-{uuid4().hex[:8]}"
        product = Product(sku=unique_sku, name="Low Stock Product", category_id=category.id)
        db_session.add(product)
        await db_session.flush()

        size = Size(value="10", region="US", category_id=category.id)
        db_session.add(size)
        await db_session.flush()

        # Create item with 2 units (below threshold of 5)
        low_stock_item = InventoryItem(
            product_id=product.id,
            size_id=size.id,
            quantity=2,
            reserved_quantity=0,
            status="in_stock",
            purchase_price=Decimal("100.00"),
        )
        db_session.add(low_stock_item)
        await db_session.commit()

        # Get low stock items
        items = await inventory_service.get_low_stock_items_with_reservations(threshold=5)

        assert len(items) > 0
        # Verify our low stock item is included
        item_ids = [item["id"] for item in items]
        assert str(low_stock_item.id) in item_ids

    async def test_low_stock_with_reservations(
        self, inventory_service, sample_inventory_item, db_session
    ):
        """Test low stock detection considers reservations"""
        item_id = sample_inventory_item.id

        # Reserve stock to bring available below threshold
        # Item has 10 total, reserve 7 to leave 3 available (below threshold of 5)
        await inventory_service.reserve_inventory_stock(item_id, 7)

        # Commit the reservation to ensure it's persisted
        await db_session.commit()

        # Get low stock items
        items = await inventory_service.get_low_stock_items_with_reservations(threshold=5)

        # Should include our item
        item_ids = [item["id"] for item in items]
        assert str(item_id) in item_ids


@pytest.mark.unit
@pytest.mark.asyncio
class TestAvailableQuantity:
    """Tests for available_quantity property"""

    async def test_available_quantity_no_reservations(self, sample_inventory_item):
        """Test available quantity with no reservations"""
        item = sample_inventory_item
        assert item.available_quantity == 10  # Same as total quantity

    async def test_available_quantity_with_reservations(
        self, inventory_service, sample_inventory_item
    ):
        """Test available quantity with reservations"""
        item_id = sample_inventory_item.id

        # Reserve 4 units
        await inventory_service.reserve_inventory_stock(item_id, 4)

        # Get fresh item
        item = await inventory_service.inventory_repo.get_by_id(item_id)
        assert item.available_quantity == 6  # 10 - 4

    async def test_available_quantity_full_reservation(
        self, inventory_service, sample_inventory_item
    ):
        """Test available quantity when all stock is reserved"""
        item_id = sample_inventory_item.id

        # Reserve all stock
        await inventory_service.reserve_inventory_stock(item_id, 10)

        # Get fresh item
        item = await inventory_service.inventory_repo.get_by_id(item_id)
        assert item.available_quantity == 0

"""
Comprehensive test suite for AutoListingService
Tests automated listing rules, conditions, and execution
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from domains.pricing.services.auto_listing_service import AutoListingService, ListingRule
from shared.database.models import Brand, InventoryItem, Product

# ===== FIXTURES =====


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    return AsyncMock()


@pytest.fixture
def auto_listing_service(mock_db_session):
    """AutoListingService instance with mocked dependencies"""
    return AutoListingService(mock_db_session)


@pytest.fixture
def sample_product():
    """Sample product for testing"""
    product = MagicMock(spec=Product)
    product.id = uuid.uuid4()
    product.sku = "NIKE-AIR-MAX-90"
    product.product_name = "Nike Air Max 90"
    product.brand = "Nike"
    product.category = "Sneakers"
    product.size = "10"
    product.colorway = "White/Black"
    return product


@pytest.fixture
def sample_inventory_item(sample_product):
    """Sample inventory item for testing"""
    item = MagicMock(spec=InventoryItem)
    item.id = uuid.uuid4()
    item.product_id = sample_product.id
    item.product = sample_product
    item.status = "in_stock"
    item.condition = "new"
    item.purchase_price = Decimal("150.00")
    item.purchase_date = datetime.now(timezone.utc) - timedelta(days=5)
    item.created_at = datetime.now(timezone.utc) - timedelta(days=5)
    item.location = "Warehouse A"
    item.platform_id = None
    item.listed_price = None
    return item


@pytest.fixture
def sample_listing_rule():
    """Sample listing rule for testing"""
    return ListingRule(
        name="Test Rule",
        conditions={
            "min_profit_margin_percent": 20.0,
            "status": ["in_stock"],
            "brand_names": ["Nike", "Adidas"],
        },
        actions={
            "list_on_platform": "stockx",
            "pricing_strategy": "market_based",
            "markup_percent": 25.0,
        },
        priority=10,
        active=True,
    )


# ===== LISTING RULE TESTS =====


def test_listing_rule_initialization(sample_listing_rule):
    """Test ListingRule initialization"""
    assert sample_listing_rule.name == "Test Rule"
    assert sample_listing_rule.conditions["min_profit_margin_percent"] == 20.0
    assert sample_listing_rule.actions["list_on_platform"] == "stockx"
    assert sample_listing_rule.priority == 10
    assert sample_listing_rule.active is True
    assert sample_listing_rule.id is not None
    assert sample_listing_rule.created_at is not None


def test_auto_listing_service_initialization(auto_listing_service):
    """Test AutoListingService initializes with default rules"""
    assert auto_listing_service.db_session is not None
    assert auto_listing_service._listing_rules is not None
    # Should have default rules loaded
    assert len(auto_listing_service._listing_rules) > 0


def test_load_default_rules(auto_listing_service):
    """Test default rules are loaded correctly"""
    rules = auto_listing_service._listing_rules
    # Should have at least 3 default rules
    assert len(rules) >= 3
    # Check rule names exist
    rule_names = [rule.name for rule in rules]
    assert "High Profit Margin Auto-List" in rule_names
    assert "Quick Turnover Items" in rule_names
    assert "Premium Items Strategy" in rule_names


# ===== RULE MANAGEMENT TESTS =====


@pytest.mark.asyncio
async def test_add_custom_rule_success(auto_listing_service, sample_listing_rule):
    """Test adding a valid custom rule"""
    initial_count = len(auto_listing_service._listing_rules)

    result = await auto_listing_service.add_custom_rule(sample_listing_rule)

    assert result is True
    assert len(auto_listing_service._listing_rules) == initial_count + 1
    # Verify rule was added
    added_rule = auto_listing_service.get_rule_by_name("Test Rule")
    assert added_rule is not None
    assert added_rule.name == "Test Rule"


@pytest.mark.asyncio
async def test_add_custom_rule_invalid(auto_listing_service):
    """Test adding an invalid rule fails"""
    invalid_rule = ListingRule(
        name="Invalid Rule",
        conditions={},  # No conditions
        actions={},  # No actions
        priority=10,
    )

    result = await auto_listing_service.add_custom_rule(invalid_rule)

    assert result is False


def test_validate_rule_valid(auto_listing_service, sample_listing_rule):
    """Test rule validation with valid rule"""
    result = auto_listing_service._validate_rule(sample_listing_rule)
    assert result is True


def test_validate_rule_missing_conditions(auto_listing_service):
    """Test rule validation fails with missing conditions"""
    invalid_rule = ListingRule(
        name="Invalid",
        conditions={},  # Empty
        actions={"list_on_platform": "stockx"},
        priority=10,
    )
    result = auto_listing_service._validate_rule(invalid_rule)
    assert result is False


def test_validate_rule_missing_actions(auto_listing_service):
    """Test rule validation fails with missing actions"""
    invalid_rule = ListingRule(
        name="Invalid",
        conditions={"min_profit_margin_percent": 20.0},
        actions={},  # Empty
        priority=10,
    )
    result = auto_listing_service._validate_rule(invalid_rule)
    assert result is False


def test_get_rule_by_name_found(auto_listing_service):
    """Test getting rule by name when it exists"""
    rule = auto_listing_service.get_rule_by_name("High Profit Margin Auto-List")
    assert rule is not None
    assert rule.name == "High Profit Margin Auto-List"


def test_get_rule_by_name_not_found(auto_listing_service):
    """Test getting rule by name when it doesn't exist"""
    rule = auto_listing_service.get_rule_by_name("Non-Existent Rule")
    assert rule is None


@pytest.mark.asyncio
async def test_toggle_rule_success(auto_listing_service):
    """Test toggling a rule on/off"""
    rule_name = "High Profit Margin Auto-List"

    # Toggle off
    result = await auto_listing_service.toggle_rule(rule_name, False)
    assert result is True
    rule = auto_listing_service.get_rule_by_name(rule_name)
    assert rule.active is False

    # Toggle on
    result = await auto_listing_service.toggle_rule(rule_name, True)
    assert result is True
    rule = auto_listing_service.get_rule_by_name(rule_name)
    assert rule.active is True


@pytest.mark.asyncio
async def test_toggle_rule_not_found(auto_listing_service):
    """Test toggling a non-existent rule"""
    result = await auto_listing_service.toggle_rule("Non-Existent", True)
    assert result is False


# ===== PRICE CALCULATION TESTS (Simplified) =====


@pytest.mark.asyncio
async def test_calculate_listing_price_cost_plus(
    auto_listing_service, sample_inventory_item
):
    """Test calculating listing price with cost_plus strategy"""
    price = await auto_listing_service._calculate_listing_price(
        sample_inventory_item, "cost_plus", Decimal("30.0")
    )

    # Should use purchase price with markup: 150 * 1.30 = 195.00
    assert price == Decimal("195.00")


# ===== AUTOMATION STATUS TESTS =====


@pytest.mark.asyncio
async def test_get_automation_status(auto_listing_service):
    """Test getting automation status"""
    status = await auto_listing_service.get_automation_status()

    assert "total_rules" in status
    assert "active_rules" in status
    assert status["total_rules"] >= 3  # Default rules


# ===== UNIT TESTS FOR HELPER METHODS =====


def test_listing_rule_has_required_attributes():
    """Test that ListingRule has all required attributes"""
    rule = ListingRule(
        name="Test",
        conditions={"status": ["in_stock"]},
        actions={"list_on_platform": "stockx"},
    )
    assert hasattr(rule, "id")
    assert hasattr(rule, "name")
    assert hasattr(rule, "conditions")
    assert hasattr(rule, "actions")
    assert hasattr(rule, "priority")
    assert hasattr(rule, "active")
    assert hasattr(rule, "created_at")


def test_listing_rule_priority_default():
    """Test ListingRule default priority"""
    rule = ListingRule(
        name="Test",
        conditions={"status": ["in_stock"]},
        actions={"list_on_platform": "stockx"},
    )
    assert rule.priority == 100


def test_listing_rule_active_default():
    """Test ListingRule default active status"""
    rule = ListingRule(
        name="Test",
        conditions={"status": ["in_stock"]},
        actions={"list_on_platform": "stockx"},
    )
    assert rule.active is True


def test_auto_listing_service_has_logger(auto_listing_service):
    """Test that AutoListingService has logger"""
    assert auto_listing_service.logger is not None


def test_auto_listing_service_has_rules_list(auto_listing_service):
    """Test that AutoListingService has _listing_rules list"""
    assert isinstance(auto_listing_service._listing_rules, list)

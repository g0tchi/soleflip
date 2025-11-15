"""
Comprehensive test suite for DeadStockService
Tests dead stock identification, risk analysis, and automated clearance
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from domains.inventory.services.dead_stock_service import (
    DeadStockService,
    StockRiskLevel,
    DeadStockItem,
    DeadStockAnalysis,
)
from shared.database.models import InventoryItem, Product, Brand, Category, Size


# ===== FIXTURES =====


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = AsyncMock()
    return session


@pytest.fixture
def dead_stock_service(mock_db_session):
    """DeadStockService instance with mocked dependencies"""
    return DeadStockService(mock_db_session)


@pytest.fixture
def sample_inventory_items():
    """Sample inventory items with various ages and scenarios"""

    def create_item(
        days_old: int, purchase_price: Decimal, brand_name: str = "Nike", status: str = "in_stock"
    ):
        """Helper to create mock inventory item"""
        item = MagicMock(spec=InventoryItem)
        item.id = uuid4()
        item.purchase_price = purchase_price
        item.quantity = 1
        item.status = status
        item.created_at = datetime.now(timezone.utc) - timedelta(days=days_old)
        item.purchase_date = datetime.now(timezone.utc) - timedelta(days=days_old)

        # Mock product
        product = MagicMock(spec=Product)
        product.id = uuid4()
        product.name = f"{brand_name} Test Sneaker"

        # Mock brand
        brand = MagicMock(spec=Brand)
        brand.id = uuid4()
        brand.name = brand_name
        product.brand = brand

        # Mock category
        category = MagicMock(spec=Category)
        category.id = uuid4()
        category.name = "Sneakers"
        product.category = category

        item.product = product

        # Mock size
        size = MagicMock(spec=Size)
        size.value = "US 10"
        item.size = size

        return item

    return [
        create_item(15, Decimal("100.00"), "Nike"),  # HOT
        create_item(45, Decimal("150.00"), "Adidas"),  # WARM
        create_item(90, Decimal("200.00"), "Jordan"),  # COLD
        create_item(150, Decimal("250.00"), "Puma"),  # DEAD
        create_item(200, Decimal("300.00"), "Reebok"),  # CRITICAL
    ]


# ===== MAIN ANALYSIS FLOW TESTS =====


@pytest.mark.asyncio
async def test_analyze_dead_stock_success(dead_stock_service, sample_inventory_items):
    """Test successful dead stock analysis"""
    # Mock inventory retrieval
    dead_stock_service._get_inventory_for_analysis = AsyncMock(
        return_value=sample_inventory_items
    )

    # Mock _analyze_item_risk to return realistic DeadStockItem objects
    async def mock_analyze_risk(item):
        days = (datetime.now(timezone.utc) - item.purchase_date.replace(tzinfo=timezone.utc)).days
        risk_score = min(days / 200, 1.0)  # Simple risk score based on age

        return DeadStockItem(
            item_id=item.id,
            product_name=item.product.name,
            brand_name=item.product.brand.name,
            size_value=item.size.value,
            purchase_price=item.purchase_price,
            current_market_price=item.purchase_price * Decimal("0.9"),
            days_in_inventory=days,
            risk_score=risk_score,
            risk_level=StockRiskLevel.COLD,
            locked_capital=item.purchase_price,
            potential_loss=Decimal("20.00"),
            last_price_check=datetime.now(timezone.utc),
            recommended_actions=["Test action"],
            market_trend="stable",
            velocity_score=0.5,
        )

    dead_stock_service._analyze_item_risk = mock_analyze_risk

    # Execute
    result = await dead_stock_service.analyze_dead_stock(min_risk_score=0.0)

    # Assert
    assert isinstance(result, DeadStockAnalysis)
    assert result.total_items_analyzed == 5
    assert len(result.dead_stock_items) == 5
    assert isinstance(result.risk_summary, dict)
    assert isinstance(result.financial_impact, dict)
    assert isinstance(result.recommendations, list)


@pytest.mark.asyncio
async def test_analyze_dead_stock_with_brand_filter(dead_stock_service, sample_inventory_items):
    """Test dead stock analysis with brand filter"""
    # Filter only Nike items
    nike_items = [item for item in sample_inventory_items if item.product.brand.name == "Nike"]

    dead_stock_service._get_inventory_for_analysis = AsyncMock(return_value=nike_items)
    dead_stock_service._analyze_item_risk = AsyncMock(
        return_value=MagicMock(risk_score=0.6, risk_level=StockRiskLevel.COLD)
    )

    result = await dead_stock_service.analyze_dead_stock(brand_filter="Nike", min_risk_score=0.5)

    # Verify brand filter was passed
    dead_stock_service._get_inventory_for_analysis.assert_called_once_with("Nike", None)
    assert result.total_items_analyzed == len(nike_items)


@pytest.mark.asyncio
async def test_analyze_dead_stock_with_min_risk_score_filter(
    dead_stock_service, sample_inventory_items
):
    """Test dead stock analysis filters by minimum risk score"""
    dead_stock_service._get_inventory_for_analysis = AsyncMock(
        return_value=sample_inventory_items
    )

    # Mock items with varying risk scores
    risk_scores = [0.2, 0.4, 0.6, 0.8, 1.0]
    call_count = 0

    async def mock_analyze_with_scores(item):
        nonlocal call_count
        score = risk_scores[call_count]
        call_count += 1

        return DeadStockItem(
            item_id=item.id,
            product_name=item.product.name,
            brand_name=item.product.brand.name,
            size_value=item.size.value,
            purchase_price=item.purchase_price,
            current_market_price=item.purchase_price,
            days_in_inventory=30,
            risk_score=score,
            risk_level=StockRiskLevel.WARM,
            locked_capital=item.purchase_price,
            potential_loss=Decimal("10.00"),
            last_price_check=datetime.now(timezone.utc),
            recommended_actions=[],
            market_trend="stable",
            velocity_score=0.5,
        )

    dead_stock_service._analyze_item_risk = mock_analyze_with_scores

    result = await dead_stock_service.analyze_dead_stock(min_risk_score=0.5)

    # Should only include items with risk_score >= 0.5
    assert len(result.dead_stock_items) == 3  # 0.6, 0.8, 1.0


@pytest.mark.asyncio
async def test_analyze_dead_stock_error_handling(dead_stock_service):
    """Test error handling in dead stock analysis"""
    dead_stock_service._get_inventory_for_analysis = AsyncMock(
        side_effect=Exception("Database error")
    )

    with pytest.raises(Exception, match="Database error"):
        await dead_stock_service.analyze_dead_stock()


# ===== INVENTORY RETRIEVAL TESTS =====


@pytest.mark.asyncio
async def test_get_inventory_for_analysis_basic(dead_stock_service, mock_db_session):
    """Test basic inventory retrieval"""
    # Mock database query result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [MagicMock(), MagicMock()]

    mock_db_session.execute = AsyncMock(return_value=mock_result)
    mock_db_session.refresh = AsyncMock()

    result = await dead_stock_service._get_inventory_for_analysis()

    assert len(result) == 2
    mock_db_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_inventory_for_analysis_with_filters(dead_stock_service, mock_db_session):
    """Test inventory retrieval with brand and category filters"""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []

    mock_db_session.execute = AsyncMock(return_value=mock_result)

    result = await dead_stock_service._get_inventory_for_analysis("Nike", "Sneakers")

    assert isinstance(result, list)
    mock_db_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_inventory_for_analysis_error_handling(dead_stock_service, mock_db_session):
    """Test error handling returns empty list"""
    mock_db_session.execute = AsyncMock(side_effect=Exception("DB error"))

    result = await dead_stock_service._get_inventory_for_analysis()

    assert result == []


# ===== ITEM RISK ANALYSIS TESTS =====


@pytest.mark.asyncio
async def test_analyze_item_risk_complete(dead_stock_service, sample_inventory_items):
    """Test complete item risk analysis"""
    item = sample_inventory_items[2]  # 90-day old item

    # Mock market price
    dead_stock_service._get_current_market_price = AsyncMock(return_value=Decimal("180.00"))

    result = await dead_stock_service._analyze_item_risk(item)

    assert isinstance(result, DeadStockItem)
    assert result.item_id == item.id
    assert result.product_name == item.product.name
    assert result.brand_name == item.product.brand.name
    assert result.size_value == item.size.value
    assert result.purchase_price == item.purchase_price
    assert result.days_in_inventory >= 0
    assert 0.0 <= result.risk_score <= 1.0
    assert isinstance(result.risk_level, StockRiskLevel)
    assert result.locked_capital == item.purchase_price * item.quantity
    assert isinstance(result.potential_loss, Decimal)
    assert isinstance(result.recommended_actions, list)


@pytest.mark.asyncio
async def test_analyze_item_risk_without_product(dead_stock_service):
    """Test item risk analysis when product data is missing"""
    item = MagicMock(spec=InventoryItem)
    item.id = uuid4()
    item.purchase_price = Decimal("100.00")
    item.quantity = 1
    item.purchase_date = datetime.now(timezone.utc) - timedelta(days=50)
    item.created_at = datetime.now(timezone.utc) - timedelta(days=50)
    item.product = None
    item.size = None

    dead_stock_service._get_current_market_price = AsyncMock(return_value=Decimal("90.00"))

    result = await dead_stock_service._analyze_item_risk(item)

    assert result.product_name == "Unknown"
    assert result.brand_name == "Unknown"
    assert result.size_value == "N/A"


# ===== MARKET PRICE CALCULATION TESTS =====


@pytest.mark.asyncio
async def test_get_current_market_price_new_item(dead_stock_service, sample_inventory_items):
    """Test market price for new items (< 30 days)"""
    item = sample_inventory_items[0]  # 15 days old

    result = await dead_stock_service._get_current_market_price(item)

    assert result is not None
    # New items should have higher market price
    assert result >= item.purchase_price


@pytest.mark.asyncio
async def test_get_current_market_price_old_item(dead_stock_service, sample_inventory_items):
    """Test market price for old items (> 90 days)"""
    item = sample_inventory_items[4]  # 200 days old

    result = await dead_stock_service._get_current_market_price(item)

    assert result is not None
    # Old items should have lower market price
    assert result < item.purchase_price


@pytest.mark.asyncio
async def test_get_current_market_price_premium_brand(dead_stock_service, sample_inventory_items):
    """Test premium brands hold value better"""
    nike_item = sample_inventory_items[0]  # Nike brand
    nike_price = await dead_stock_service._get_current_market_price(nike_item)

    # Create non-premium brand item
    generic_item = MagicMock(spec=InventoryItem)
    generic_item.purchase_price = Decimal("100.00")
    generic_item.purchase_date = datetime.now(timezone.utc) - timedelta(days=15)
    generic_item.created_at = datetime.now(timezone.utc) - timedelta(days=15)

    generic_product = MagicMock(spec=Product)
    generic_brand = MagicMock(spec=Brand)
    generic_brand.name = "Generic"
    generic_product.brand = generic_brand
    generic_item.product = generic_product

    generic_price = await dead_stock_service._get_current_market_price(generic_item)

    # Nike should have better price retention
    assert nike_price >= generic_price


@pytest.mark.asyncio
async def test_get_current_market_price_no_purchase_price(dead_stock_service):
    """Test market price returns None if no purchase price"""
    item = MagicMock(spec=InventoryItem)
    item.purchase_price = None

    result = await dead_stock_service._get_current_market_price(item)

    assert result is None


# ===== RISK COMPONENTS TESTS =====


@pytest.mark.asyncio
async def test_calculate_risk_components_hot_item(dead_stock_service, sample_inventory_items):
    """Test risk components for HOT item (< 30 days)"""
    item = sample_inventory_items[0]
    market_price = Decimal("115.00")  # > 1.1 ratio for rising trend

    result = await dead_stock_service._calculate_risk_components(item, 15, market_price)

    assert result["age_risk"] == 0.1  # HOT age risk
    assert result["market_risk"] == 0.3  # Rising price (ratio > 1.1)
    assert result["trend_direction"] == "rising"
    assert result["days_in_inventory"] == 15


@pytest.mark.asyncio
async def test_calculate_risk_components_dead_item(dead_stock_service, sample_inventory_items):
    """Test risk components for DEAD item (> 120 days)"""
    item = sample_inventory_items[3]
    market_price = Decimal("200.00")  # Price declined

    result = await dead_stock_service._calculate_risk_components(item, 150, market_price)

    assert result["age_risk"] == 0.8  # DEAD age risk
    assert result["market_risk"] == 0.7  # Declining price
    assert result["trend_direction"] == "declining"


@pytest.mark.asyncio
async def test_calculate_risk_components_critical_item(dead_stock_service, sample_inventory_items):
    """Test risk components for CRITICAL item (> 180 days)"""
    item = sample_inventory_items[4]
    market_price = Decimal("200.00")  # Severe decline

    result = await dead_stock_service._calculate_risk_components(item, 200, market_price)

    assert result["age_risk"] == 1.0  # CRITICAL age risk
    assert result["market_risk"] == 0.9  # Severe price decline


@pytest.mark.asyncio
async def test_calculate_risk_components_no_market_price(
    dead_stock_service, sample_inventory_items
):
    """Test risk components when market price is unavailable"""
    item = sample_inventory_items[0]

    result = await dead_stock_service._calculate_risk_components(item, 30, None)

    assert result["market_risk"] == 0.5  # Default
    assert result["trend_direction"] == "stable"


@pytest.mark.asyncio
async def test_calculate_risk_components_velocity_by_brand(dead_stock_service):
    """Test velocity risk varies by brand"""
    # Create Nike item (fast-moving)
    nike_item = MagicMock(spec=InventoryItem)
    nike_product = MagicMock(spec=Product)
    nike_brand = MagicMock(spec=Brand)
    nike_brand.name = "Nike"
    nike_product.brand = nike_brand
    nike_product.category = MagicMock(spec=Category)
    nike_product.category.name = "Sneakers"
    nike_item.product = nike_product
    nike_item.purchase_price = Decimal("100.00")

    nike_result = await dead_stock_service._calculate_risk_components(
        nike_item, 30, Decimal("100.00")
    )

    # Create generic item (slower-moving)
    generic_item = MagicMock(spec=InventoryItem)
    generic_product = MagicMock(spec=Product)
    generic_brand = MagicMock(spec=Brand)
    generic_brand.name = "Generic"
    generic_product.brand = generic_brand
    generic_product.category = MagicMock(spec=Category)
    generic_product.category.name = "Sneakers"
    generic_item.product = generic_product
    generic_item.purchase_price = Decimal("100.00")

    generic_result = await dead_stock_service._calculate_risk_components(
        generic_item, 30, Decimal("100.00")
    )

    # Nike should have lower velocity risk
    assert nike_result["velocity_risk"] < generic_result["velocity_risk"]


# ===== RISK LEVEL DETERMINATION TESTS =====


def test_determine_risk_level_hot(dead_stock_service):
    """Test HOT risk level determination"""
    result = dead_stock_service._determine_risk_level(days_in_inventory=20, risk_score=0.15)
    assert result == StockRiskLevel.HOT


def test_determine_risk_level_warm(dead_stock_service):
    """Test WARM risk level determination"""
    result = dead_stock_service._determine_risk_level(days_in_inventory=45, risk_score=0.35)
    assert result == StockRiskLevel.WARM


def test_determine_risk_level_cold(dead_stock_service):
    """Test COLD risk level determination"""
    result = dead_stock_service._determine_risk_level(days_in_inventory=90, risk_score=0.6)
    assert result == StockRiskLevel.COLD


def test_determine_risk_level_dead(dead_stock_service):
    """Test DEAD risk level determination"""
    result = dead_stock_service._determine_risk_level(days_in_inventory=150, risk_score=0.8)
    assert result == StockRiskLevel.DEAD


def test_determine_risk_level_critical_by_days(dead_stock_service):
    """Test CRITICAL risk level by days threshold"""
    result = dead_stock_service._determine_risk_level(days_in_inventory=200, risk_score=0.5)
    assert result == StockRiskLevel.CRITICAL


def test_determine_risk_level_critical_by_score(dead_stock_service):
    """Test CRITICAL risk level by risk score"""
    result = dead_stock_service._determine_risk_level(days_in_inventory=100, risk_score=0.95)
    assert result == StockRiskLevel.CRITICAL


# ===== FINANCIAL CALCULATIONS TESTS =====


def test_calculate_potential_loss_with_market_price(dead_stock_service):
    """Test potential loss calculation with market price"""
    result = dead_stock_service._calculate_potential_loss(
        purchase_price=Decimal("100.00"), market_price=Decimal("80.00"), risk_score=0.5
    )

    # Loss = (100 - 80) * (1 + 0.5) = 30
    assert result == Decimal("30.00")


def test_calculate_potential_loss_without_market_price(dead_stock_service):
    """Test potential loss estimation without market price"""
    result = dead_stock_service._calculate_potential_loss(
        purchase_price=Decimal("100.00"), market_price=None, risk_score=0.6
    )

    # Estimated loss = 100 * 0.6 * 0.3 = 18
    assert result == Decimal("18.00")


def test_calculate_potential_loss_market_price_higher(dead_stock_service):
    """Test potential loss when market price is higher than purchase price"""
    result = dead_stock_service._calculate_potential_loss(
        purchase_price=Decimal("100.00"), market_price=Decimal("120.00"), risk_score=0.3
    )

    assert result == Decimal("0.00")


def test_calculate_risk_summary(dead_stock_service):
    """Test risk summary calculation"""
    items = [
        MagicMock(risk_level=StockRiskLevel.HOT),
        MagicMock(risk_level=StockRiskLevel.HOT),
        MagicMock(risk_level=StockRiskLevel.WARM),
        MagicMock(risk_level=StockRiskLevel.COLD),
        MagicMock(risk_level=StockRiskLevel.DEAD),
        MagicMock(risk_level=StockRiskLevel.CRITICAL),
    ]

    result = dead_stock_service._calculate_risk_summary(items)

    assert result["hot"] == 2
    assert result["warm"] == 1
    assert result["cold"] == 1
    assert result["dead"] == 1
    assert result["critical"] == 1


def test_calculate_financial_impact(dead_stock_service):
    """Test financial impact calculation"""
    items = [
        MagicMock(
            risk_level=StockRiskLevel.DEAD,
            locked_capital=Decimal("100.00"),
            potential_loss=Decimal("20.00"),
        ),
        MagicMock(
            risk_level=StockRiskLevel.CRITICAL,
            locked_capital=Decimal("200.00"),
            potential_loss=Decimal("50.00"),
        ),
    ]

    result = dead_stock_service._calculate_financial_impact(items)

    assert result["total_locked_capital"] == 300.0
    assert result["total_potential_loss"] == 70.0
    assert "locked_capital_by_risk" in result
    assert "potential_loss_by_risk" in result
    assert result["loss_percentage"] == pytest.approx(23.33, rel=0.1)


def test_calculate_financial_impact_zero_capital(dead_stock_service):
    """Test financial impact with zero locked capital"""
    items = []

    result = dead_stock_service._calculate_financial_impact(items)

    assert result["total_locked_capital"] == 0
    assert result["total_potential_loss"] == 0
    assert result["loss_percentage"] == 0


# ===== RECOMMENDATIONS TESTS =====


def test_generate_item_recommendations_critical(dead_stock_service):
    """Test recommendations for CRITICAL risk level"""
    result = dead_stock_service._generate_item_recommendations(
        risk_level=StockRiskLevel.CRITICAL,
        days_in_inventory=200,
        risk_components={"trend_direction": "declining"},
    )

    assert len(result) > 0
    assert any("SOFORT-AKTION" in r for r in result)
    assert any("Liquidation" in r for r in result)
    assert any("Markttrend beachten" in r for r in result)


def test_generate_item_recommendations_dead(dead_stock_service):
    """Test recommendations for DEAD risk level"""
    result = dead_stock_service._generate_item_recommendations(
        risk_level=StockRiskLevel.DEAD,
        days_in_inventory=150,
        risk_components={"trend_direction": "stable"},
    )

    assert len(result) > 0
    assert any("Aggressive Preissenkung" in r for r in result)
    assert any("Clearance Sale" in r for r in result)


def test_generate_item_recommendations_cold(dead_stock_service):
    """Test recommendations for COLD risk level"""
    result = dead_stock_service._generate_item_recommendations(
        risk_level=StockRiskLevel.COLD,
        days_in_inventory=90,
        risk_components={"trend_direction": "stable"},
    )

    assert len(result) > 0
    assert any("Preisanpassung" in r for r in result)


def test_generate_item_recommendations_warm(dead_stock_service):
    """Test recommendations for WARM risk level"""
    result = dead_stock_service._generate_item_recommendations(
        risk_level=StockRiskLevel.WARM,
        days_in_inventory=45,
        risk_components={"trend_direction": "stable"},
    )

    assert len(result) > 0
    assert any("Monitoring" in r for r in result)


def test_generate_item_recommendations_hot(dead_stock_service):
    """Test recommendations for HOT risk level"""
    result = dead_stock_service._generate_item_recommendations(
        risk_level=StockRiskLevel.HOT,
        days_in_inventory=15,
        risk_components={"trend_direction": "rising"},
    )

    assert len(result) > 0
    assert any("Status Quo" in r or "Preis-Optimierung" in r for r in result)
    assert any("Markttrend nutzen" in r for r in result)


def test_generate_recommendations_with_critical_items(dead_stock_service):
    """Test global recommendations with critical items"""
    items = [
        MagicMock(risk_level=StockRiskLevel.CRITICAL, locked_capital=Decimal("500.00")),
        MagicMock(risk_level=StockRiskLevel.DEAD, locked_capital=Decimal("300.00")),
    ]

    financial_impact = {
        "total_locked_capital": 800.0,
        "total_potential_loss": 200.0,
        "locked_capital_by_risk": {"critical": 500.0, "dead": 300.0},
        "loss_percentage": 25.0,
    }

    result = dead_stock_service._generate_recommendations(items, financial_impact)

    assert len(result) > 0
    assert any("PRIORITÄT 1" in r for r in result)
    assert any("kritische Items" in r for r in result)


def test_generate_recommendations_high_potential_loss(dead_stock_service):
    """Test recommendations with high potential loss"""
    items = [MagicMock(risk_level=StockRiskLevel.DEAD)]

    financial_impact = {
        "total_locked_capital": 1000.0,
        "total_potential_loss": 300.0,  # 30% loss
        "locked_capital_by_risk": {"dead": 1000.0},
        "loss_percentage": 30.0,
    }

    result = dead_stock_service._generate_recommendations(items, financial_impact)

    assert any("FINANZ-WARNUNG" in r for r in result)


def test_generate_recommendations_high_locked_capital(dead_stock_service):
    """Test recommendations with high locked capital"""
    items = [MagicMock(risk_level=StockRiskLevel.COLD)]

    financial_impact = {
        "total_locked_capital": 15000.0,
        "total_potential_loss": 1000.0,
        "locked_capital_by_risk": {"cold": 15000.0},
        "loss_percentage": 6.67,
    }

    result = dead_stock_service._generate_recommendations(items, financial_impact)

    assert any("KAPITAL-OPTIMIERUNG" in r for r in result)


# ===== DEAD STOCK SUMMARY TESTS =====


@pytest.mark.asyncio
async def test_get_dead_stock_summary_success(dead_stock_service):
    """Test successful dead stock summary"""
    mock_analysis = DeadStockAnalysis(
        total_items_analyzed=100,
        dead_stock_items=[
            MagicMock(risk_level=StockRiskLevel.CRITICAL),
            MagicMock(risk_level=StockRiskLevel.DEAD),
            MagicMock(risk_level=StockRiskLevel.COLD),
        ],
        risk_summary={"critical": 1, "dead": 1, "cold": 1},
        financial_impact={
            "total_locked_capital": 1000.0,
            "total_potential_loss": 200.0,
            "loss_percentage": 20.0,
        },
        recommendations=["Test recommendation"],
        analysis_timestamp=datetime.now(timezone.utc),
    )

    dead_stock_service.analyze_dead_stock = AsyncMock(return_value=mock_analysis)

    result = await dead_stock_service.get_dead_stock_summary()

    assert result["total_items_at_risk"] == 3
    assert "risk_breakdown" in result
    assert "financial_impact" in result
    assert len(result["top_priorities"]) <= 5


@pytest.mark.asyncio
async def test_get_dead_stock_summary_error_handling(dead_stock_service):
    """Test error handling in dead stock summary"""
    dead_stock_service.analyze_dead_stock = AsyncMock(side_effect=Exception("Analysis failed"))

    result = await dead_stock_service.get_dead_stock_summary()

    assert "error" in result
    assert result["total_items_at_risk"] == 0


# ===== AUTOMATED CLEARANCE TESTS =====


@pytest.mark.asyncio
async def test_execute_automated_clearance_dry_run(dead_stock_service):
    """Test automated clearance in dry run mode"""
    mock_items = [
        DeadStockItem(
            item_id=uuid4(),
            product_name="Test Product 1",
            brand_name="Nike",
            size_value="US 10",
            purchase_price=Decimal("100.00"),
            current_market_price=Decimal("80.00"),
            days_in_inventory=150,
            risk_score=0.8,
            risk_level=StockRiskLevel.DEAD,
            locked_capital=Decimal("100.00"),
            potential_loss=Decimal("20.00"),
            last_price_check=datetime.now(timezone.utc),
            recommended_actions=[],
            market_trend="declining",
            velocity_score=0.6,
        ),
        DeadStockItem(
            item_id=uuid4(),
            product_name="Test Product 2",
            brand_name="Adidas",
            size_value="US 11",
            purchase_price=Decimal("150.00"),
            current_market_price=Decimal("100.00"),
            days_in_inventory=200,
            risk_score=0.95,
            risk_level=StockRiskLevel.CRITICAL,
            locked_capital=Decimal("150.00"),
            potential_loss=Decimal("50.00"),
            last_price_check=datetime.now(timezone.utc),
            recommended_actions=[],
            market_trend="declining",
            velocity_score=0.8,
        ),
    ]

    mock_analysis = MagicMock()
    mock_analysis.dead_stock_items = mock_items

    dead_stock_service.analyze_dead_stock = AsyncMock(return_value=mock_analysis)

    result = await dead_stock_service.execute_automated_clearance(dry_run=True)

    assert result["success"] is True
    assert result["dry_run"] is True
    assert result["items_processed"] == 2
    assert len(result["actions_taken"]) == 2
    assert result["total_price_reductions"] > 0


@pytest.mark.asyncio
async def test_execute_automated_clearance_with_risk_level_filter(dead_stock_service):
    """Test automated clearance with specific risk levels"""
    mock_items = [
        MagicMock(
            item_id=uuid4(),
            product_name="Critical Item",
            purchase_price=Decimal("100.00"),
            risk_level=StockRiskLevel.CRITICAL,
            locked_capital=Decimal("100.00"),
        ),
        MagicMock(
            item_id=uuid4(),
            product_name="Dead Item",
            purchase_price=Decimal("150.00"),
            risk_level=StockRiskLevel.DEAD,
            locked_capital=Decimal("150.00"),
        ),
        MagicMock(
            item_id=uuid4(),
            product_name="Cold Item",
            purchase_price=Decimal("200.00"),
            risk_level=StockRiskLevel.COLD,
            locked_capital=Decimal("200.00"),
        ),
    ]

    mock_analysis = MagicMock()
    mock_analysis.dead_stock_items = mock_items

    dead_stock_service.analyze_dead_stock = AsyncMock(return_value=mock_analysis)

    # Only process CRITICAL items
    result = await dead_stock_service.execute_automated_clearance(
        risk_levels=[StockRiskLevel.CRITICAL], dry_run=True
    )

    assert result["items_processed"] == 1
    assert result["actions_taken"][0]["product_name"] == "Critical Item"


@pytest.mark.asyncio
async def test_execute_automated_clearance_max_items_limit(dead_stock_service):
    """Test automated clearance respects max_items limit"""
    # Create 100 mock items
    mock_items = [
        MagicMock(
            item_id=uuid4(),
            product_name=f"Item {i}",
            purchase_price=Decimal("100.00"),
            risk_level=StockRiskLevel.DEAD,
            locked_capital=Decimal("100.00"),
        )
        for i in range(100)
    ]

    mock_analysis = MagicMock()
    mock_analysis.dead_stock_items = mock_items

    dead_stock_service.analyze_dead_stock = AsyncMock(return_value=mock_analysis)

    result = await dead_stock_service.execute_automated_clearance(max_items=10, dry_run=True)

    assert result["items_processed"] == 10


@pytest.mark.asyncio
async def test_execute_automated_clearance_pricing_calculation(dead_stock_service):
    """Test clearance pricing calculations"""
    critical_item = MagicMock(
        item_id=uuid4(),
        product_name="Critical Item",
        purchase_price=Decimal("100.00"),
        risk_level=StockRiskLevel.CRITICAL,
        locked_capital=Decimal("100.00"),
    )

    dead_item = MagicMock(
        item_id=uuid4(),
        product_name="Dead Item",
        purchase_price=Decimal("100.00"),
        risk_level=StockRiskLevel.DEAD,
        locked_capital=Decimal("100.00"),
    )

    mock_analysis = MagicMock()
    mock_analysis.dead_stock_items = [critical_item, dead_item]

    dead_stock_service.analyze_dead_stock = AsyncMock(return_value=mock_analysis)

    result = await dead_stock_service.execute_automated_clearance(dry_run=True)

    actions = result["actions_taken"]

    # CRITICAL should get 30% discount
    critical_action = next(a for a in actions if a["product_name"] == "Critical Item")
    assert critical_action["discount_percent"] == 30.0
    assert critical_action["new_price"] == 70.0

    # DEAD should get 20% discount
    dead_action = next(a for a in actions if a["product_name"] == "Dead Item")
    assert dead_action["discount_percent"] == 20.0
    assert dead_action["new_price"] == 80.0


@pytest.mark.asyncio
async def test_execute_automated_clearance_error_handling(dead_stock_service):
    """Test error handling in automated clearance"""
    dead_stock_service.analyze_dead_stock = AsyncMock(side_effect=Exception("Analysis failed"))

    result = await dead_stock_service.execute_automated_clearance()

    assert result["success"] is False
    assert "error" in result

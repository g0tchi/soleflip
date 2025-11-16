"""
Comprehensive test suite for PricingEngine
Tests all pricing strategies and calculation methods
"""

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from domains.pricing.models import PriceRule
from domains.pricing.services.pricing_engine import (
    PricingContext,
    PricingEngine,
    PricingResult,
    PricingStrategy,
)
from shared.database.models import Brand, InventoryItem, Product

# ===== FIXTURES =====


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    return AsyncMock()


@pytest.fixture
def mock_repository():
    """Mock PricingRepository"""
    repo = AsyncMock()
    repo.get_active_price_rules = AsyncMock(return_value=[])
    repo.get_market_prices = AsyncMock(return_value=[])
    repo.get_competitive_pricing_data = AsyncMock(return_value={})
    repo.get_brand_multipliers = AsyncMock(return_value=[])
    repo.get_latest_price = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def pricing_engine(mock_db_session, mock_repository):
    """PricingEngine instance with mocked dependencies"""
    engine = PricingEngine(mock_db_session)
    engine.repository = mock_repository
    return engine


@pytest.fixture
def sample_product():
    """Sample product"""
    product = MagicMock(spec=Product)
    product.id = uuid.uuid4()
    product.name = "Nike Air Jordan 1"
    product.brand_id = uuid.uuid4()
    product.category_id = uuid.uuid4()

    brand = MagicMock(spec=Brand)
    brand.id = product.brand_id
    brand.name = "Nike"
    product.brand = brand

    return product


@pytest.fixture
def sample_inventory_item():
    """Sample inventory item"""
    item = MagicMock(spec=InventoryItem)
    item.id = uuid.uuid4()
    item.purchase_price = Decimal("100.00")
    item.quantity = 1
    return item


@pytest.fixture
def sample_context(sample_product, sample_inventory_item):
    """Sample pricing context"""
    return PricingContext(
        product=sample_product,
        inventory_item=sample_inventory_item,
        condition="new",
        target_margin=Decimal("25.0"),
    )


@pytest.fixture
def sample_price_rule():
    """Sample price rule"""
    rule = MagicMock(spec=PriceRule)
    rule.id = uuid.uuid4()
    rule.name = "Test Rule"
    rule.rule_type = "cost_plus"
    rule.base_markup_percent = Decimal("25.0")
    rule.minimum_margin_percent = Decimal("15.0")
    rule.maximum_discount_percent = Decimal("10.0")
    rule.seasonal_adjustments = None
    rule.condition_multipliers = None
    rule.priority = 1
    rule.active = True
    return rule


# ===== MAIN PRICING METHOD TESTS =====


@pytest.mark.asyncio
async def test_calculate_optimal_price_success(pricing_engine, sample_context, mock_repository):
    """Test successful optimal price calculation"""
    # Mock repository methods
    mock_repository.get_active_price_rules = AsyncMock(return_value=[])

    # Mock market prices
    market_price = MagicMock()
    market_price.last_sale = Decimal("150.00")
    market_price.average_price = Decimal("145.00")
    mock_repository.get_market_prices = AsyncMock(return_value=[market_price])

    # Mock competitive data
    mock_repository.get_competitive_pricing_data = AsyncMock(
        return_value={"platforms": {"stockx": {"last_sale": Decimal("148.00")}}}
    )

    result = await pricing_engine.calculate_optimal_price(sample_context)

    assert isinstance(result, PricingResult)
    assert result.suggested_price > Decimal("0")
    assert isinstance(result.strategy_used, PricingStrategy)
    assert Decimal("0") <= result.confidence_score <= Decimal("1")
    assert result.margin_percent >= Decimal("0")
    assert isinstance(result.reasoning, list)
    assert len(result.reasoning) > 0


@pytest.mark.asyncio
async def test_calculate_optimal_price_with_custom_strategies(
    pricing_engine, sample_context, mock_repository
):
    """Test optimal price with custom strategy list"""
    mock_repository.get_active_price_rules = AsyncMock(return_value=[])

    # Only cost-plus should succeed
    strategies = [PricingStrategy.COST_PLUS]

    result = await pricing_engine.calculate_optimal_price(sample_context, strategies)

    assert result.strategy_used == PricingStrategy.COST_PLUS
    assert result.confidence_score == Decimal("0.85")


@pytest.mark.asyncio
async def test_calculate_optimal_price_fallback_to_cost_plus(
    pricing_engine, sample_context, mock_repository
):
    """Test fallback to cost-plus when other strategies fail"""
    mock_repository.get_active_price_rules = AsyncMock(return_value=[])
    mock_repository.get_market_prices = AsyncMock(return_value=[])  # No market data
    mock_repository.get_competitive_pricing_data = AsyncMock(return_value={})  # No competitive data

    result = await pricing_engine.calculate_optimal_price(sample_context)

    assert result.strategy_used == PricingStrategy.COST_PLUS


@pytest.mark.asyncio
async def test_get_applicable_rules(pricing_engine, sample_context, mock_repository):
    """Test getting applicable pricing rules"""
    expected_rules = [MagicMock(), MagicMock()]
    mock_repository.get_active_price_rules = AsyncMock(return_value=expected_rules)

    result = await pricing_engine._get_applicable_rules(sample_context)

    assert result == expected_rules
    mock_repository.get_active_price_rules.assert_called_once_with(
        brand_id=sample_context.product.brand_id,
        category_id=sample_context.product.category_id,
        platform_id=sample_context.platform_id,
    )


# ===== COST-PLUS PRICING TESTS =====


@pytest.mark.asyncio
async def test_calculate_cost_plus_price_with_inventory_item(
    pricing_engine, sample_context, sample_price_rule
):
    """Test cost-plus pricing with inventory item"""
    result = await pricing_engine._calculate_cost_plus_price(sample_context, [sample_price_rule])

    # Expected: 100 * 1.25 = 125.00
    assert result.suggested_price == Decimal("125.00")
    assert result.strategy_used == PricingStrategy.COST_PLUS
    assert result.confidence_score == Decimal("0.85")
    assert result.markup_percent == Decimal("25.00")
    assert "Base cost from inventory item" in result.reasoning[1]


@pytest.mark.asyncio
async def test_calculate_cost_plus_price_without_inventory_item(
    pricing_engine, sample_context, mock_repository
):
    """Test cost-plus pricing without inventory item"""
    sample_context.inventory_item = None

    # Mock estimated cost
    mock_repository.get_latest_price = AsyncMock(return_value=None)
    mock_repository.get_market_prices = AsyncMock(return_value=[])

    result = await pricing_engine._calculate_cost_plus_price(sample_context, [])

    # Should use default cost of 50.00
    assert result.suggested_price == Decimal("62.50")  # 50 * 1.25
    assert "Estimated base cost" in result.reasoning[1]


@pytest.mark.asyncio
async def test_calculate_cost_plus_price_with_condition_multiplier(
    pricing_engine, sample_context, sample_price_rule
):
    """Test cost-plus pricing with condition multiplier"""
    sample_context.condition = "good"  # 0.75 multiplier

    result = await pricing_engine._calculate_cost_plus_price(sample_context, [])

    # 100 * 1.25 * 0.75 = 93.75
    assert result.suggested_price == Decimal("93.75")
    assert "Condition 'good' multiplier" in str(result.reasoning)


@pytest.mark.asyncio
async def test_calculate_cost_plus_price_with_brand_multipliers(
    pricing_engine, sample_context, mock_repository
):
    """Test cost-plus pricing with brand multipliers"""
    brand_multiplier = MagicMock()
    brand_multiplier.is_effective = MagicMock(return_value=True)
    brand_multiplier.multiplier_value = Decimal("1.15")
    brand_multiplier.multiplier_type = "premium"

    mock_repository.get_brand_multipliers = AsyncMock(return_value=[brand_multiplier])

    result = await pricing_engine._calculate_cost_plus_price(sample_context, [])

    # 100 * 1.25 * 1.15 = 143.75
    assert result.suggested_price == Decimal("143.75")
    assert "premium multiplier" in str(result.reasoning)


# ===== MARKET-BASED PRICING TESTS =====


@pytest.mark.asyncio
async def test_calculate_market_based_price_success(
    pricing_engine, sample_context, mock_repository
):
    """Test market-based pricing with valid market data"""
    market_price1 = MagicMock()
    market_price1.last_sale = Decimal("150.00")
    market_price1.average_price = Decimal("145.00")

    market_price2 = MagicMock()
    market_price2.last_sale = Decimal("155.00")
    market_price2.average_price = Decimal("150.00")

    mock_repository.get_market_prices = AsyncMock(return_value=[market_price1, market_price2])

    result = await pricing_engine._calculate_market_based_price(sample_context, [])

    # Average: (150 + 155) / 2 = 152.5, positioned 2% below = 149.45
    assert result.suggested_price == Decimal("149.45")
    assert result.strategy_used == PricingStrategy.MARKET_BASED
    assert result.confidence_score == Decimal("0.90")
    assert result.market_position == "slightly_below_market"
    assert "Market average from 2 data points" in str(result.reasoning)


@pytest.mark.asyncio
async def test_calculate_market_based_price_no_market_data(
    pricing_engine, sample_context, mock_repository
):
    """Test market-based pricing fails without market data"""
    mock_repository.get_market_prices = AsyncMock(return_value=[])

    with pytest.raises(ValueError, match="No market data available"):
        await pricing_engine._calculate_market_based_price(sample_context, [])


@pytest.mark.asyncio
async def test_calculate_market_based_price_with_average_price_fallback(
    pricing_engine, sample_context, mock_repository
):
    """Test market-based pricing uses average_price if last_sale is None"""
    market_price = MagicMock()
    market_price.last_sale = None
    market_price.average_price = Decimal("140.00")

    mock_repository.get_market_prices = AsyncMock(return_value=[market_price])

    result = await pricing_engine._calculate_market_based_price(sample_context, [])

    # 140 * 0.98 = 137.20
    assert result.suggested_price == Decimal("137.20")


@pytest.mark.asyncio
async def test_calculate_market_based_price_with_minimum_margin(
    pricing_engine, sample_context, mock_repository
):
    """Test market-based pricing respects minimum margin"""
    # Very low market price
    market_price = MagicMock()
    market_price.last_sale = Decimal("80.00")  # Below min margin threshold

    mock_repository.get_market_prices = AsyncMock(return_value=[market_price])

    # Mock _estimate_product_cost to return 100.00
    pricing_engine._estimate_product_cost = AsyncMock(return_value=Decimal("100.00"))

    result = await pricing_engine._calculate_market_based_price(sample_context, [])

    # Should adjust to meet 15% minimum margin
    # Min price = 100 / (1 - 0.15) = 117.65
    assert result.suggested_price >= Decimal("117.65")
    assert "minimum" in str(result.reasoning).lower()


@pytest.mark.asyncio
async def test_calculate_market_based_price_with_seasonal_adjustment(
    pricing_engine, sample_context, mock_repository
):
    """Test market-based pricing with seasonal adjustments"""
    market_price = MagicMock()
    market_price.last_sale = Decimal("150.00")
    mock_repository.get_market_prices = AsyncMock(return_value=[market_price])

    # Create rule with seasonal adjustment
    rule = MagicMock(spec=PriceRule)
    rule.rule_type = "market_based"
    rule.seasonal_adjustments = {1: 1.1, 12: 1.2}
    rule.get_seasonal_adjustment = MagicMock(return_value=Decimal("1.1"))

    result = await pricing_engine._calculate_market_based_price(sample_context, [rule])

    # 150 * 1.1 (seasonal) * 0.98 (positioning) = 161.70
    assert result.suggested_price == Decimal("161.70")
    assert "Seasonal adjustment" in str(result.reasoning)


# ===== COMPETITIVE PRICING TESTS =====


@pytest.mark.asyncio
async def test_calculate_competitive_price_success(pricing_engine, sample_context, mock_repository):
    """Test competitive pricing with valid competitor data"""
    competitive_data = {
        "platforms": {
            "stockx": {"last_sale": Decimal("145.00")},
            "goat": {"lowest_ask": Decimal("150.00")},
            "ebay": {"last_sale": Decimal("148.00")},
        }
    }
    mock_repository.get_competitive_pricing_data = AsyncMock(return_value=competitive_data)

    result = await pricing_engine._calculate_competitive_price(sample_context, [])

    # Min: 145, Max: 150, Avg: 147.67
    # Positioned between min and avg: (145 + 147.67) / 2 = 146.33
    assert result.suggested_price == Decimal("146.33")
    assert result.strategy_used == PricingStrategy.COMPETITIVE
    assert result.confidence_score == Decimal("0.88")
    assert result.market_position == "competitive_positioning"
    assert result.price_range is not None


@pytest.mark.asyncio
async def test_calculate_competitive_price_no_data(pricing_engine, sample_context, mock_repository):
    """Test competitive pricing fails without competitor data"""
    mock_repository.get_competitive_pricing_data = AsyncMock(return_value={})

    with pytest.raises(ValueError, match="No competitive data available"):
        await pricing_engine._calculate_competitive_price(sample_context, [])


@pytest.mark.asyncio
async def test_calculate_competitive_price_with_max_discount_rule(
    pricing_engine, sample_context, mock_repository, sample_price_rule
):
    """Test competitive pricing with maximum discount rule"""
    competitive_data = {"platforms": {"stockx": {"last_sale": Decimal("150.00")}}}
    mock_repository.get_competitive_pricing_data = AsyncMock(return_value=competitive_data)

    # Mock _estimate_product_cost to return 100.00
    pricing_engine._estimate_product_cost = AsyncMock(return_value=Decimal("100.00"))

    sample_price_rule.rule_type = "competitive"
    sample_price_rule.maximum_discount_percent = Decimal("5.0")

    result = await pricing_engine._calculate_competitive_price(sample_context, [sample_price_rule])

    # 150 * (1 - 0.05) = 142.50
    assert result.suggested_price == Decimal("142.50")
    assert "5.0% below lowest competitor" in str(result.reasoning)


@pytest.mark.asyncio
async def test_calculate_competitive_price_ensures_minimum_margin(
    pricing_engine, sample_context, mock_repository
):
    """Test competitive pricing respects minimum margin"""
    # Very low competitor prices
    competitive_data = {"platforms": {"stockx": {"last_sale": Decimal("90.00")}}}
    mock_repository.get_competitive_pricing_data = AsyncMock(return_value=competitive_data)

    # Mock _estimate_product_cost to return 100.00
    pricing_engine._estimate_product_cost = AsyncMock(return_value=Decimal("100.00"))

    result = await pricing_engine._calculate_competitive_price(sample_context, [])

    # Should enforce 10% minimum margin
    # Min price = 100 / (1 - 0.10) = 111.11
    assert result.suggested_price >= Decimal("111.11")


# ===== VALUE-BASED PRICING TESTS =====


@pytest.mark.asyncio
async def test_calculate_value_based_price_with_market_baseline(
    pricing_engine, sample_context, mock_repository
):
    """Test value-based pricing with market baseline"""
    market_price = MagicMock()
    market_price.last_sale = Decimal("150.00")
    mock_repository.get_market_prices = AsyncMock(return_value=[market_price])

    result = await pricing_engine._calculate_value_based_price(sample_context, [])

    # Market baseline: 150 * 0.98 = 147
    # Brand premium: 147 * 1.1 = 161.70
    # Demand/scarcity: neutral (1.0)
    assert result.suggested_price == Decimal("161.70")
    assert result.strategy_used == PricingStrategy.VALUE_BASED
    assert result.confidence_score == Decimal("0.82")
    assert result.market_position == "value_premium"


@pytest.mark.asyncio
async def test_calculate_value_based_price_with_cost_baseline_fallback(
    pricing_engine, sample_context, mock_repository
):
    """Test value-based pricing falls back to cost-plus baseline"""
    mock_repository.get_market_prices = AsyncMock(return_value=[])  # No market data

    result = await pricing_engine._calculate_value_based_price(sample_context, [])

    # Cost-plus baseline: 100 * 1.25 = 125
    # Brand premium: 125 * 1.1 = 137.50
    assert result.suggested_price == Decimal("137.50")
    assert "Cost-plus baseline" in str(result.reasoning)


@pytest.mark.asyncio
async def test_calculate_value_based_price_with_brand_premium(
    pricing_engine, sample_context, mock_repository
):
    """Test value-based pricing applies brand premium"""
    market_price = MagicMock()
    market_price.last_sale = Decimal("150.00")
    mock_repository.get_market_prices = AsyncMock(return_value=[market_price])

    # Mock brand premium
    pricing_engine._calculate_brand_premium = AsyncMock(return_value=Decimal("1.2"))

    result = await pricing_engine._calculate_value_based_price(sample_context, [])

    # 147 (market baseline) * 1.2 (brand premium) = 176.40
    assert result.suggested_price == Decimal("176.40")
    assert "Brand premium applied: 20.0%" in str(result.reasoning)


@pytest.mark.asyncio
async def test_calculate_value_based_price_with_demand_adjustment(
    pricing_engine, sample_context, mock_repository
):
    """Test value-based pricing applies demand adjustment"""
    market_price = MagicMock()
    market_price.last_sale = Decimal("150.00")
    mock_repository.get_market_prices = AsyncMock(return_value=[market_price])

    # Mock high demand
    pricing_engine._calculate_demand_adjustment = AsyncMock(return_value=Decimal("1.15"))

    result = await pricing_engine._calculate_value_based_price(sample_context, [])

    # 147 * 1.1 (brand) * 1.15 (demand) = 185.96
    assert result.suggested_price == Decimal("185.96")
    assert "High demand premium: 15.0%" in str(result.reasoning)


@pytest.mark.asyncio
async def test_calculate_value_based_price_with_scarcity_multiplier(
    pricing_engine, sample_context, mock_repository
):
    """Test value-based pricing applies scarcity multiplier"""
    market_price = MagicMock()
    market_price.last_sale = Decimal("150.00")
    mock_repository.get_market_prices = AsyncMock(return_value=[market_price])

    # Mock scarcity
    pricing_engine._calculate_scarcity_multiplier = AsyncMock(return_value=Decimal("1.25"))
    # Mock _estimate_product_cost for margin calculation
    pricing_engine._estimate_product_cost = AsyncMock(return_value=Decimal("100.00"))

    result = await pricing_engine._calculate_value_based_price(sample_context, [])

    # 147 * 1.1 * 1.0 * 1.25 = 202.125 -> 202.13
    assert result.suggested_price == Decimal("202.13")
    assert "Scarcity premium: 25.0%" in str(result.reasoning)


# ===== DYNAMIC PRICING TESTS =====


@pytest.mark.asyncio
async def test_calculate_dynamic_price_success(pricing_engine, sample_context, mock_repository):
    """Test dynamic pricing combines multiple strategies"""
    # Mock market data
    market_price = MagicMock()
    market_price.last_sale = Decimal("150.00")
    mock_repository.get_market_prices = AsyncMock(return_value=[market_price])

    # Mock competitive data
    competitive_data = {"platforms": {"stockx": {"last_sale": Decimal("148.00")}}}
    mock_repository.get_competitive_pricing_data = AsyncMock(return_value=competitive_data)

    result = await pricing_engine._calculate_dynamic_price(sample_context, [])

    assert result.strategy_used == PricingStrategy.DYNAMIC
    assert result.confidence_score == Decimal("0.92")
    assert result.market_position == "dynamic_optimal"
    assert "Weighted average of" in str(result.reasoning)


@pytest.mark.asyncio
async def test_calculate_dynamic_price_fallback_to_cost_plus(
    pricing_engine, sample_context, mock_repository
):
    """Test dynamic pricing works even without market/competitive data"""
    mock_repository.get_market_prices = AsyncMock(return_value=[])
    mock_repository.get_competitive_pricing_data = AsyncMock(return_value={})
    # Mock _estimate_product_cost for margin calculation
    pricing_engine._estimate_product_cost = AsyncMock(return_value=Decimal("100.00"))

    result = await pricing_engine._calculate_dynamic_price(sample_context, [])

    # Dynamic pricing always returns DYNAMIC strategy, even with fallback data
    assert result.strategy_used == PricingStrategy.DYNAMIC
    # Should still calculate a valid price using available data
    assert result.suggested_price > Decimal("0")
    assert "Weighted average of" in str(result.reasoning)


@pytest.mark.asyncio
async def test_calculate_dynamic_price_with_velocity_adjustment(
    pricing_engine, sample_context, mock_repository
):
    """Test dynamic pricing applies velocity adjustment"""
    market_price = MagicMock()
    market_price.last_sale = Decimal("150.00")
    mock_repository.get_market_prices = AsyncMock(return_value=[market_price])

    # Mock velocity adjustment
    pricing_engine._get_velocity_adjustment = AsyncMock(return_value=Decimal("0.95"))

    result = await pricing_engine._calculate_dynamic_price(sample_context, [])

    # Should include velocity adjustment
    assert "velocity adjustment: -5.0%" in str(result.reasoning).lower()


# ===== HELPER METHOD TESTS =====


def test_select_best_pricing_result(pricing_engine):
    """Test selecting best pricing result"""
    results = {
        PricingStrategy.COST_PLUS: PricingResult(
            suggested_price=Decimal("120.00"),
            strategy_used=PricingStrategy.COST_PLUS,
            confidence_score=Decimal("0.85"),
            margin_percent=Decimal("20.0"),
            markup_percent=Decimal("20.0"),
            reasoning=[],
        ),
        PricingStrategy.MARKET_BASED: PricingResult(
            suggested_price=Decimal("147.00"),
            strategy_used=PricingStrategy.MARKET_BASED,
            confidence_score=Decimal("0.90"),
            margin_percent=Decimal("30.0"),
            markup_percent=Decimal("47.0"),
            reasoning=[],
        ),
    }

    context = MagicMock(spec=PricingContext)
    best = pricing_engine._select_best_pricing_result(results, context)

    # Market-based should win (0.90 * 0.9 = 0.81 vs 0.85 * 0.7 = 0.595)
    assert best.strategy_used == PricingStrategy.MARKET_BASED


@pytest.mark.asyncio
async def test_apply_final_adjustments_with_minimum_margin(
    pricing_engine, sample_context, mock_repository, sample_price_rule
):
    """Test final adjustments enforce minimum margin"""
    result = PricingResult(
        suggested_price=Decimal("110.00"),
        strategy_used=PricingStrategy.MARKET_BASED,
        confidence_score=Decimal("0.90"),
        margin_percent=Decimal("10.0"),
        markup_percent=Decimal("10.0"),
        reasoning=[],
    )

    sample_price_rule.minimum_margin_percent = Decimal("20.0")

    # Mock _estimate_product_cost for margin calculation
    pricing_engine._estimate_product_cost = AsyncMock(return_value=Decimal("100.00"))

    final = await pricing_engine._apply_final_adjustments(
        result, sample_context, [sample_price_rule]
    )

    # Should raise to meet 20% margin: 100 / (1 - 0.20) = 125.00
    assert final.suggested_price >= Decimal("125.00")
    assert final.adjustments_applied is not None


@pytest.mark.asyncio
async def test_apply_final_adjustments_psychological_pricing(
    pricing_engine, sample_context, mock_repository
):
    """Test final adjustments apply psychological pricing"""
    result = PricingResult(
        suggested_price=Decimal("123.45"),
        strategy_used=PricingStrategy.MARKET_BASED,
        confidence_score=Decimal("0.90"),
        margin_percent=Decimal("20.0"),
        markup_percent=Decimal("23.45"),
        reasoning=[],
    )

    final = await pricing_engine._apply_final_adjustments(result, sample_context, [])

    # Should round to nearest 5: 125.00
    assert final.suggested_price == Decimal("125.00")
    assert "psychological" in str(final.adjustments_applied).lower()


@pytest.mark.asyncio
async def test_apply_brand_multipliers(pricing_engine, mock_repository):
    """Test applying brand multipliers"""
    multiplier1 = MagicMock()
    multiplier1.is_effective = MagicMock(return_value=True)
    multiplier1.multiplier_value = Decimal("1.15")
    multiplier1.multiplier_type = "premium"

    multiplier2 = MagicMock()
    multiplier2.is_effective = MagicMock(return_value=True)
    multiplier2.multiplier_value = Decimal("1.05")
    multiplier2.multiplier_type = "seasonal"

    mock_repository.get_brand_multipliers = AsyncMock(return_value=[multiplier1, multiplier2])

    final_price, adjustments = await pricing_engine._apply_brand_multipliers(
        Decimal("100.00"), uuid.uuid4()
    )

    # 100 * 1.15 * 1.05 = 120.75
    assert final_price == Decimal("120.75")
    assert len(adjustments) == 2


@pytest.mark.asyncio
async def test_estimate_product_cost_from_recent_purchase(
    pricing_engine, sample_product, mock_repository
):
    """Test cost estimation from recent purchase price"""
    recent_price = MagicMock()
    recent_price.price_amount = Decimal("95.00")

    mock_repository.get_latest_price = AsyncMock(return_value=recent_price)

    cost = await pricing_engine._estimate_product_cost(sample_product)

    assert cost == Decimal("95.00")


@pytest.mark.asyncio
async def test_estimate_product_cost_from_market_prices(
    pricing_engine, sample_product, mock_repository
):
    """Test cost estimation from market prices"""
    mock_repository.get_latest_price = AsyncMock(return_value=None)

    market_price = MagicMock()
    market_price.last_sale = Decimal("150.00")
    market_price.average_price = Decimal("145.00")

    mock_repository.get_market_prices = AsyncMock(return_value=[market_price])

    cost = await pricing_engine._estimate_product_cost(sample_product)

    # Average of last_sale OR average_price (not both): 150 * 0.65 = 97.50
    assert cost == Decimal("97.50")


@pytest.mark.asyncio
async def test_estimate_product_cost_default_fallback(
    pricing_engine, sample_product, mock_repository
):
    """Test cost estimation default fallback"""
    mock_repository.get_latest_price = AsyncMock(return_value=None)
    mock_repository.get_market_prices = AsyncMock(return_value=[])

    cost = await pricing_engine._estimate_product_cost(sample_product)

    assert cost == Decimal("50.00")


def test_apply_psychological_pricing_low_price(pricing_engine):
    """Test psychological pricing for low prices (< 20)"""
    result = pricing_engine._apply_psychological_pricing(Decimal("15.50"))
    # Rounds up to 16, then subtracts 0.05 = 15.95
    assert result == Decimal("15.95")


def test_apply_psychological_pricing_medium_price(pricing_engine):
    """Test psychological pricing for medium prices (20-100)"""
    result = pricing_engine._apply_psychological_pricing(Decimal("75.50"))
    # Rounds up to 76, then subtracts 0.01 = 75.99
    assert result == Decimal("75.99")


def test_apply_psychological_pricing_high_price(pricing_engine):
    """Test psychological pricing for high prices (> 100)"""
    result = pricing_engine._apply_psychological_pricing(Decimal("123.45"))
    # Round to nearest 5: 125.00
    assert result == Decimal("125.00")


@pytest.mark.asyncio
async def test_get_condition_multiplier_default(pricing_engine):
    """Test condition multiplier defaults"""
    assert await pricing_engine._get_condition_multiplier("new", []) == Decimal("1.0")
    assert await pricing_engine._get_condition_multiplier("excellent", []) == Decimal("0.92")
    assert await pricing_engine._get_condition_multiplier("good", []) == Decimal("0.75")
    assert await pricing_engine._get_condition_multiplier("poor", []) == Decimal("0.50")


@pytest.mark.asyncio
async def test_get_condition_multiplier_from_rule(pricing_engine, sample_price_rule):
    """Test condition multiplier from rule"""
    sample_price_rule.condition_multipliers = {"new": 1.05, "good": 0.80}

    result = await pricing_engine._get_condition_multiplier("new", [sample_price_rule])
    assert result == Decimal("1.05")


@pytest.mark.asyncio
async def test_calculate_brand_premium(pricing_engine):
    """Test brand premium calculation"""
    result = await pricing_engine._calculate_brand_premium(uuid.uuid4())
    assert result == Decimal("1.1")


@pytest.mark.asyncio
async def test_calculate_demand_adjustment(pricing_engine):
    """Test demand adjustment calculation"""
    result = await pricing_engine._calculate_demand_adjustment(uuid.uuid4())
    assert result == Decimal("1.0")


@pytest.mark.asyncio
async def test_calculate_scarcity_multiplier(pricing_engine):
    """Test scarcity multiplier calculation"""
    result = await pricing_engine._calculate_scarcity_multiplier(uuid.uuid4())
    assert result == Decimal("1.0")


@pytest.mark.asyncio
async def test_get_velocity_adjustment(pricing_engine):
    """Test velocity adjustment calculation"""
    result = await pricing_engine._get_velocity_adjustment(uuid.uuid4())
    assert result == Decimal("1.0")


# ===== STRATEGY ROUTING TESTS =====


@pytest.mark.asyncio
async def test_calculate_strategy_price_cost_plus(pricing_engine, sample_context):
    """Test strategy routing for cost-plus"""
    result = await pricing_engine._calculate_strategy_price(
        sample_context, PricingStrategy.COST_PLUS, []
    )
    assert result.strategy_used == PricingStrategy.COST_PLUS


@pytest.mark.asyncio
async def test_calculate_strategy_price_invalid_strategy(pricing_engine, sample_context):
    """Test strategy routing with invalid strategy"""
    with pytest.raises(ValueError, match="Unknown pricing strategy"):
        await pricing_engine._calculate_strategy_price(sample_context, "invalid_strategy", [])

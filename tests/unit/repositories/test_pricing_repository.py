"""
Unit tests for PricingRepository
Testing domain-specific pricing data access methods
"""

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from domains.pricing.models import BrandMultiplier, MarketPrice, PriceHistory, PriceRule
from domains.pricing.repositories.pricing_repository import PricingRepository


@pytest.fixture
def mock_db_session():
    """Create mock database session"""
    session = MagicMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def pricing_repo(mock_db_session):
    """Create PricingRepository instance with mock session"""
    return PricingRepository(mock_db_session)


class TestPriceRulesManagement:
    """Test price rules operations"""

    async def test_get_active_price_rules_no_filters(self, pricing_repo, mock_db_session):
        """Test getting active price rules without filters"""
        # Arrange
        mock_rules = [
            PriceRule(id=uuid.uuid4(), rule_type="markup", active=True),
            PriceRule(id=uuid.uuid4(), rule_type="discount", active=True),
        ]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_rules)
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await pricing_repo.get_active_price_rules()

        # Assert
        assert result == mock_rules
        mock_db_session.execute.assert_awaited_once()

    async def test_get_active_price_rules_with_brand_filter(self, pricing_repo, mock_db_session):
        """Test getting active price rules filtered by brand"""
        # Arrange
        brand_id = uuid.uuid4()
        mock_rules = [PriceRule(id=uuid.uuid4(), brand_id=brand_id, active=True)]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_rules)
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await pricing_repo.get_active_price_rules(brand_id=brand_id)

        # Assert
        assert result == mock_rules
        mock_db_session.execute.assert_awaited_once()

    async def test_create_price_rule(self, pricing_repo, mock_db_session):
        """Test creating new price rule"""
        # Arrange
        rule_data = {
            "rule_type": "markup",
            "active": True,
            "priority": 1,
        }

        # Act
        with MagicMock():
            PriceRule.__init__ = MagicMock(return_value=None)
            await pricing_repo.create_price_rule(rule_data)

        # Assert
        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_awaited_once()

    async def test_update_price_rule_success(self, pricing_repo, mock_db_session):
        """Test updating existing price rule"""
        # Arrange
        rule_id = uuid.uuid4()
        update_data = {"active": False, "priority": 5}
        mock_rule = MagicMock()
        mock_rule.id = rule_id
        mock_rule.active = True
        mock_rule.priority = 1

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_rule)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await pricing_repo.update_price_rule(rule_id, update_data)

        # Assert
        assert result == mock_rule
        assert not result.active
        assert result.priority == 5
        mock_db_session.flush.assert_awaited_once()

    async def test_update_price_rule_not_found(self, pricing_repo, mock_db_session):
        """Test updating non-existent price rule"""
        # Arrange
        rule_id = uuid.uuid4()
        update_data = {"active": False}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await pricing_repo.update_price_rule(rule_id, update_data)

        # Assert
        assert result is None
        mock_db_session.flush.assert_not_awaited()


class TestBrandMultipliers:
    """Test brand multiplier operations"""

    async def test_get_brand_multipliers_default_date(self, pricing_repo, mock_db_session):
        """Test getting brand multipliers with default effective date"""
        # Arrange
        brand_id = uuid.uuid4()
        mock_multipliers = [
            BrandMultiplier(
                id=uuid.uuid4(),
                brand_id=brand_id,
                multiplier_type="seasonal",
                active=True,
            )
        ]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_multipliers)
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await pricing_repo.get_brand_multipliers(brand_id)

        # Assert
        assert result == mock_multipliers
        mock_db_session.execute.assert_awaited_once()

    async def test_get_brand_multipliers_with_type_filter(self, pricing_repo, mock_db_session):
        """Test getting brand multipliers filtered by type"""
        # Arrange
        brand_id = uuid.uuid4()
        multiplier_type = "promotional"
        mock_multipliers = [
            BrandMultiplier(
                id=uuid.uuid4(),
                brand_id=brand_id,
                multiplier_type=multiplier_type,
                active=True,
            )
        ]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_multipliers)
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await pricing_repo.get_brand_multipliers(brand_id, multiplier_type=multiplier_type)

        # Assert
        assert result == mock_multipliers
        mock_db_session.execute.assert_awaited_once()

    async def test_create_brand_multiplier(self, pricing_repo, mock_db_session):
        """Test creating new brand multiplier"""
        # Arrange
        multiplier_data = {
            "brand_id": uuid.uuid4(),
            "multiplier_type": "seasonal",
            "multiplier_value": Decimal("1.15"),
            "active": True,
        }

        # Act
        with MagicMock():
            BrandMultiplier.__init__ = MagicMock(return_value=None)
            await pricing_repo.create_brand_multiplier(multiplier_data)

        # Assert
        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_awaited_once()


class TestPriceHistoryTracking:
    """Test price history operations"""

    async def test_record_price_history(self, pricing_repo, mock_db_session):
        """Test recording price history entry"""
        # Arrange
        price_data = {
            "product_id": uuid.uuid4(),
            "price_type": "listing",
            "price_amount": Decimal("150.00"),
            "price_date": date.today(),
        }

        # Act
        with MagicMock():
            PriceHistory.__init__ = MagicMock(return_value=None)
            await pricing_repo.record_price_history(price_data)

        # Assert
        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_awaited_once()

    async def test_get_price_history_default_params(self, pricing_repo, mock_db_session):
        """Test getting price history with default parameters"""
        # Arrange
        product_id = uuid.uuid4()
        mock_history = [
            PriceHistory(
                id=uuid.uuid4(),
                product_id=product_id,
                price_type="listing",
                price_date=date.today(),
            )
        ]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_history)
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await pricing_repo.get_price_history(product_id)

        # Assert
        assert result == mock_history
        mock_db_session.execute.assert_awaited_once()

    async def test_get_price_history_with_filters(self, pricing_repo, mock_db_session):
        """Test getting price history with type and platform filters"""
        # Arrange
        product_id = uuid.uuid4()
        platform_id = uuid.uuid4()
        price_types = ["listing", "sale"]
        mock_history = []

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_history)
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await pricing_repo.get_price_history(
            product_id, days_back=60, price_types=price_types, platform_id=platform_id
        )

        # Assert
        assert result == mock_history
        mock_db_session.execute.assert_awaited_once()

    async def test_get_latest_price_found(self, pricing_repo, mock_db_session):
        """Test getting latest price when it exists"""
        # Arrange
        product_id = uuid.uuid4()
        mock_price = PriceHistory(
            id=uuid.uuid4(),
            product_id=product_id,
            price_type="listing",
            price_amount=Decimal("200.00"),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_price)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await pricing_repo.get_latest_price(product_id)

        # Assert
        assert result == mock_price
        mock_db_session.execute.assert_awaited_once()

    async def test_get_latest_price_not_found(self, pricing_repo, mock_db_session):
        """Test getting latest price when none exists"""
        # Arrange
        product_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await pricing_repo.get_latest_price(product_id)

        # Assert
        assert result is None


class TestMarketPriceData:
    """Test market price operations"""

    async def test_get_market_prices_no_filters(self, pricing_repo, mock_db_session):
        """Test getting market prices without filters"""
        # Arrange
        product_id = uuid.uuid4()
        mock_prices = [
            MarketPrice(
                id=uuid.uuid4(),
                product_id=product_id,
                platform_name="StockX",
                price_date=date.today(),
            )
        ]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_prices)
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await pricing_repo.get_market_prices(product_id)

        # Assert
        assert result == mock_prices
        mock_db_session.execute.assert_awaited_once()

    async def test_get_market_prices_with_filters(self, pricing_repo, mock_db_session):
        """Test getting market prices with platform and condition filters"""
        # Arrange
        product_id = uuid.uuid4()
        mock_prices = []

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_prices)
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await pricing_repo.get_market_prices(
            product_id, platform_name="GOAT", condition="new", days_back=14
        )

        # Assert
        assert result == mock_prices
        mock_db_session.execute.assert_awaited_once()

    async def test_create_market_price(self, pricing_repo, mock_db_session):
        """Test creating market price entry"""
        # Arrange
        market_data = {
            "product_id": uuid.uuid4(),
            "platform_name": "StockX",
            "condition": "new",
            "price_date": date.today(),
            "lowest_ask": Decimal("180.00"),
            "highest_bid": Decimal("170.00"),
        }

        # Act
        with MagicMock():
            MarketPrice.__init__ = MagicMock(return_value=None)
            await pricing_repo.create_market_price(market_data)

        # Assert
        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_awaited_once()

    async def test_get_competitive_pricing_data_with_results(self, pricing_repo, mock_db_session):
        """Test getting competitive pricing data with market prices"""
        # Arrange
        product_id = uuid.uuid4()

        # Create mock market prices using MagicMock
        mock_price1 = MagicMock()
        mock_price1.platform_name = "StockX"
        mock_price1.price_date = date.today()
        mock_price1.lowest_ask = Decimal("180.00")
        mock_price1.highest_bid = Decimal("170.00")
        mock_price1.last_sale = Decimal("175.00")
        mock_price1.average_price = Decimal("176.00")
        mock_price1.sales_volume = 50

        mock_price2 = MagicMock()
        mock_price2.platform_name = "GOAT"
        mock_price2.price_date = date.today()
        mock_price2.lowest_ask = Decimal("185.00")
        mock_price2.highest_bid = Decimal("175.00")
        mock_price2.last_sale = Decimal("180.00")
        mock_price2.average_price = Decimal("181.00")
        mock_price2.sales_volume = 30

        mock_prices = [mock_price1, mock_price2]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_prices)
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await pricing_repo.get_competitive_pricing_data(product_id, condition="new")

        # Assert
        assert "platforms" in result
        assert "StockX" in result["platforms"]
        assert "GOAT" in result["platforms"]
        assert result["platforms"]["StockX"]["lowest_ask"] == Decimal("180.00")
        assert result["platforms"]["GOAT"]["lowest_ask"] == Decimal("185.00")
        assert result["market_average"] == 178.5  # (176 + 181) / 2
        assert result["market_range"]["min"] == 175.0
        assert result["market_range"]["max"] == 180.0
        assert result["total_volume"] == 80  # 50 + 30
        assert result["data_points"] == 2

    async def test_get_competitive_pricing_data_empty(self, pricing_repo, mock_db_session):
        """Test getting competitive pricing data with no market prices"""
        # Arrange
        product_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[])
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await pricing_repo.get_competitive_pricing_data(product_id)

        # Assert
        assert result == {}


class TestAnalyticsQueries:
    """Test analytics and performance queries"""

    async def test_get_pricing_performance_metrics_default_dates(
        self, pricing_repo, mock_db_session
    ):
        """Test getting pricing performance metrics with default date range"""
        # Arrange
        mock_metrics = MagicMock()
        mock_metrics.total_price_changes = 100
        mock_metrics.avg_price = Decimal("150.50")
        mock_metrics.min_price = Decimal("100.00")
        mock_metrics.max_price = Decimal("200.00")
        mock_metrics.price_volatility = Decimal("25.75")

        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=mock_metrics)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await pricing_repo.get_pricing_performance_metrics()

        # Assert
        assert result["total_price_changes"] == 100
        assert result["average_price"] == 150.50
        assert result["price_range"]["min"] == 100.0
        assert result["price_range"]["max"] == 200.0
        assert result["price_volatility"] == 25.75
        assert "period" in result
        mock_db_session.execute.assert_awaited_once()

    async def test_get_pricing_performance_metrics_with_brand_filter(
        self, pricing_repo, mock_db_session
    ):
        """Test getting pricing performance metrics filtered by brand"""
        # Arrange
        brand_id = uuid.uuid4()
        mock_metrics = MagicMock()
        mock_metrics.total_price_changes = 50
        mock_metrics.avg_price = Decimal("175.00")
        mock_metrics.min_price = Decimal("150.00")
        mock_metrics.max_price = Decimal("200.00")
        mock_metrics.price_volatility = Decimal("15.50")

        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=mock_metrics)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await pricing_repo.get_pricing_performance_metrics(brand_id=brand_id)

        # Assert
        assert result["total_price_changes"] == 50
        mock_db_session.execute.assert_awaited_once()

    async def test_get_top_performing_products_by_volume(self, pricing_repo, mock_db_session):
        """Test getting top products by sales volume"""
        # Arrange
        mock_row1 = MagicMock()
        mock_row1.id = uuid.uuid4()
        mock_row1.name = "Nike Air Jordan 1"
        mock_row1.sku = "AJ1-001"
        mock_row1.brand_name = "Nike"
        mock_row1.total_volume = 1000
        mock_row1.avg_sale_price = Decimal("180.00")

        mock_row2 = MagicMock()
        mock_row2.id = uuid.uuid4()
        mock_row2.name = "Adidas Yeezy 350"
        mock_row2.sku = "YZY-350"
        mock_row2.brand_name = "Adidas"
        mock_row2.total_volume = 800
        mock_row2.avg_sale_price = Decimal("250.00")

        mock_rows = [mock_row1, mock_row2]

        mock_result = MagicMock()
        mock_result.all = MagicMock(return_value=mock_rows)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await pricing_repo.get_top_performing_products(
            limit=10, metric="volume", days_back=30
        )

        # Assert
        assert len(result) == 2
        assert result[0]["name"] == "Nike Air Jordan 1"
        assert result[0]["total_volume"] == 1000
        assert result[0]["avg_sale_price"] == 180.0
        assert result[1]["brand"] == "Adidas"
        assert result[1]["total_volume"] == 800

    async def test_get_top_performing_products_by_price_growth(self, pricing_repo, mock_db_session):
        """Test getting top products by price appreciation"""
        # Arrange
        mock_row = MagicMock()
        mock_row.id = uuid.uuid4()
        mock_row.name = "Nike Dunk Low"
        mock_row.sku = "DUNK-001"
        mock_row.brand_name = "Nike"
        mock_row.first_price = Decimal("100.00")
        mock_row.latest_price = Decimal("150.00")
        mock_row.price_growth_percent = Decimal("50.00")

        mock_rows = [mock_row]

        mock_result = MagicMock()
        mock_result.all = MagicMock(return_value=mock_rows)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await pricing_repo.get_top_performing_products(metric="price_growth")

        # Assert
        assert len(result) == 1
        assert result[0]["name"] == "Nike Dunk Low"
        assert result[0]["first_price"] == 100.0
        assert result[0]["latest_price"] == 150.0
        assert result[0]["growth_percent"] == 50.0

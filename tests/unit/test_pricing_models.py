"""
Unit tests for pricing models business logic
Testing model methods and properties for 100% coverage
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from domains.pricing.models import (
    BrandMultiplier,
    ForecastAccuracy,
    MarketPrice,
    PriceRule,
    PricingKPI,
    SalesForecast,
)


class TestPriceRule:
    """Test PriceRule model business logic"""

    def test_is_active_default_behavior(self):
        """Test is_active with default parameters"""
        now = datetime.now(timezone.utc)
        future = datetime.now(timezone.utc).replace(year=now.year + 1)

        rule = PriceRule(
            id=uuid4(),
            name="Test Rule",
            rule_type="cost_plus",
            active=True,
            effective_from=now,
            effective_until=future,
        )

        assert rule.is_active() is True

    def test_is_active_inactive_rule(self):
        """Test is_active with inactive rule"""
        rule = PriceRule(
            id=uuid4(),
            name="Inactive Rule",
            rule_type="cost_plus",
            active=False,
            effective_from=datetime.now(timezone.utc),
        )

        assert rule.is_active() is False

    def test_is_active_before_effective_date(self):
        """Test is_active before effective date"""
        future = datetime.now().replace(year=datetime.now().year + 1)

        rule = PriceRule(
            id=uuid4(),
            name="Future Rule",
            rule_type="cost_plus",
            active=True,
            effective_from=future,
        )

        assert rule.is_active() is False

    def test_is_active_after_expiry(self):
        """Test is_active after expiry date"""
        past = datetime.now().replace(year=2020)
        yesterday = (
            datetime.now().replace(day=datetime.now().day - 1)
            if datetime.now().day > 1
            else datetime.now().replace(month=datetime.now().month - 1, day=28)
        )

        rule = PriceRule(
            id=uuid4(),
            name="Expired Rule",
            rule_type="cost_plus",
            active=True,
            effective_from=past,
            effective_until=yesterday,
        )

        assert rule.is_active() is False

    def test_is_active_no_expiry(self):
        """Test is_active with no expiry date"""
        past = datetime.now().replace(year=2020)

        rule = PriceRule(
            id=uuid4(),
            name="No Expiry Rule",
            rule_type="cost_plus",
            active=True,
            effective_from=past,
            effective_until=None,
        )

        assert rule.is_active() is True

    def test_is_active_with_specific_date(self):
        """Test is_active with specific check date"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)
        check_date = datetime(2024, 6, 15)

        rule = PriceRule(
            id=uuid4(),
            name="Date Range Rule",
            rule_type="cost_plus",
            active=True,
            effective_from=start_date,
            effective_until=end_date,
        )

        assert rule.is_active(check_date) is True

    def test_get_condition_multiplier_no_data(self):
        """Test get_condition_multiplier with no data"""
        rule = PriceRule(
            id=uuid4(),
            name="No Multipliers",
            rule_type="cost_plus",
            active=True,
            effective_from=datetime.now(timezone.utc),
            condition_multipliers=None,
        )

        result = rule.get_condition_multiplier("used")
        assert result == Decimal("1.0")

    def test_get_condition_multiplier_with_data(self):
        """Test get_condition_multiplier with existing data"""
        rule = PriceRule(
            id=uuid4(),
            name="With Multipliers",
            rule_type="cost_plus",
            active=True,
            effective_from=datetime.now(timezone.utc),
            condition_multipliers={"used": 0.8, "deadstock": 0.6, "new": 1.2},
        )

        assert rule.get_condition_multiplier("used") == Decimal("0.8")
        assert rule.get_condition_multiplier("new") == Decimal("1.2")
        assert rule.get_condition_multiplier("unknown") == Decimal("1.0")

    def test_get_seasonal_adjustment_no_data(self):
        """Test get_seasonal_adjustment with no data"""
        rule = PriceRule(
            id=uuid4(),
            name="No Seasonal",
            rule_type="cost_plus",
            active=True,
            effective_from=datetime.now(timezone.utc),
            seasonal_adjustments=None,
        )

        result = rule.get_seasonal_adjustment(12)
        assert result == Decimal("1.0")

    def test_get_seasonal_adjustment_with_data(self):
        """Test get_seasonal_adjustment with existing data"""
        rule = PriceRule(
            id=uuid4(),
            name="With Seasonal",
            rule_type="cost_plus",
            active=True,
            effective_from=datetime.now(timezone.utc),
            seasonal_adjustments={"12": 1.3, "1": 1.1, "6": 0.9},
        )

        assert rule.get_seasonal_adjustment(12) == Decimal("1.3")
        assert rule.get_seasonal_adjustment(1) == Decimal("1.1")
        assert rule.get_seasonal_adjustment(7) == Decimal("1.0")


class TestBrandMultiplier:
    """Test BrandMultiplier model business logic"""

    def test_is_effective_active_today(self):
        """Test is_effective for active multiplier today"""
        multiplier = BrandMultiplier(
            id=uuid4(),
            brand_id=uuid4(),
            multiplier_type="premium",
            multiplier_value=Decimal("1.2"),
            active=True,
            effective_from=date.today(),
            effective_until=None,
        )

        assert multiplier.is_effective() is True

    def test_is_effective_inactive(self):
        """Test is_effective for inactive multiplier"""
        multiplier = BrandMultiplier(
            id=uuid4(),
            brand_id=uuid4(),
            multiplier_type="premium",
            multiplier_value=Decimal("1.2"),
            active=False,
            effective_from=date.today(),
        )

        assert multiplier.is_effective() is False

    def test_is_effective_future_date(self):
        """Test is_effective for future effective date"""
        future_date = date(2025, 12, 31)

        multiplier = BrandMultiplier(
            id=uuid4(),
            brand_id=uuid4(),
            multiplier_type="seasonal",
            multiplier_value=Decimal("0.8"),
            active=True,
            effective_from=future_date,
        )

        assert multiplier.is_effective() is False

    def test_is_effective_expired(self):
        """Test is_effective for expired multiplier"""
        past_date = date(2020, 1, 1)
        yesterday = date.today().replace(day=date.today().day - 1)

        multiplier = BrandMultiplier(
            id=uuid4(),
            brand_id=uuid4(),
            multiplier_type="discount",
            multiplier_value=Decimal("0.9"),
            active=True,
            effective_from=past_date,
            effective_until=yesterday,
        )

        assert multiplier.is_effective() is False

    def test_is_effective_with_specific_date(self):
        """Test is_effective with specific check date"""
        check_date = date(2024, 6, 15)
        start_date = date(2024, 1, 1)
        end_date = date(2024, 12, 31)

        multiplier = BrandMultiplier(
            id=uuid4(),
            brand_id=uuid4(),
            multiplier_type="premium",
            multiplier_value=Decimal("1.15"),
            active=True,
            effective_from=start_date,
            effective_until=end_date,
        )

        assert multiplier.is_effective(check_date) is True


class TestMarketPrice:
    """Test MarketPrice model business logic"""

    def test_get_market_price_last_sale(self):
        """Test get_market_price for last sale"""
        price = MarketPrice(
            id=uuid4(),
            product_id=uuid4(),
            platform_name="StockX",
            condition="new",
            price_date=date.today(),
            last_sale=Decimal("250.00"),
            lowest_ask=Decimal("280.00"),
            highest_bid=Decimal("240.00"),
            average_price=Decimal("255.00"),
        )

        result = price.get_market_price("last_sale")
        assert result == Decimal("250.00")

    def test_get_market_price_lowest_ask(self):
        """Test get_market_price for lowest ask"""
        price = MarketPrice(
            id=uuid4(),
            product_id=uuid4(),
            platform_name="StockX",
            condition="new",
            price_date=date.today(),
            lowest_ask=Decimal("280.00"),
        )

        result = price.get_market_price("lowest_ask")
        assert result == Decimal("280.00")

    def test_get_market_price_highest_bid(self):
        """Test get_market_price for highest bid"""
        price = MarketPrice(
            id=uuid4(),
            product_id=uuid4(),
            platform_name="GOAT",
            condition="used",
            price_date=date.today(),
            highest_bid=Decimal("190.00"),
        )

        result = price.get_market_price("highest_bid")
        assert result == Decimal("190.00")

    def test_get_market_price_average(self):
        """Test get_market_price for average price"""
        price = MarketPrice(
            id=uuid4(),
            product_id=uuid4(),
            platform_name="Klekt",
            condition="new",
            price_date=date.today(),
            average_price=Decimal("275.50"),
        )

        result = price.get_market_price("average")
        assert result == Decimal("275.50")

    def test_get_market_price_unknown_type(self):
        """Test get_market_price for unknown price type"""
        price = MarketPrice(
            id=uuid4(),
            product_id=uuid4(),
            platform_name="StockX",
            condition="new",
            price_date=date.today(),
            last_sale=Decimal("250.00"),
        )

        result = price.get_market_price("unknown_type")
        assert result is None

    def test_get_market_price_none_value(self):
        """Test get_market_price when value is None"""
        price = MarketPrice(
            id=uuid4(),
            product_id=uuid4(),
            platform_name="StockX",
            condition="new",
            price_date=date.today(),
            last_sale=None,
        )

        result = price.get_market_price("last_sale")
        assert result is None


class TestSalesForecast:
    """Test SalesForecast model business logic"""

    def test_confidence_interval_property(self):
        """Test confidence_interval property"""
        forecast = SalesForecast(
            id=uuid4(),
            forecast_run_id=uuid4(),
            forecast_level="product",
            forecast_date=date.today(),
            forecast_horizon="weekly",
            forecasted_units=Decimal("25.5"),
            forecasted_revenue=Decimal("1200.00"),
            confidence_lower=Decimal("20.0"),
            confidence_upper=Decimal("30.0"),
            model_name="ARIMA",
            model_version="1.0",
        )

        interval = forecast.confidence_interval
        assert interval == (Decimal("20.0"), Decimal("30.0"))

    def test_confidence_interval_none_values(self):
        """Test confidence_interval with None values"""
        forecast = SalesForecast(
            id=uuid4(),
            forecast_run_id=uuid4(),
            forecast_level="brand",
            forecast_date=date.today(),
            forecast_horizon="monthly",
            forecasted_units=Decimal("100.0"),
            forecasted_revenue=Decimal("5000.00"),
            model_name="LinearRegression",
            model_version="2.1",
        )

        interval = forecast.confidence_interval
        assert interval == (None, None)

    def test_accuracy_score_valid_actual(self):
        """Test accuracy_score with valid actual value"""
        forecast = SalesForecast(
            id=uuid4(),
            forecast_run_id=uuid4(),
            forecast_level="category",
            forecast_date=date.today(),
            forecast_horizon="daily",
            forecasted_units=Decimal("50.0"),
            forecasted_revenue=Decimal("2500.00"),
            model_name="RandomForest",
            model_version="3.0",
        )

        actual_value = Decimal("45.0")
        result = forecast.accuracy_score(actual_value)

        assert result["absolute_error"] == 5.0
        assert abs(result["percentage_error"] - 11.11) < 0.01
        assert result["forecast_value"] == 50.0
        assert result["actual_value"] == 45.0

    def test_accuracy_score_zero_actual(self):
        """Test accuracy_score with zero actual value"""
        forecast = SalesForecast(
            id=uuid4(),
            forecast_run_id=uuid4(),
            forecast_level="product",
            forecast_date=date.today(),
            forecast_horizon="weekly",
            forecasted_units=Decimal("10.0"),
            forecasted_revenue=Decimal("500.00"),
            model_name="LSTM",
            model_version="1.5",
        )

        actual_value = Decimal("0")
        result = forecast.accuracy_score(actual_value)

        # Zero actual value returns empty dict (line 262-263 in model)
        assert result == {}

    def test_accuracy_score_none_actual(self):
        """Test accuracy_score with None actual value"""
        forecast = SalesForecast(
            id=uuid4(),
            forecast_run_id=uuid4(),
            forecast_level="platform",
            forecast_date=date.today(),
            forecast_horizon="monthly",
            forecasted_units=Decimal("75.0"),
            forecasted_revenue=Decimal("3750.00"),
            model_name="XGBoost",
            model_version="4.2",
        )

        result = forecast.accuracy_score(None)
        assert result == {}

    def test_accuracy_score_perfect_forecast(self):
        """Test accuracy_score with perfect forecast"""
        forecast = SalesForecast(
            id=uuid4(),
            forecast_run_id=uuid4(),
            forecast_level="product",
            forecast_date=date.today(),
            forecast_horizon="daily",
            forecasted_units=Decimal("100.0"),
            forecasted_revenue=Decimal("5000.00"),
            model_name="Perfect",
            model_version="1.0",
        )

        actual_value = Decimal("100.0")
        result = forecast.accuracy_score(actual_value)

        assert result["absolute_error"] == 0.0
        assert result["percentage_error"] == 0.0
        assert result["forecast_value"] == 100.0
        assert result["actual_value"] == 100.0


class TestForecastAccuracy:
    """Test ForecastAccuracy model business logic"""

    def test_get_accuracy_summary_complete_data(self):
        """Test get_accuracy_summary with complete data"""
        accuracy = ForecastAccuracy(
            id=uuid4(),
            forecast_run_id=uuid4(),
            model_name="ARIMA",
            forecast_level="product",
            forecast_horizon="weekly",
            accuracy_date=date.today(),
            mape_score=Decimal("15.25"),
            rmse_score=Decimal("8.75"),
            mae_score=Decimal("6.50"),
            r2_score=Decimal("0.8245"),
            bias_score=Decimal("2.15"),
            records_evaluated=150,
            evaluation_period_days=30,
        )

        summary = accuracy.get_accuracy_summary()

        assert summary["model"] == "ARIMA"
        assert summary["level"] == "product"
        assert summary["horizon"] == "weekly"
        assert summary["mape"] == 15.25
        assert summary["rmse"] == 8.75
        assert summary["r2"] == 0.8245
        assert summary["records"] == 150
        assert summary["period_days"] == 30

    def test_get_accuracy_summary_partial_data(self):
        """Test get_accuracy_summary with partial data"""
        accuracy = ForecastAccuracy(
            id=uuid4(),
            forecast_run_id=uuid4(),
            model_name="LinearRegression",
            forecast_level="brand",
            forecast_horizon="monthly",
            accuracy_date=date.today(),
            mape_score=None,
            rmse_score=Decimal("12.34"),
            r2_score=None,
            records_evaluated=75,
            evaluation_period_days=60,
        )

        summary = accuracy.get_accuracy_summary()

        assert summary["model"] == "LinearRegression"
        assert summary["mape"] is None
        assert summary["rmse"] == 12.34
        assert summary["r2"] is None
        assert summary["records"] == 75


class TestPricingKPI:
    """Test PricingKPI model business logic"""

    def test_get_performance_summary_complete_data(self):
        """Test get_performance_summary with complete data"""
        kpi_date = date(2024, 6, 15)
        kpi = PricingKPI(
            id=uuid4(),
            kpi_date=kpi_date,
            aggregation_level="product",
            average_margin_percent=Decimal("25.50"),
            average_markup_percent=Decimal("35.75"),
            conversion_rate_percent=Decimal("12.25"),
            revenue_impact_eur=Decimal("15750.00"),
            units_sold=125,
            average_selling_price=Decimal("126.00"),
        )

        summary = kpi.get_performance_summary()

        assert summary["date"] == "2024-06-15"
        assert summary["level"] == "product"
        assert summary["margin"] == 25.50
        assert summary["markup"] == 35.75
        assert summary["conversion"] == 12.25
        assert summary["revenue"] == 15750.00
        assert summary["units"] == 125
        assert summary["avg_price"] == 126.00

    def test_get_performance_summary_partial_data(self):
        """Test get_performance_summary with partial data"""
        kpi_date = date(2024, 7, 20)
        kpi = PricingKPI(
            id=uuid4(),
            kpi_date=kpi_date,
            aggregation_level="brand",
            average_margin_percent=None,
            conversion_rate_percent=Decimal("8.75"),
            revenue_impact_eur=None,
            units_sold=None,
            average_selling_price=Decimal("95.50"),
        )

        summary = kpi.get_performance_summary()

        assert summary["date"] == "2024-07-20"
        assert summary["level"] == "brand"
        assert summary["margin"] is None
        assert summary["markup"] is None
        assert summary["conversion"] == 8.75
        assert summary["revenue"] is None
        assert summary["units"] is None
        assert summary["avg_price"] == 95.50

    def test_get_performance_summary_zero_values(self):
        """Test get_performance_summary with zero values"""
        kpi_date = date(2024, 8, 1)
        kpi = PricingKPI(
            id=uuid4(),
            kpi_date=kpi_date,
            aggregation_level="category",
            average_margin_percent=Decimal("0.00"),
            average_markup_percent=None,
            conversion_rate_percent=None,
            revenue_impact_eur=Decimal("0.00"),
            units_sold=0,
            average_selling_price=None,
        )

        summary = kpi.get_performance_summary()

        assert summary["date"] == "2024-08-01"
        assert summary["margin"] is None  # Decimal(0) becomes None in summary
        assert summary["revenue"] is None  # None values stay None in summary
        assert summary["units"] == 0

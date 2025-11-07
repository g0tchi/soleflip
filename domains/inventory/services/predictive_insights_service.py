"""
Predictive Inventory Insights Service

Integrates with the existing forecast engine to provide actionable inventory insights:
- Demand prediction for inventory planning
- Restock recommendations based on forecasts
- Seasonal pattern analysis for optimal timing
- ROI projections for inventory investments
- Market trend integration with StockX data
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from domains.analytics.services.forecast_engine import (
    ForecastConfig,
    ForecastEngine,
    ForecastHorizon,
    ForecastLevel,
    ForecastModel,
)
from domains.integration.services.stockx_service import StockXService
from domains.pricing.services.smart_pricing_service import SmartPricingService
from shared.database.models import InventoryItem


class InsightType(Enum):
    """Types of predictive insights"""

    RESTOCK_OPPORTUNITY = "restock_opportunity"
    DEMAND_SURGE = "demand_surge"
    SEASONAL_TREND = "seasonal_trend"
    MARKET_SHIFT = "market_shift"
    PROFIT_OPTIMIZATION = "profit_optimization"
    CLEARANCE_ALERT = "clearance_alert"


class InsightPriority(Enum):
    """Priority levels for insights"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ActionType(Enum):
    """Recommended action types"""

    RESTOCK = "restock"
    INCREASE_PRICE = "increase_price"
    DECREASE_PRICE = "decrease_price"
    HOLD_INVENTORY = "hold_inventory"
    LIQUIDATE = "liquidate"
    MONITOR = "monitor"


@dataclass
class PredictiveInsight:
    """Individual predictive insight"""

    insight_id: str
    insight_type: InsightType
    priority: InsightPriority
    title: str
    description: str
    product_id: Optional[uuid.UUID] = None
    product_name: Optional[str] = None
    current_inventory: Optional[int] = None
    predicted_demand: Optional[float] = None
    confidence_score: float = 0.0
    potential_revenue: Optional[Decimal] = None
    potential_profit: Optional[Decimal] = None
    recommended_actions: List[Dict[str, Any]] = None
    supporting_data: Dict[str, Any] = None
    expires_at: Optional[datetime] = None


@dataclass
class InventoryForecast:
    """Inventory-specific forecast result"""

    product_id: uuid.UUID
    product_name: str
    current_stock: int
    predicted_demand_30d: float
    predicted_demand_90d: float
    restock_recommendation: str
    optimal_restock_quantity: int
    days_until_stockout: Optional[int]
    confidence_level: float
    seasonal_factors: Dict[str, float]
    market_trends: Dict[str, Any]


@dataclass
class RestockRecommendation:
    """Detailed restock recommendation"""

    product_id: uuid.UUID
    product_name: str
    current_stock: int
    recommended_quantity: int
    investment_required: Decimal
    projected_revenue: Decimal
    projected_profit: Decimal
    roi_estimate: float
    optimal_timing: date
    risk_level: str
    supporting_insights: List[str]


class PredictiveInsightsService:
    """
    Advanced inventory insights service using forecasting and market intelligence

    Key Features:
    - Demand prediction integration with forecast engine
    - StockX market data correlation
    - Seasonal pattern recognition
    - ROI-optimized restock recommendations
    - Automated insight generation with priority scoring
    - Action-oriented recommendations
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.logger = logging.getLogger(__name__)

        # Initialize service dependencies
        self.forecast_engine = ForecastEngine(db_session)
        self.stockx_service = StockXService()
        self.pricing_service = SmartPricingService(db_session)

    # =====================================================
    # MAIN INSIGHT GENERATION METHODS
    # =====================================================

    async def generate_inventory_insights(
        self,
        products: Optional[List[InventoryItem]] = None,
        insight_types: Optional[List[InsightType]] = None,
        days_ahead: int = 30,
    ) -> List[PredictiveInsight]:
        """Generate comprehensive predictive insights for inventory"""
        self.logger.info("Generating predictive inventory insights")

        insights = []

        # Get products to analyze
        if not products:
            products = await self._get_active_inventory_products()

        # Generate different types of insights
        if not insight_types:
            insight_types = list(InsightType)

        for insight_type in insight_types:
            try:
                type_insights = await self._generate_insights_by_type(
                    insight_type, products, days_ahead
                )
                insights.extend(type_insights)
            except Exception as e:
                self.logger.error(f"Failed to generate {insight_type.value} insights: {str(e)}")
                continue

        # Sort by priority and confidence
        insights.sort(key=lambda x: (x.priority.value, -x.confidence_score))

        self.logger.info(f"Generated {len(insights)} predictive insights")
        return insights

    async def get_inventory_forecasts(
        self, product_ids: Optional[List[uuid.UUID]] = None, horizon_days: int = 90
    ) -> List[InventoryForecast]:
        """Get detailed inventory forecasts with market intelligence"""
        self.logger.info("Generating inventory forecasts")

        forecasts = []

        # Get product data
        products = await self._get_inventory_products(product_ids)

        for product in products:
            try:
                forecast = await self._generate_product_forecast(product, horizon_days)
                if forecast:
                    forecasts.append(forecast)
            except Exception as e:
                self.logger.error(f"Failed to forecast product {product.id}: {str(e)}")
                continue

        return forecasts

    async def generate_restock_recommendations(
        self,
        investment_budget: Optional[Decimal] = None,
        min_roi: float = 0.15,
        max_products: int = 20,
    ) -> List[RestockRecommendation]:
        """Generate ROI-optimized restock recommendations"""
        self.logger.info("Generating restock recommendations")

        # Get inventory forecasts
        forecasts = await self.get_inventory_forecasts()

        recommendations = []
        total_investment = Decimal("0")

        # Filter and score restock opportunities
        opportunities = []
        for forecast in forecasts:
            if forecast.days_until_stockout and forecast.days_until_stockout <= 60:
                opportunity_score = await self._calculate_restock_opportunity_score(forecast)
                opportunities.append((forecast, opportunity_score))

        # Sort by opportunity score
        opportunities.sort(key=lambda x: x[1], reverse=True)

        # Generate recommendations within budget
        for forecast, score in opportunities[:max_products]:
            try:
                recommendation = await self._create_restock_recommendation(forecast, min_roi)

                if recommendation and recommendation.roi_estimate >= min_roi:
                    if investment_budget:
                        if (
                            total_investment + recommendation.investment_required
                            <= investment_budget
                        ):
                            recommendations.append(recommendation)
                            total_investment += recommendation.investment_required
                        else:
                            continue
                    else:
                        recommendations.append(recommendation)

            except Exception as e:
                self.logger.error(f"Failed to create restock recommendation: {str(e)}")
                continue

        return recommendations

    # =====================================================
    # INSIGHT TYPE GENERATORS
    # =====================================================

    async def _generate_insights_by_type(
        self, insight_type: InsightType, products: List[InventoryItem], days_ahead: int
    ) -> List[PredictiveInsight]:
        """Generate insights for specific type"""

        generators = {
            InsightType.RESTOCK_OPPORTUNITY: self._generate_restock_insights,
            InsightType.DEMAND_SURGE: self._generate_demand_surge_insights,
            InsightType.SEASONAL_TREND: self._generate_seasonal_insights,
            InsightType.MARKET_SHIFT: self._generate_market_shift_insights,
            InsightType.PROFIT_OPTIMIZATION: self._generate_profit_insights,
            InsightType.CLEARANCE_ALERT: self._generate_clearance_insights,
        }

        generator = generators.get(insight_type)
        if not generator:
            return []

        return await generator(products, days_ahead)

    async def _generate_restock_insights(
        self, products: List[InventoryItem], days_ahead: int
    ) -> List[PredictiveInsight]:
        """Generate restock opportunity insights"""
        insights = []

        for product in products:
            try:
                # Get demand forecast
                forecast = await self._get_product_demand_forecast(product, days_ahead)

                if not forecast:
                    continue

                # Calculate restock opportunity
                predicted_demand = sum(
                    p["forecasted_units"] for p in forecast.predictions[:days_ahead]
                )
                current_stock = getattr(product, "current_stock", 0)

                if predicted_demand > current_stock * 1.5:  # Demand exceeds 1.5x current stock
                    # Get market data for validation
                    market_data = await self._get_stockx_market_data(product.sku)

                    confidence = 0.7
                    if market_data and market_data.get("recent_sales_increase", False):
                        confidence = 0.85

                    # Calculate potential revenue
                    estimated_price = Decimal(str(market_data.get("current_market_price", 100)))
                    potential_revenue = estimated_price * Decimal(str(predicted_demand))

                    insight = PredictiveInsight(
                        insight_id=f"restock_{product.id}_{int(datetime.now().timestamp())}",
                        insight_type=InsightType.RESTOCK_OPPORTUNITY,
                        priority=self._calculate_priority(
                            predicted_demand - current_stock, confidence
                        ),
                        title=f"Restock Opportunity: {product.brand} {product.model}",
                        description=f"Predicted demand of {int(predicted_demand)} units in next {days_ahead} days exceeds current stock of {current_stock} units",
                        product_id=product.id,
                        product_name=f"{product.brand} {product.model}",
                        current_inventory=current_stock,
                        predicted_demand=predicted_demand,
                        confidence_score=confidence,
                        potential_revenue=potential_revenue,
                        recommended_actions=[
                            {
                                "action": ActionType.RESTOCK.value,
                                "quantity": int(predicted_demand - current_stock + 10),  # Buffer
                                "priority": "high",
                                "timing": "within_7_days",
                            }
                        ],
                        supporting_data={
                            "forecast_model": forecast.model_name,
                            "market_trend": (
                                market_data.get("trend", "stable") if market_data else "unknown"
                            ),
                            "days_until_stockout": max(
                                1, int(current_stock / (predicted_demand / days_ahead))
                            ),
                        },
                        expires_at=datetime.now() + timedelta(days=7),
                    )

                    insights.append(insight)

            except Exception as e:
                self.logger.error(
                    f"Failed to generate restock insight for product {product.id}: {str(e)}"
                )
                continue

        return insights

    async def _generate_demand_surge_insights(
        self, products: List[InventoryItem], days_ahead: int
    ) -> List[PredictiveInsight]:
        """Generate demand surge prediction insights"""
        insights = []

        for product in products:
            try:
                # Get historical and forecast data
                forecast = await self._get_product_demand_forecast(product, days_ahead)
                if not forecast:
                    continue

                # Calculate trend
                recent_predictions = [
                    p["forecasted_units"] for p in forecast.predictions[:14]
                ]  # Next 2 weeks
                avg_recent = sum(recent_predictions) / len(recent_predictions)

                # Get historical average (mock calculation)
                historical_avg = getattr(product, "avg_daily_sales", 2.0)  # Placeholder

                surge_factor = avg_recent / max(historical_avg, 0.1)

                if surge_factor > 1.5:  # 50% increase
                    market_data = await self._get_stockx_market_data(product.sku)

                    insight = PredictiveInsight(
                        insight_id=f"surge_{product.id}_{int(datetime.now().timestamp())}",
                        insight_type=InsightType.DEMAND_SURGE,
                        priority=(
                            InsightPriority.HIGH if surge_factor > 2.0 else InsightPriority.MEDIUM
                        ),
                        title=f"Demand Surge Predicted: {product.brand} {product.model}",
                        description=f"Predicted {int((surge_factor - 1) * 100)}% increase in demand over next {days_ahead} days",
                        product_id=product.id,
                        product_name=f"{product.brand} {product.model}",
                        predicted_demand=avg_recent * days_ahead,
                        confidence_score=0.75,
                        recommended_actions=[
                            {
                                "action": ActionType.RESTOCK.value,
                                "urgency": "immediate",
                                "reason": "surge_preparation",
                            },
                            {
                                "action": ActionType.INCREASE_PRICE.value,
                                "percentage": min(15, int((surge_factor - 1) * 10)),
                                "timing": "before_surge",
                            },
                        ],
                        supporting_data={
                            "surge_factor": surge_factor,
                            "market_conditions": (
                                market_data.get("market_conditions", "unknown")
                                if market_data
                                else "unknown"
                            ),
                            "predicted_peak_demand": max(recent_predictions),
                        },
                        expires_at=datetime.now() + timedelta(days=3),
                    )

                    insights.append(insight)

            except Exception as e:
                self.logger.error(
                    f"Failed to generate surge insight for product {product.id}: {str(e)}"
                )
                continue

        return insights

    async def _generate_seasonal_insights(
        self, products: List[InventoryItem], days_ahead: int
    ) -> List[PredictiveInsight]:
        """Generate seasonal trend insights"""
        insights = []

        current_month = datetime.now().month
        seasonal_patterns = {
            "back_to_school": [8, 9],  # August, September
            "holiday_season": [11, 12],  # November, December
            "spring_summer": [3, 4, 5, 6],  # March to June
            "fall_winter": [9, 10, 11, 12],  # September to December
        }

        for product in products:
            try:
                # Determine if we're in a seasonal period
                active_seasons = []
                for season, months in seasonal_patterns.items():
                    if current_month in months or (current_month + 1) % 12 in months:
                        active_seasons.append(season)

                if not active_seasons:
                    continue

                # Get category-specific seasonal multipliers
                category = getattr(product, "category", "").lower()
                seasonal_multiplier = 1.0

                if "jordan" in category or "basketball" in category:
                    if "back_to_school" in active_seasons:
                        seasonal_multiplier = 1.4
                elif "boot" in category or "winter" in category:
                    if "fall_winter" in active_seasons:
                        seasonal_multiplier = 1.6
                elif "sandal" in category or "summer" in category:
                    if "spring_summer" in active_seasons:
                        seasonal_multiplier = 1.3

                if seasonal_multiplier > 1.1:
                    forecast = await self._get_product_demand_forecast(product, days_ahead)
                    base_demand = (
                        sum(p["forecasted_units"] for p in forecast.predictions) if forecast else 30
                    )
                    seasonal_demand = base_demand * seasonal_multiplier

                    insight = PredictiveInsight(
                        insight_id=f"seasonal_{product.id}_{int(datetime.now().timestamp())}",
                        insight_type=InsightType.SEASONAL_TREND,
                        priority=InsightPriority.MEDIUM,
                        title=f"Seasonal Trend: {', '.join(active_seasons).replace('_', ' ').title()}",
                        description=f"Seasonal pattern indicates {int((seasonal_multiplier - 1) * 100)}% increase in demand for {product.brand} {product.model}",
                        product_id=product.id,
                        product_name=f"{product.brand} {product.model}",
                        predicted_demand=seasonal_demand,
                        confidence_score=0.65,
                        recommended_actions=[
                            {
                                "action": ActionType.RESTOCK.value,
                                "seasonal_factor": seasonal_multiplier,
                                "timing": "before_peak_season",
                            }
                        ],
                        supporting_data={
                            "active_seasons": active_seasons,
                            "seasonal_multiplier": seasonal_multiplier,
                            "product_category": category,
                            "peak_months": [
                                m for season in active_seasons for m in seasonal_patterns[season]
                            ],
                        },
                        expires_at=datetime.now() + timedelta(days=30),
                    )

                    insights.append(insight)

            except Exception as e:
                self.logger.error(
                    f"Failed to generate seasonal insight for product {product.id}: {str(e)}"
                )
                continue

        return insights

    async def _generate_market_shift_insights(
        self, products: List[InventoryItem], days_ahead: int
    ) -> List[PredictiveInsight]:
        """Generate market shift insights based on StockX data"""
        insights = []

        for product in products:
            try:
                market_data = await self._get_stockx_market_data(product.sku)
                if not market_data:
                    continue

                # Analyze market shifts
                price_trend = market_data.get("price_trend", "stable")
                volume_trend = market_data.get("volume_trend", "stable")
                volatility = market_data.get("volatility", "low")

                shift_detected = False
                shift_description = ""
                recommended_actions = []
                priority = InsightPriority.LOW

                if price_trend == "bullish" and volume_trend == "increasing":
                    shift_detected = True
                    shift_description = "Strong bullish market with increasing volume"
                    recommended_actions = [
                        {"action": ActionType.HOLD_INVENTORY.value, "reason": "price_appreciation"},
                        {"action": ActionType.INCREASE_PRICE.value, "percentage": 10},
                    ]
                    priority = InsightPriority.HIGH

                elif price_trend == "bearish" and volume_trend == "decreasing":
                    shift_detected = True
                    shift_description = "Bearish market with declining volume"
                    recommended_actions = [
                        {"action": ActionType.DECREASE_PRICE.value, "percentage": 8},
                        {"action": ActionType.LIQUIDATE.value, "urgency": "consider"},
                    ]
                    priority = InsightPriority.MEDIUM

                elif volatility == "high":
                    shift_detected = True
                    shift_description = "High market volatility detected"
                    recommended_actions = [
                        {"action": ActionType.MONITOR.value, "frequency": "daily"},
                        {"action": ActionType.HOLD_INVENTORY.value, "reason": "volatility_risk"},
                    ]
                    priority = InsightPriority.MEDIUM

                if shift_detected:
                    insight = PredictiveInsight(
                        insight_id=f"market_{product.id}_{int(datetime.now().timestamp())}",
                        insight_type=InsightType.MARKET_SHIFT,
                        priority=priority,
                        title=f"Market Shift: {product.brand} {product.model}",
                        description=shift_description,
                        product_id=product.id,
                        product_name=f"{product.brand} {product.model}",
                        confidence_score=0.8,
                        recommended_actions=recommended_actions,
                        supporting_data={
                            "price_trend": price_trend,
                            "volume_trend": volume_trend,
                            "volatility": volatility,
                            "current_market_price": market_data.get("current_market_price"),
                            "52w_high": market_data.get("52w_high"),
                            "52w_low": market_data.get("52w_low"),
                        },
                        expires_at=datetime.now() + timedelta(days=5),
                    )

                    insights.append(insight)

            except Exception as e:
                self.logger.error(
                    f"Failed to generate market shift insight for product {product.id}: {str(e)}"
                )
                continue

        return insights

    async def _generate_profit_insights(
        self, products: List[InventoryItem], days_ahead: int
    ) -> List[PredictiveInsight]:
        """Generate profit optimization insights"""
        insights = []

        for product in products:
            try:
                # Get pricing optimization data
                pricing_analysis = await self.pricing_service.analyze_product_pricing(product.sku)
                if not pricing_analysis:
                    continue

                current_price = getattr(product, "current_price", Decimal("100"))
                optimal_price = pricing_analysis.get("optimal_price", current_price)
                profit_increase = pricing_analysis.get("profit_increase_potential", 0)

                if profit_increase > 0.1:  # 10% profit increase potential
                    forecast = await self._get_product_demand_forecast(product, days_ahead)
                    predicted_sales = (
                        sum(p["forecasted_units"] for p in forecast.predictions) if forecast else 20
                    )

                    potential_profit = (
                        Decimal(str(profit_increase))
                        * current_price
                        * Decimal(str(predicted_sales))
                    )

                    insight = PredictiveInsight(
                        insight_id=f"profit_{product.id}_{int(datetime.now().timestamp())}",
                        insight_type=InsightType.PROFIT_OPTIMIZATION,
                        priority=(
                            InsightPriority.HIGH
                            if profit_increase > 0.2
                            else InsightPriority.MEDIUM
                        ),
                        title=f"Profit Optimization: {product.brand} {product.model}",
                        description=f"Price optimization could increase profit by {int(profit_increase * 100)}% over next {days_ahead} days",
                        product_id=product.id,
                        product_name=f"{product.brand} {product.model}",
                        potential_profit=potential_profit,
                        confidence_score=pricing_analysis.get("confidence", 0.7),
                        recommended_actions=[
                            {
                                "action": ActionType.INCREASE_PRICE.value,
                                "from_price": float(current_price),
                                "to_price": float(optimal_price),
                                "expected_profit_increase": profit_increase,
                            }
                        ],
                        supporting_data={
                            "current_price": float(current_price),
                            "optimal_price": float(optimal_price),
                            "profit_increase": profit_increase,
                            "predicted_sales": predicted_sales,
                            "pricing_strategy": pricing_analysis.get(
                                "recommended_strategy", "dynamic"
                            ),
                        },
                        expires_at=datetime.now() + timedelta(days=14),
                    )

                    insights.append(insight)

            except Exception as e:
                self.logger.error(
                    f"Failed to generate profit insight for product {product.id}: {str(e)}"
                )
                continue

        return insights

    async def _generate_clearance_insights(
        self, products: List[InventoryItem], days_ahead: int
    ) -> List[PredictiveInsight]:
        """Generate clearance alert insights"""
        insights = []

        for product in products:
            try:
                # Get demand forecast
                forecast = await self._get_product_demand_forecast(product, 60)  # 60 days lookout
                if not forecast:
                    continue

                predicted_demand = sum(p["forecasted_units"] for p in forecast.predictions[:60])
                current_stock = getattr(product, "current_stock", 0)

                # Calculate inventory turnover
                if predicted_demand > 0:
                    days_to_clear = (current_stock / predicted_demand) * 60
                else:
                    days_to_clear = 999  # Essentially infinite

                # Alert for slow-moving inventory
                if days_to_clear > 120:  # More than 4 months to clear
                    market_data = await self._get_stockx_market_data(product.sku)
                    getattr(product, "current_price", Decimal("100"))

                    # Calculate clearance scenarios
                    discount_scenarios = [
                        {"discount": 0.15, "expected_velocity": 2.0},
                        {"discount": 0.25, "expected_velocity": 3.5},
                        {"discount": 0.40, "expected_velocity": 5.0},
                    ]

                    best_scenario = discount_scenarios[1]  # 25% discount as default

                    insight = PredictiveInsight(
                        insight_id=f"clearance_{product.id}_{int(datetime.now().timestamp())}",
                        insight_type=InsightType.CLEARANCE_ALERT,
                        priority=(
                            InsightPriority.MEDIUM if days_to_clear > 180 else InsightPriority.LOW
                        ),
                        title=f"Clearance Alert: {product.brand} {product.model}",
                        description=f"Slow-moving inventory: {int(days_to_clear)} days to clear at current demand rate",
                        product_id=product.id,
                        product_name=f"{product.brand} {product.model}",
                        current_inventory=current_stock,
                        predicted_demand=predicted_demand,
                        confidence_score=0.75,
                        recommended_actions=[
                            {
                                "action": ActionType.DECREASE_PRICE.value,
                                "discount_percentage": best_scenario["discount"],
                                "expected_velocity_increase": best_scenario["expected_velocity"],
                                "timing": "within_30_days",
                            },
                            {
                                "action": ActionType.MONITOR.value,
                                "metric": "sales_velocity",
                                "frequency": "weekly",
                            },
                        ],
                        supporting_data={
                            "days_to_clear": days_to_clear,
                            "current_velocity": predicted_demand / 60,  # per day
                            "discount_scenarios": discount_scenarios,
                            "market_trend": (
                                market_data.get("trend", "stable") if market_data else "unknown"
                            ),
                        },
                        expires_at=datetime.now() + timedelta(days=21),
                    )

                    insights.append(insight)

            except Exception as e:
                self.logger.error(
                    f"Failed to generate clearance insight for product {product.id}: {str(e)}"
                )
                continue

        return insights

    # =====================================================
    # FORECAST AND RECOMMENDATION HELPERS
    # =====================================================

    async def _generate_product_forecast(
        self, product: InventoryItem, horizon_days: int
    ) -> Optional[InventoryForecast]:
        """Generate detailed forecast for a product"""
        try:
            # Get demand forecast
            forecast_result = await self._get_product_demand_forecast(product, horizon_days)
            if not forecast_result:
                return None

            # Calculate predictions
            predictions_30d = sum(p["forecasted_units"] for p in forecast_result.predictions[:30])
            predictions_90d = sum(p["forecasted_units"] for p in forecast_result.predictions[:90])

            current_stock = getattr(product, "current_stock", 0)

            # Calculate days until stockout
            daily_demand = predictions_30d / 30 if predictions_30d > 0 else 0
            days_until_stockout = int(current_stock / daily_demand) if daily_demand > 0 else None

            # Get market data
            market_data = await self._get_stockx_market_data(product.sku)

            # Determine restock recommendation
            if days_until_stockout and days_until_stockout < 30:
                restock_recommendation = "URGENT"
            elif days_until_stockout and days_until_stockout < 60:
                restock_recommendation = "RECOMMENDED"
            else:
                restock_recommendation = "MONITOR"

            # Calculate optimal restock quantity
            optimal_quantity = max(int(predictions_30d * 1.5), 10)  # 45 days worth + buffer

            return InventoryForecast(
                product_id=product.id,
                product_name=f"{product.brand} {product.model}",
                current_stock=current_stock,
                predicted_demand_30d=predictions_30d,
                predicted_demand_90d=predictions_90d,
                restock_recommendation=restock_recommendation,
                optimal_restock_quantity=optimal_quantity,
                days_until_stockout=days_until_stockout,
                confidence_level=(
                    forecast_result.model_metrics.get("r2_score", 0.7)
                    if forecast_result.model_metrics
                    else 0.7
                ),
                seasonal_factors={
                    "current_month_factor": 1.0,  # Would be calculated from historical data
                    "next_month_factor": 1.1,
                    "quarter_trend": "stable",
                },
                market_trends=market_data or {"status": "no_data"},
            )

        except Exception as e:
            self.logger.error(f"Failed to generate forecast for product {product.id}: {str(e)}")
            return None

    async def _create_restock_recommendation(
        self, forecast: InventoryForecast, min_roi: float
    ) -> Optional[RestockRecommendation]:
        """Create detailed restock recommendation"""
        try:
            # Estimate costs and revenue
            estimated_cost_per_unit = Decimal("80")  # Would be retrieved from product data
            estimated_selling_price = Decimal("120")  # Would be from pricing service

            recommended_quantity = forecast.optimal_restock_quantity
            investment_required = estimated_cost_per_unit * recommended_quantity
            projected_revenue = estimated_selling_price * Decimal(
                str(forecast.predicted_demand_30d)
            )
            projected_profit = projected_revenue - (
                estimated_cost_per_unit * Decimal(str(forecast.predicted_demand_30d))
            )

            # Calculate ROI
            roi_estimate = (
                float(projected_profit / investment_required) if investment_required > 0 else 0
            )

            if roi_estimate < min_roi:
                return None

            # Determine optimal timing
            if forecast.days_until_stockout and forecast.days_until_stockout <= 14:
                optimal_timing = date.today() + timedelta(days=1)  # Urgent
            elif forecast.days_until_stockout and forecast.days_until_stockout <= 30:
                optimal_timing = date.today() + timedelta(days=7)  # Soon
            else:
                optimal_timing = date.today() + timedelta(days=14)  # Planned

            # Risk assessment
            risk_level = "LOW"
            if forecast.confidence_level < 0.6:
                risk_level = "HIGH"
            elif forecast.confidence_level < 0.75:
                risk_level = "MEDIUM"

            return RestockRecommendation(
                product_id=forecast.product_id,
                product_name=forecast.product_name,
                current_stock=forecast.current_stock,
                recommended_quantity=recommended_quantity,
                investment_required=investment_required,
                projected_revenue=projected_revenue,
                projected_profit=projected_profit,
                roi_estimate=roi_estimate,
                optimal_timing=optimal_timing,
                risk_level=risk_level,
                supporting_insights=[
                    f"Predicted demand: {forecast.predicted_demand_30d:.1f} units/month",
                    f"Days until stockout: {forecast.days_until_stockout}",
                    f"Forecast confidence: {forecast.confidence_level:.1%}",
                    f"Market trend: {forecast.market_trends.get('trend', 'stable')}",
                ],
            )

        except Exception as e:
            self.logger.error(f"Failed to create restock recommendation: {str(e)}")
            return None

    # =====================================================
    # UTILITY AND HELPER METHODS
    # =====================================================

    async def _get_product_demand_forecast(self, product: InventoryItem, days_ahead: int):
        """Get demand forecast for a specific product"""
        try:
            config = ForecastConfig(
                model=ForecastModel.ENSEMBLE,
                horizon=ForecastHorizon.DAILY,
                level=ForecastLevel.PRODUCT,
                prediction_days=days_ahead,
                confidence_level=0.95,
                min_history_days=30,
            )

            forecasts = await self.forecast_engine.generate_forecasts(
                config=config,
                entity_ids=[product.id],
            )

            return forecasts[0] if forecasts else None

        except Exception as e:
            self.logger.error(f"Failed to get forecast for product {product.id}: {str(e)}")
            return None

    async def _get_stockx_market_data(self, sku: str) -> Optional[Dict[str, Any]]:
        """Get StockX market data for product"""
        try:
            market_data = await self.stockx_service.get_market_data(sku)
            return market_data
        except Exception as e:
            self.logger.error(f"Failed to get StockX data for SKU {sku}: {str(e)}")
            return None

    async def _get_active_inventory_products(self) -> List[InventoryItem]:
        """Get active inventory products for analysis"""
        # Mock implementation - would query actual database
        mock_products = []

        for i in range(10):
            product = type(
                "InventoryItem",
                (),
                {
                    "id": uuid.uuid4(),
                    "sku": f"SKU{i:03d}",
                    "brand": "Nike" if i % 2 == 0 else "Adidas",
                    "model": f"Model-{i}",
                    "current_stock": 25 + (i * 3),
                    "category": "basketball" if i % 3 == 0 else "running",
                    "current_price": Decimal("120") + Decimal(str(i * 10)),
                    "avg_daily_sales": 2.5 + (i * 0.3),
                },
            )()
            mock_products.append(product)

        return mock_products

    async def _get_inventory_products(
        self, product_ids: Optional[List[uuid.UUID]] = None
    ) -> List[InventoryItem]:
        """Get specific inventory products"""
        all_products = await self._get_active_inventory_products()

        if product_ids:
            return [p for p in all_products if p.id in product_ids]

        return all_products

    def _calculate_priority(self, impact_score: float, confidence: float) -> InsightPriority:
        """Calculate insight priority based on impact and confidence"""
        combined_score = impact_score * confidence

        if combined_score > 50 and confidence > 0.8:
            return InsightPriority.CRITICAL
        elif combined_score > 30 and confidence > 0.7:
            return InsightPriority.HIGH
        elif combined_score > 15:
            return InsightPriority.MEDIUM
        else:
            return InsightPriority.LOW

    async def _calculate_restock_opportunity_score(self, forecast: InventoryForecast) -> float:
        """Calculate opportunity score for restock recommendations"""
        score = 0.0

        # Demand factor (higher demand = higher score)
        if forecast.predicted_demand_30d > 0:
            demand_factor = min(forecast.predicted_demand_30d / 30, 5.0)  # Cap at 5 units/day
            score += demand_factor * 20  # Max 100 points

        # Urgency factor (sooner stockout = higher score)
        if forecast.days_until_stockout:
            if forecast.days_until_stockout <= 14:
                score += 50  # Very urgent
            elif forecast.days_until_stockout <= 30:
                score += 30  # Urgent
            elif forecast.days_until_stockout <= 60:
                score += 15  # Moderate

        # Confidence factor
        score += forecast.confidence_level * 30  # Max 30 points

        # Market trend factor
        market_trend = forecast.market_trends.get("trend", "stable")
        if market_trend == "bullish":
            score += 20
        elif market_trend == "bearish":
            score -= 10

        return max(0.0, score)

"""
Demand Score Calculator - Calculates product demand scores for arbitrage opportunities

The demand score (0-100) indicates how likely a product is to sell quickly.
Higher scores mean faster turnover and lower risk for arbitrage.
"""

import logging
import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.analytics.repositories.forecast_repository import ForecastRepository
from domains.pricing.models import DemandPattern
from shared.database.models import Brand, InventoryItem, Order, Product

logger = logging.getLogger(__name__)


class DemandScoreCalculator:
    """
    Calculates demand scores for products to assess arbitrage viability.

    The demand score is calculated based on:
    1. Sales Frequency (40%): Orders per day over last 90 days
    2. Price Trend (25%): Increasing prices indicate higher demand
    3. Stock Turnover (20%): Average shelf_life_days
    4. Seasonal Adjustment (10%): Current month seasonality factor
    5. Brand Popularity (5%): Brand's overall sales velocity
    """

    # Weights for different factors
    WEIGHT_SALES_FREQUENCY = 0.40
    WEIGHT_PRICE_TREND = 0.25
    WEIGHT_STOCK_TURNOVER = 0.20
    WEIGHT_SEASONAL = 0.10
    WEIGHT_BRAND = 0.05

    # Scoring thresholds
    EXCELLENT_SALES_PER_DAY = 1.0  # 1+ sales/day = 100 score
    GOOD_SALES_PER_DAY = 0.5  # 0.5 sales/day = 75 score
    FAIR_SALES_PER_DAY = 0.2  # 0.2 sales/day = 50 score
    POOR_SALES_PER_DAY = 0.05  # 0.05 sales/day = 25 score

    FAST_TURNOVER_DAYS = 7  # Sells in < 7 days = excellent
    MEDIUM_TURNOVER_DAYS = 14  # Sells in 7-14 days = good
    SLOW_TURNOVER_DAYS = 30  # Sells in 14-30 days = fair
    VERY_SLOW_TURNOVER_DAYS = 60  # Sells in > 60 days = poor

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.forecast_repo = ForecastRepository(db_session)
        self.logger = logging.getLogger(__name__)

    async def calculate_product_demand_score(
        self, product_id: uuid.UUID, days_back: int = 90
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate demand score for a product.

        Args:
            product_id: Product UUID
            days_back: Number of days to analyze (default 90)

        Returns:
            Tuple of (demand_score: 0-100, breakdown: dict with component scores)
        """
        self.logger.info(f"Calculating demand score for product {product_id}")

        # Gather all metrics in parallel
        sales_freq_score, sales_freq_value = await self._calculate_sales_frequency_score(
            product_id, days_back
        )
        price_trend_score, trend_direction = await self._calculate_price_trend_score(
            product_id, days_back
        )
        turnover_score, avg_turnover = await self._calculate_stock_turnover_score(
            product_id, days_back
        )
        seasonal_score = await self._calculate_seasonal_score()
        brand_score = await self._calculate_brand_score(product_id)

        # Calculate weighted demand score
        demand_score = (
            sales_freq_score * self.WEIGHT_SALES_FREQUENCY
            + price_trend_score * self.WEIGHT_PRICE_TREND
            + turnover_score * self.WEIGHT_STOCK_TURNOVER
            + seasonal_score * self.WEIGHT_SEASONAL
            + brand_score * self.WEIGHT_BRAND
        )

        # Breakdown for transparency
        breakdown = {
            "sales_frequency_score": round(sales_freq_score, 2),
            "sales_per_day": round(sales_freq_value, 3),
            "price_trend_score": round(price_trend_score, 2),
            "trend_direction": trend_direction,
            "stock_turnover_score": round(turnover_score, 2),
            "avg_turnover_days": round(avg_turnover, 1) if avg_turnover else None,
            "seasonal_score": round(seasonal_score, 2),
            "brand_score": round(brand_score, 2),
            "final_demand_score": round(demand_score, 2),
        }

        self.logger.info(
            f"Product {product_id} demand score: {demand_score:.2f} "
            f"(sales_freq: {sales_freq_score:.1f}, trend: {price_trend_score:.1f}, "
            f"turnover: {turnover_score:.1f})"
        )

        return round(demand_score, 2), breakdown

    async def _calculate_sales_frequency_score(
        self, product_id: uuid.UUID, days_back: int
    ) -> Tuple[float, float]:
        """
        Calculate sales frequency score (0-100) based on orders per day.

        Returns:
            Tuple of (score, sales_per_day)
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)

        # Count completed orders for this product
        query = (
            select(func.count(Order.id))
            .select_from(Order)
            .join(InventoryItem, Order.inventory_item_id == InventoryItem.id)
            .where(
                and_(
                    InventoryItem.product_id == product_id,
                    Order.sold_at.between(start_date, end_date),
                    Order.status == "completed",
                )
            )
        )

        result = await self.db.execute(query)
        total_sales = result.scalar() or 0

        # Calculate sales per day
        sales_per_day = total_sales / days_back if days_back > 0 else 0

        # Score based on sales frequency
        if sales_per_day >= self.EXCELLENT_SALES_PER_DAY:
            score = 100.0
        elif sales_per_day >= self.GOOD_SALES_PER_DAY:
            # Linear interpolation between 75-100
            score = 75 + (25 * (sales_per_day - self.GOOD_SALES_PER_DAY) /
                         (self.EXCELLENT_SALES_PER_DAY - self.GOOD_SALES_PER_DAY))
        elif sales_per_day >= self.FAIR_SALES_PER_DAY:
            # Linear interpolation between 50-75
            score = 50 + (25 * (sales_per_day - self.FAIR_SALES_PER_DAY) /
                         (self.GOOD_SALES_PER_DAY - self.FAIR_SALES_PER_DAY))
        elif sales_per_day >= self.POOR_SALES_PER_DAY:
            # Linear interpolation between 25-50
            score = 25 + (25 * (sales_per_day - self.POOR_SALES_PER_DAY) /
                         (self.FAIR_SALES_PER_DAY - self.POOR_SALES_PER_DAY))
        else:
            # Below poor threshold
            score = max(0, (sales_per_day / self.POOR_SALES_PER_DAY) * 25)

        return min(100.0, score), sales_per_day

    async def _calculate_price_trend_score(
        self, product_id: uuid.UUID, days_back: int
    ) -> Tuple[float, str]:
        """
        Calculate price trend score based on recent price movements.
        Increasing prices indicate higher demand.

        Returns:
            Tuple of (score, trend_direction: 'increasing'|'decreasing'|'stable')
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)

        # Get average sale prices over time
        query = (
            select(
                func.date_trunc("week", Order.sold_at).label("week"),
                func.avg(Order.net_proceeds).label("avg_price"),
            )
            .select_from(Order)
            .join(InventoryItem, Order.inventory_item_id == InventoryItem.id)
            .where(
                and_(
                    InventoryItem.product_id == product_id,
                    Order.sold_at.between(start_date, end_date),
                    Order.status == "completed",
                )
            )
            .group_by(func.date_trunc("week", Order.sold_at))
            .order_by(func.date_trunc("week", Order.sold_at).asc())
        )

        result = await self.db.execute(query)
        price_data = result.all()

        if len(price_data) < 2:
            # Not enough data for trend analysis
            return 50.0, "stable"

        # Calculate linear trend using simple regression
        prices = [float(row.avg_price) for row in price_data]
        n = len(prices)

        # Calculate trend (slope of best fit line)
        x_vals = list(range(n))
        mean_x = sum(x_vals) / n
        mean_y = sum(prices) / n

        numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_vals, prices))
        denominator = sum((x - mean_x) ** 2 for x in x_vals)

        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator

        # Determine trend direction and score
        avg_price = mean_y
        slope_percentage = (slope / avg_price * 100) if avg_price > 0 else 0

        if slope_percentage > 2:  # Increasing > 2% per week
            trend_direction = "increasing"
            score = min(100, 75 + (slope_percentage * 5))  # Cap at 100
        elif slope_percentage < -2:  # Decreasing > 2% per week
            trend_direction = "decreasing"
            score = max(0, 50 + (slope_percentage * 5))  # Floor at 0
        else:  # Stable
            trend_direction = "stable"
            score = 60.0

        return score, trend_direction

    async def _calculate_stock_turnover_score(
        self, product_id: uuid.UUID, days_back: int
    ) -> Tuple[float, Optional[float]]:
        """
        Calculate stock turnover score based on average shelf_life_days.
        Faster turnover = higher score.

        Returns:
            Tuple of (score, avg_shelf_life_days)
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)

        # Get average shelf_life_days for sold items
        query = (
            select(func.avg(Order.shelf_life_days))
            .select_from(Order)
            .join(InventoryItem, Order.inventory_item_id == InventoryItem.id)
            .where(
                and_(
                    InventoryItem.product_id == product_id,
                    Order.sold_at.between(start_date, end_date),
                    Order.status == "completed",
                    Order.shelf_life_days.isnot(None),
                )
            )
        )

        result = await self.db.execute(query)
        avg_turnover = result.scalar()

        if avg_turnover is None:
            # No turnover data available
            return 50.0, None

        avg_turnover_float = float(avg_turnover)

        # Score based on turnover speed
        if avg_turnover_float <= self.FAST_TURNOVER_DAYS:
            score = 100.0
        elif avg_turnover_float <= self.MEDIUM_TURNOVER_DAYS:
            # Linear interpolation between 75-100
            score = 75 + (25 * (self.MEDIUM_TURNOVER_DAYS - avg_turnover_float) /
                         (self.MEDIUM_TURNOVER_DAYS - self.FAST_TURNOVER_DAYS))
        elif avg_turnover_float <= self.SLOW_TURNOVER_DAYS:
            # Linear interpolation between 50-75
            score = 50 + (25 * (self.SLOW_TURNOVER_DAYS - avg_turnover_float) /
                         (self.SLOW_TURNOVER_DAYS - self.MEDIUM_TURNOVER_DAYS))
        elif avg_turnover_float <= self.VERY_SLOW_TURNOVER_DAYS:
            # Linear interpolation between 25-50
            score = 25 + (25 * (self.VERY_SLOW_TURNOVER_DAYS - avg_turnover_float) /
                         (self.VERY_SLOW_TURNOVER_DAYS - self.SLOW_TURNOVER_DAYS))
        else:
            # Very slow turnover
            score = max(0, 25 * (90 - avg_turnover_float) / 60)

        return min(100.0, score), avg_turnover_float

    async def _calculate_seasonal_score(self) -> float:
        """
        Calculate seasonal score based on current month's seasonality factor.
        Uses sneaker industry seasonality patterns.

        Returns:
            Score (0-100) based on current month
        """
        current_month = date.today().month

        # Sneaker industry seasonality (from forecast_repository.py)
        seasonal_factors = {
            1: 0.85,  # January - Post-holiday low
            2: 0.9,  # February
            3: 1.05,  # March - Spring releases
            4: 1.1,  # April - Spring peak
            5: 1.0,  # May
            6: 0.95,  # June - Summer start
            7: 0.9,  # July - Summer low
            8: 1.0,  # August - Back to school prep
            9: 1.15,  # September - Back to school peak
            10: 1.1,  # October - Fall releases
            11: 1.2,  # November - Holiday shopping
            12: 1.25,  # December - Holiday peak
        }

        factor = seasonal_factors.get(current_month, 1.0)

        # Convert factor (0.85-1.25) to score (0-100)
        # 0.85 -> 40, 1.0 -> 60, 1.25 -> 100
        if factor >= 1.0:
            score = 60 + ((factor - 1.0) / 0.25) * 40
        else:
            score = 60 - ((1.0 - factor) / 0.15) * 20

        return min(100.0, max(0.0, score))

    async def _calculate_brand_score(self, product_id: uuid.UUID) -> float:
        """
        Calculate brand popularity score based on brand's overall sales velocity.

        Returns:
            Score (0-100)
        """
        # Get product's brand
        query = select(Product.brand_id).where(Product.id == product_id)
        result = await self.db.execute(query)
        brand_id = result.scalar()

        if not brand_id:
            return 50.0  # Neutral score if no brand

        # Get brand's sales in last 90 days
        end_date = date.today()
        start_date = end_date - timedelta(days=90)

        query = (
            select(func.count(Order.id))
            .select_from(Order)
            .join(InventoryItem, Order.inventory_item_id == InventoryItem.id)
            .join(Product, InventoryItem.product_id == Product.id)
            .where(
                and_(
                    Product.brand_id == brand_id,
                    Order.sold_at.between(start_date, end_date),
                    Order.status == "completed",
                )
            )
        )

        result = await self.db.execute(query)
        brand_sales = result.scalar() or 0

        # Score based on brand sales volume
        sales_per_day = brand_sales / 90

        if sales_per_day >= 10:  # Very popular brand
            score = 100.0
        elif sales_per_day >= 5:  # Popular brand
            score = 75 + (25 * (sales_per_day - 5) / 5)
        elif sales_per_day >= 2:  # Medium popularity
            score = 50 + (25 * (sales_per_day - 2) / 3)
        elif sales_per_day >= 0.5:  # Low popularity
            score = 25 + (25 * (sales_per_day - 0.5) / 1.5)
        else:  # Very low popularity
            score = max(0, (sales_per_day / 0.5) * 25)

        return min(100.0, score)

    async def save_demand_pattern(
        self,
        product_id: uuid.UUID,
        demand_score: float,
        breakdown: Dict[str, float],
        trend_direction: str,
    ) -> DemandPattern:
        """
        Save demand pattern to database for future reference.

        Args:
            product_id: Product UUID
            demand_score: Calculated demand score (0-100)
            breakdown: Detailed score breakdown
            trend_direction: 'increasing', 'decreasing', or 'stable'

        Returns:
            Created DemandPattern instance
        """
        pattern = DemandPattern(
            product_id=product_id,
            analysis_level="product",
            pattern_date=date.today(),
            period_type="daily",
            demand_score=Decimal(str(demand_score)),
            trend_direction=trend_direction,
            pattern_metadata=breakdown,
        )

        self.db.add(pattern)
        await self.db.flush()

        self.logger.info(f"Saved demand pattern for product {product_id}: score={demand_score}")

        return pattern

    async def calculate_and_save(
        self, product_id: uuid.UUID, days_back: int = 90
    ) -> Tuple[float, DemandPattern]:
        """
        Calculate demand score and save to database.

        Args:
            product_id: Product UUID
            days_back: Analysis period in days

        Returns:
            Tuple of (demand_score, DemandPattern instance)
        """
        demand_score, breakdown = await self.calculate_product_demand_score(
            product_id, days_back
        )

        trend_direction = breakdown.get("trend_direction", "stable")

        pattern = await self.save_demand_pattern(
            product_id, demand_score, breakdown, trend_direction
        )

        return demand_score, pattern

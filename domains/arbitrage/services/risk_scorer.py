"""
Risk Scorer - Assesses risk level for arbitrage opportunities

This service evaluates arbitrage opportunities and assigns risk scores based on:
- Demand score (from DemandScoreCalculator)
- Price volatility
- Stock availability
- Historical success rate
- Platform-specific factors
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from typing import Dict, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.integration.services.quickflip_detection_service import QuickFlipOpportunity
from domains.pricing.models import DemandPattern, MarketPrice
from shared.database.models import InventoryItem, Order, Product


logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk level classification"""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class RiskAssessment:
    """Risk assessment result"""

    risk_level: RiskLevel
    risk_score: int  # 0-100 (lower is better/safer)
    confidence_score: int  # 0-100 (confidence in assessment)
    risk_factors: Dict[str, str]
    recommendations: list[str]


class RiskScorer:
    """
    Rule-based risk scoring for arbitrage opportunities.

    Risk is calculated based on multiple factors:
    1. Demand Score (30%): Low demand = higher risk
    2. Price Volatility (25%): High volatility = higher risk
    3. Stock Availability (20%): Low stock = higher risk
    4. Profit Margin (15%): Low margin = higher risk
    5. Platform Reliability (10%): Less reliable platforms = higher risk
    """

    # Weights for different risk factors
    WEIGHT_DEMAND = 0.30
    WEIGHT_VOLATILITY = 0.25
    WEIGHT_STOCK_AVAILABILITY = 0.20
    WEIGHT_PROFIT_MARGIN = 0.15
    WEIGHT_PLATFORM = 0.10

    # Risk thresholds
    LOW_RISK_THRESHOLD = 30  # Risk score < 30 = LOW
    MEDIUM_RISK_THRESHOLD = 60  # Risk score 30-60 = MEDIUM
    # HIGH_RISK_THRESHOLD = 60  # Risk score > 60 = HIGH

    # Platform reliability scores (0-100, higher = more reliable)
    PLATFORM_RELIABILITY = {
        "stockx": 95,
        "goat": 90,
        "alias": 90,
        "ebay": 75,
        "klekt": 70,
        "awin": 60,
        "webgains": 60,
    }

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.logger = logging.getLogger(__name__)

    async def assess_opportunity_risk(
        self,
        opportunity: QuickFlipOpportunity,
        demand_score: Optional[float] = None,
    ) -> RiskAssessment:
        """
        Assess risk for an arbitrage opportunity.

        Args:
            opportunity: QuickFlipOpportunity instance
            demand_score: Pre-calculated demand score (optional)

        Returns:
            RiskAssessment with risk level, score, and recommendations
        """
        self.logger.info(
            f"Assessing risk for opportunity: {opportunity.product_name} "
            f"(profit: €{opportunity.gross_profit})"
        )

        # Calculate individual risk components
        demand_risk = await self._calculate_demand_risk(opportunity.product_id, demand_score)
        volatility_risk = await self._calculate_volatility_risk(opportunity.product_id)
        stock_risk = await self._calculate_stock_availability_risk(opportunity)
        margin_risk = self._calculate_margin_risk(opportunity)
        platform_risk = self._calculate_platform_risk(opportunity)

        # Calculate weighted overall risk score
        risk_score = int(
            demand_risk * self.WEIGHT_DEMAND
            + volatility_risk * self.WEIGHT_VOLATILITY
            + stock_risk * self.WEIGHT_STOCK_AVAILABILITY
            + margin_risk * self.WEIGHT_PROFIT_MARGIN
            + platform_risk * self.WEIGHT_PLATFORM
        )

        # Determine risk level
        if risk_score < self.LOW_RISK_THRESHOLD:
            risk_level = RiskLevel.LOW
            confidence = 85
        elif risk_score < self.MEDIUM_RISK_THRESHOLD:
            risk_level = RiskLevel.MEDIUM
            confidence = 75
        else:
            risk_level = RiskLevel.HIGH
            confidence = 80

        # Collect risk factors and recommendations
        risk_factors = self._build_risk_factors(
            demand_risk, volatility_risk, stock_risk, margin_risk, platform_risk
        )
        recommendations = self._generate_recommendations(
            risk_level, risk_factors, opportunity
        )

        assessment = RiskAssessment(
            risk_level=risk_level,
            risk_score=risk_score,
            confidence_score=confidence,
            risk_factors=risk_factors,
            recommendations=recommendations,
        )

        self.logger.info(
            f"Risk assessment for {opportunity.product_name}: "
            f"{risk_level.value} (score: {risk_score}/100)"
        )

        return assessment

    async def _calculate_demand_risk(
        self, product_id: uuid.UUID, demand_score: Optional[float]
    ) -> float:
        """
        Calculate demand-based risk (0-100, higher = more risk).

        Args:
            product_id: Product UUID
            demand_score: Pre-calculated demand score (optional)

        Returns:
            Risk score (0-100)
        """
        if demand_score is None:
            # Fetch latest demand pattern from database
            query = (
                select(DemandPattern.demand_score)
                .where(DemandPattern.product_id == product_id)
                .order_by(DemandPattern.pattern_date.desc())
                .limit(1)
            )

            result = await self.db.execute(query)
            demand_pattern = result.scalar()

            if demand_pattern:
                demand_score = float(demand_pattern)
            else:
                # No demand data available - assume medium risk
                return 50.0

        # Invert demand score: high demand = low risk
        risk = 100 - demand_score

        return max(0.0, min(100.0, risk))

    async def _calculate_volatility_risk(self, product_id: uuid.UUID) -> float:
        """
        Calculate price volatility risk based on recent price fluctuations.

        High volatility = higher risk of price drops after purchase.

        Returns:
            Risk score (0-100)
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=60)

        # Get recent sale prices
        query = (
            select(Order.net_proceeds)
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
        prices = [float(row[0]) for row in result.all()]

        if len(prices) < 3:
            # Not enough data - assume medium risk
            return 50.0

        # Calculate coefficient of variation (CV = std_dev / mean)
        mean_price = sum(prices) / len(prices)
        variance = sum((p - mean_price) ** 2 for p in prices) / len(prices)
        std_dev = variance**0.5

        cv = (std_dev / mean_price * 100) if mean_price > 0 else 0

        # Convert CV to risk score
        # CV < 5% = low risk (20)
        # CV 5-10% = medium risk (50)
        # CV > 15% = high risk (80+)
        if cv < 5:
            risk = 20 + (cv / 5) * 30
        elif cv < 10:
            risk = 50 + ((cv - 5) / 5) * 25
        elif cv < 20:
            risk = 75 + ((cv - 10) / 10) * 20
        else:
            risk = 95

        return min(100.0, risk)

    async def _calculate_stock_availability_risk(
        self, opportunity: QuickFlipOpportunity
    ) -> float:
        """
        Calculate stock availability risk.

        Low stock = higher risk that item won't be available when trying to purchase.

        Returns:
            Risk score (0-100)
        """
        stock_qty = opportunity.buy_stock_qty or 0

        # Risk based on stock quantity
        if stock_qty == 0:
            risk = 100.0  # Out of stock = maximum risk
        elif stock_qty == 1:
            risk = 80.0  # Very low stock
        elif stock_qty <= 3:
            risk = 60.0  # Low stock
        elif stock_qty <= 10:
            risk = 40.0  # Medium stock
        elif stock_qty <= 50:
            risk = 20.0  # Good stock
        else:
            risk = 10.0  # Excellent stock

        return risk

    def _calculate_margin_risk(self, opportunity: QuickFlipOpportunity) -> float:
        """
        Calculate profit margin risk.

        Low margin = higher risk (less buffer for unexpected costs).

        Returns:
            Risk score (0-100)
        """
        margin_percent = float(opportunity.profit_margin)

        # Risk based on profit margin
        if margin_percent >= 50:  # 50%+ margin
            risk = 10.0
        elif margin_percent >= 30:  # 30-50% margin
            risk = 20 + ((50 - margin_percent) / 20) * 20
        elif margin_percent >= 20:  # 20-30% margin
            risk = 40 + ((30 - margin_percent) / 10) * 20
        elif margin_percent >= 10:  # 10-20% margin
            risk = 60 + ((20 - margin_percent) / 10) * 20
        else:  # < 10% margin
            risk = 80 + (max(0, 10 - margin_percent) / 10) * 20

        return min(100.0, risk)

    def _calculate_platform_risk(self, opportunity: QuickFlipOpportunity) -> float:
        """
        Calculate platform reliability risk.

        Less reliable platforms = higher risk of fraud, delays, or issues.

        Returns:
            Risk score (0-100)
        """
        source = opportunity.buy_source.lower() if opportunity.buy_source else "unknown"

        # Get platform reliability score
        reliability = self.PLATFORM_RELIABILITY.get(source, 50)  # Default: medium

        # Invert: high reliability = low risk
        risk = 100 - reliability

        return risk

    def _build_risk_factors(
        self,
        demand_risk: float,
        volatility_risk: float,
        stock_risk: float,
        margin_risk: float,
        platform_risk: float,
    ) -> Dict[str, str]:
        """
        Build human-readable risk factor descriptions.

        Returns:
            Dictionary of risk factors with descriptions
        """
        factors = {}

        # Demand
        if demand_risk > 70:
            factors["demand"] = "Very low demand - slow sales expected"
        elif demand_risk > 50:
            factors["demand"] = "Medium demand - moderate sales speed"
        elif demand_risk > 30:
            factors["demand"] = "Good demand - reasonable turnover"
        else:
            factors["demand"] = "High demand - fast sales expected"

        # Volatility
        if volatility_risk > 70:
            factors["volatility"] = "High price volatility - unstable market"
        elif volatility_risk > 50:
            factors["volatility"] = "Moderate volatility"
        else:
            factors["volatility"] = "Stable pricing"

        # Stock
        if stock_risk > 70:
            factors["stock"] = "Very low stock - availability uncertain"
        elif stock_risk > 50:
            factors["stock"] = "Limited stock"
        else:
            factors["stock"] = "Good stock availability"

        # Margin
        if margin_risk > 70:
            factors["margin"] = "Thin profit margin - little buffer"
        elif margin_risk > 50:
            factors["margin"] = "Moderate margin"
        else:
            factors["margin"] = "Healthy profit margin"

        # Platform
        if platform_risk > 50:
            factors["platform"] = "Platform reliability concerns"
        else:
            factors["platform"] = "Reliable platform"

        return factors

    def _generate_recommendations(
        self,
        risk_level: RiskLevel,
        risk_factors: Dict[str, str],
        opportunity: QuickFlipOpportunity,
    ) -> list[str]:
        """
        Generate actionable recommendations based on risk assessment.

        Returns:
            List of recommendation strings
        """
        recommendations = []

        if risk_level == RiskLevel.LOW:
            recommendations.append("✅ Good opportunity - proceed with confidence")
            recommendations.append("Monitor price for any sudden changes")

        elif risk_level == RiskLevel.MEDIUM:
            recommendations.append("⚠️ Moderate risk - proceed with caution")

            # Specific recommendations based on risk factors
            if "Very low demand" in risk_factors.get("demand", ""):
                recommendations.append("Consider waiting for higher demand period")

            if "High price volatility" in risk_factors.get("volatility", ""):
                recommendations.append("Set strict price alerts to monitor changes")

            if "Very low stock" in risk_factors.get("stock", ""):
                recommendations.append("Purchase immediately if proceeding")

            if "Thin profit margin" in risk_factors.get("margin", ""):
                recommendations.append("Ensure all fees are accounted for")

        else:  # HIGH RISK
            recommendations.append("🛑 High risk opportunity - careful evaluation needed")
            recommendations.append("Consider passing unless you have specific knowledge")

            if "Very low demand" in risk_factors.get("demand", ""):
                recommendations.append("❌ Low demand is a red flag for arbitrage")

            if opportunity.profit_margin < 15:
                recommendations.append("❌ Margin too thin for risk level")

        return recommendations

    async def batch_assess_opportunities(
        self, opportunities: list[QuickFlipOpportunity]
    ) -> Dict[uuid.UUID, RiskAssessment]:
        """
        Assess risk for multiple opportunities in batch.

        Args:
            opportunities: List of QuickFlipOpportunity instances

        Returns:
            Dictionary mapping product_id to RiskAssessment
        """
        self.logger.info(f"Batch assessing {len(opportunities)} opportunities")

        assessments = {}

        for opp in opportunities:
            try:
                assessment = await self.assess_opportunity_risk(opp)
                assessments[opp.product_id] = assessment
            except Exception as e:
                self.logger.error(
                    f"Failed to assess risk for product {opp.product_id}: {str(e)}"
                )
                # Continue with other opportunities
                continue

        return assessments

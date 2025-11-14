"""
Enhanced Opportunity Service - QuickFlip detection with demand scoring and risk assessment

This service extends the existing QuickFlipDetectionService by adding:
- Demand score calculation
- Risk assessment
- Feasibility scoring
- Days-to-sell estimation
"""

import logging
import uuid
from dataclasses import dataclass, field
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from domains.integration.services.quickflip_detection_service import (
    QuickFlipDetectionService,
    QuickFlipOpportunity,
)

from .demand_score_calculator import DemandScoreCalculator
from .risk_scorer import RiskAssessment, RiskLevel, RiskScorer


logger = logging.getLogger(__name__)


@dataclass
class EnhancedOpportunity:
    """Enhanced opportunity with demand and risk metrics"""

    # Original QuickFlip data
    opportunity: QuickFlipOpportunity

    # Enhanced metrics
    demand_score: float  # 0-100
    demand_breakdown: dict = field(default_factory=dict)
    risk_assessment: Optional[RiskAssessment] = None
    feasibility_score: int = 0  # 0-100 (composite score)
    estimated_days_to_sell: Optional[int] = None

    def __post_init__(self) -> None:
        """Calculate composite feasibility score after initialization"""
        if self.demand_score is not None and self.risk_assessment:
            self.feasibility_score = self._calculate_feasibility()
            self.estimated_days_to_sell = self._estimate_days_to_sell()

    def _calculate_feasibility(self) -> int:
        """
        Calculate overall feasibility score (0-100).

        Combines:
        - Demand score (40%)
        - Inverted risk score (30%)
        - Profit margin (20%)
        - Stock availability (10%)
        """
        if not self.risk_assessment:
            return int(self.demand_score * 0.7)  # Fallback if no risk assessment

        # Invert risk score (low risk = high feasibility)
        inverted_risk = 100 - self.risk_assessment.risk_score

        # Profit margin component (normalized to 0-100)
        margin_pct = float(self.opportunity.profit_margin)
        margin_score = min(100, (margin_pct / 50) * 100)  # 50% margin = 100 score

        # Stock availability component
        stock_qty = self.opportunity.buy_stock_qty or 0
        if stock_qty == 0:
            stock_score = 0
        elif stock_qty <= 5:
            stock_score = 50
        elif stock_qty <= 20:
            stock_score = 75
        else:
            stock_score = 100

        # Weighted composite
        feasibility = int(
            self.demand_score * 0.40
            + inverted_risk * 0.30
            + margin_score * 0.20
            + stock_score * 0.10
        )

        return min(100, max(0, feasibility))

    def _estimate_days_to_sell(self) -> int:
        """
        Estimate days to sell based on demand score and historical turnover.

        Returns:
            Estimated days (1-90)
        """
        # Use average turnover from demand breakdown if available
        if self.demand_breakdown and "avg_turnover_days" in self.demand_breakdown:
            avg_turnover = self.demand_breakdown["avg_turnover_days"]
            if avg_turnover is not None:
                return int(avg_turnover)

        # Fallback: Estimate based on demand score
        if self.demand_score >= 80:
            return 7  # High demand: ~1 week
        elif self.demand_score >= 60:
            return 14  # Good demand: ~2 weeks
        elif self.demand_score >= 40:
            return 30  # Medium demand: ~1 month
        elif self.demand_score >= 20:
            return 60  # Low demand: ~2 months
        else:
            return 90  # Very low demand: ~3 months

    @property
    def risk_level_str(self) -> str:
        """Get risk level as string"""
        if self.risk_assessment:
            return self.risk_assessment.risk_level.value
        return "UNKNOWN"


class EnhancedOpportunityService:
    """
    Enhanced opportunity detection service with demand and risk analysis.

    Extends QuickFlipDetectionService with:
    - Demand score calculation
    - Risk assessment
    - Feasibility scoring
    - Days-to-sell estimation
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.quickflip_service = QuickFlipDetectionService(db_session)
        self.demand_calculator = DemandScoreCalculator(db_session)
        self.risk_scorer = RiskScorer(db_session)
        self.logger = logging.getLogger(__name__)

    async def find_enhanced_opportunities(
        self,
        min_profit_margin: float = 10.0,
        min_gross_profit: float = 20.0,
        max_buy_price: Optional[float] = None,
        source_filter: Optional[str] = None,
        limit: Optional[int] = None,
        calculate_demand: bool = True,
        calculate_risk: bool = True,
    ) -> List[EnhancedOpportunity]:
        """
        Find arbitrage opportunities with enhanced metrics.

        Args:
            min_profit_margin: Minimum profit margin % (default: 10%)
            min_gross_profit: Minimum gross profit € (default: €20)
            max_buy_price: Maximum buy price filter
            source_filter: Filter by source (awin, webgains, etc.)
            limit: Max number of results
            calculate_demand: Calculate demand scores (default: True)
            calculate_risk: Calculate risk assessments (default: True)

        Returns:
            List of EnhancedOpportunity instances, sorted by feasibility score
        """
        self.logger.info(
            f"Finding enhanced opportunities (min_margin={min_profit_margin}%, "
            f"min_profit=€{min_gross_profit})"
        )

        # Get base opportunities from QuickFlip service
        base_opportunities = await self.quickflip_service.find_opportunities(
            min_profit_margin=min_profit_margin,
            min_gross_profit=min_gross_profit,
            max_buy_price=max_buy_price,
            source_filter=source_filter,
            limit=limit,
        )

        if not base_opportunities:
            self.logger.info("No base opportunities found")
            return []

        self.logger.info(f"Enhancing {len(base_opportunities)} opportunities")

        # Enhance each opportunity with demand and risk metrics
        enhanced_opportunities = []

        for opp in base_opportunities:
            try:
                enhanced = await self._enhance_opportunity(
                    opp,
                    calculate_demand=calculate_demand,
                    calculate_risk=calculate_risk,
                )
                enhanced_opportunities.append(enhanced)
            except Exception as e:
                self.logger.error(
                    f"Failed to enhance opportunity for {opp.product_name}: {str(e)}"
                )
                # Continue with other opportunities
                continue

        # Sort by feasibility score (descending)
        enhanced_opportunities.sort(key=lambda x: x.feasibility_score, reverse=True)

        self.logger.info(
            f"Enhanced {len(enhanced_opportunities)} opportunities. "
            f"Top score: {enhanced_opportunities[0].feasibility_score if enhanced_opportunities else 0}"
        )

        return enhanced_opportunities

    async def _enhance_opportunity(
        self,
        opportunity: QuickFlipOpportunity,
        calculate_demand: bool = True,
        calculate_risk: bool = True,
    ) -> EnhancedOpportunity:
        """
        Enhance a single opportunity with demand and risk metrics.

        Args:
            opportunity: QuickFlipOpportunity instance
            calculate_demand: Calculate demand score
            calculate_risk: Calculate risk assessment

        Returns:
            EnhancedOpportunity instance
        """
        demand_score = 50.0  # Default neutral score
        demand_breakdown = {}
        risk_assessment = None

        # Calculate demand score
        if calculate_demand:
            try:
                demand_score, demand_breakdown = (
                    await self.demand_calculator.calculate_product_demand_score(
                        opportunity.product_id
                    )
                )
            except Exception as e:
                self.logger.warning(
                    f"Failed to calculate demand for {opportunity.product_name}: {str(e)}"
                )
                # Continue with default demand score

        # Calculate risk assessment
        if calculate_risk:
            try:
                risk_assessment = await self.risk_scorer.assess_opportunity_risk(
                    opportunity, demand_score=demand_score
                )
            except Exception as e:
                self.logger.warning(
                    f"Failed to assess risk for {opportunity.product_name}: {str(e)}"
                )
                # Continue without risk assessment

        # Create enhanced opportunity
        enhanced = EnhancedOpportunity(
            opportunity=opportunity,
            demand_score=demand_score,
            demand_breakdown=demand_breakdown,
            risk_assessment=risk_assessment,
        )

        return enhanced

    async def get_top_opportunities(
        self,
        limit: int = 10,
        min_feasibility: int = 60,
        max_risk: Optional[RiskLevel] = RiskLevel.MEDIUM,
    ) -> List[EnhancedOpportunity]:
        """
        Get top opportunities filtered by feasibility and risk.

        Args:
            limit: Maximum number of results
            min_feasibility: Minimum feasibility score (0-100)
            max_risk: Maximum acceptable risk level (LOW or MEDIUM)

        Returns:
            List of top EnhancedOpportunity instances
        """
        # Get all enhanced opportunities
        all_opportunities = await self.find_enhanced_opportunities(
            calculate_demand=True, calculate_risk=True
        )

        # Filter by feasibility and risk
        filtered = [
            opp
            for opp in all_opportunities
            if opp.feasibility_score >= min_feasibility
            and (
                max_risk is None
                or not opp.risk_assessment
                or self._risk_level_acceptable(opp.risk_assessment.risk_level, max_risk)
            )
        ]

        # Return top N
        return filtered[:limit]

    def _risk_level_acceptable(
        self, risk_level: RiskLevel, max_risk: RiskLevel
    ) -> bool:
        """Check if risk level is acceptable"""
        risk_order = {RiskLevel.LOW: 1, RiskLevel.MEDIUM: 2, RiskLevel.HIGH: 3}

        return risk_order[risk_level] <= risk_order[max_risk]

    async def get_opportunity_summary(
        self, enhanced_opportunities: List[EnhancedOpportunity]
    ) -> dict:
        """
        Get summary statistics for a list of enhanced opportunities.

        Returns:
            Dictionary with summary metrics
        """
        if not enhanced_opportunities:
            return {
                "total_opportunities": 0,
                "avg_feasibility_score": 0,
                "avg_demand_score": 0,
                "avg_risk_score": 0,
                "risk_distribution": {},
                "total_potential_profit": 0,
            }

        total = len(enhanced_opportunities)
        avg_feasibility = sum(opp.feasibility_score for opp in enhanced_opportunities) / total
        avg_demand = sum(opp.demand_score for opp in enhanced_opportunities) / total

        # Risk distribution
        risk_counts = {level: 0 for level in RiskLevel}
        total_risk_score = 0
        risks_counted = 0

        for opp in enhanced_opportunities:
            if opp.risk_assessment:
                risk_counts[opp.risk_assessment.risk_level] += 1
                total_risk_score += opp.risk_assessment.risk_score
                risks_counted += 1

        avg_risk = total_risk_score / risks_counted if risks_counted > 0 else 0

        risk_distribution = {
            level.value: count for level, count in risk_counts.items() if count > 0
        }

        total_profit = sum(float(opp.opportunity.gross_profit) for opp in enhanced_opportunities)

        return {
            "total_opportunities": total,
            "avg_feasibility_score": round(avg_feasibility, 1),
            "avg_demand_score": round(avg_demand, 1),
            "avg_risk_score": round(avg_risk, 1),
            "risk_distribution": risk_distribution,
            "total_potential_profit": round(total_profit, 2),
            "estimated_avg_days_to_sell": round(
                sum(opp.estimated_days_to_sell or 0 for opp in enhanced_opportunities) / total, 1
            ),
        }

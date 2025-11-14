"""
Arbitrage API Router

REST API endpoints for arbitrage opportunity analysis.
"""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from domains.arbitrage.services import (
    DemandScoreCalculator,
    EnhancedOpportunity,
    EnhancedOpportunityService,
    RiskAssessment,
    RiskLevel,
    RiskScorer,
)
from domains.integration.services.quickflip_detection_service import (
    QuickFlipDetectionService,
)
from shared.database.connection import get_async_session

from .schemas import (
    BatchAssessRequest,
    BatchAssessResponse,
    DemandScoreResponse,
    EnhancedOpportunityResponse,
    OpportunityBaseResponse,
    OpportunityFilterRequest,
    OpportunitySummaryResponse,
    RiskAssessmentResponse,
    RiskFactorsResponse,
    RiskLevelEnum,
    TopOpportunitiesRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/arbitrage",
    tags=["arbitrage"],
    responses={404: {"description": "Not found"}},
)


# =====================================================
# HELPER FUNCTIONS
# =====================================================


def _map_opportunity_to_response(enhanced: EnhancedOpportunity) -> EnhancedOpportunityResponse:
    """Map EnhancedOpportunity to API response model"""
    # Map base opportunity
    opp_base = OpportunityBaseResponse(
        product_id=enhanced.opportunity.product_id,
        product_name=enhanced.opportunity.product_name,
        product_sku=enhanced.opportunity.product_sku,
        brand_name=enhanced.opportunity.brand_name,
        buy_price=enhanced.opportunity.buy_price,
        buy_source=enhanced.opportunity.buy_source,
        buy_supplier=enhanced.opportunity.buy_supplier,
        buy_url=enhanced.opportunity.buy_url,
        buy_stock_qty=enhanced.opportunity.buy_stock_qty,
        sell_price=enhanced.opportunity.sell_price,
        gross_profit=enhanced.opportunity.gross_profit,
        profit_margin=enhanced.opportunity.profit_margin,
        roi=enhanced.opportunity.roi,
    )

    # Map risk assessment if available
    risk_response = None
    if enhanced.risk_assessment:
        risk_response = RiskAssessmentResponse(
            risk_level=RiskLevelEnum(enhanced.risk_assessment.risk_level.value),
            risk_score=enhanced.risk_assessment.risk_score,
            confidence_score=enhanced.risk_assessment.confidence_score,
            risk_factors=RiskFactorsResponse(**enhanced.risk_assessment.risk_factors),
            recommendations=enhanced.risk_assessment.recommendations,
        )

    return EnhancedOpportunityResponse(
        opportunity=opp_base,
        demand_score=enhanced.demand_score,
        demand_breakdown=enhanced.demand_breakdown,
        risk_assessment=risk_response,
        feasibility_score=enhanced.feasibility_score,
        estimated_days_to_sell=enhanced.estimated_days_to_sell,
        risk_level=enhanced.risk_level_str,
    )


# =====================================================
# ENDPOINTS
# =====================================================


@router.get(
    "/opportunities/enhanced",
    response_model=List[EnhancedOpportunityResponse],
    summary="Get enhanced arbitrage opportunities",
    description="Find arbitrage opportunities with demand scoring and risk assessment",
)
async def get_enhanced_opportunities(
    min_profit_margin: float = Query(
        default=10.0, ge=0, le=100, description="Minimum profit margin %"
    ),
    min_gross_profit: float = Query(default=20.0, ge=0, description="Minimum gross profit €"),
    max_buy_price: float = Query(default=None, ge=0, description="Maximum buy price €"),
    source_filter: str = Query(default=None, description="Filter by source"),
    limit: int = Query(default=10, ge=1, le=100, description="Max results"),
    calculate_demand: bool = Query(default=True, description="Calculate demand scores"),
    calculate_risk: bool = Query(default=True, description="Calculate risk assessments"),
    session: AsyncSession = Depends(get_async_session),
) -> List[EnhancedOpportunityResponse]:
    """
    Get enhanced arbitrage opportunities with demand and risk analysis.

    **Query Parameters:**
    - **min_profit_margin**: Minimum profit margin % (default: 10%)
    - **min_gross_profit**: Minimum gross profit € (default: €20)
    - **max_buy_price**: Maximum buy price filter
    - **source_filter**: Filter by source (awin, webgains, etc.)
    - **limit**: Max number of results (default: 10, max: 100)
    - **calculate_demand**: Calculate demand scores (default: true)
    - **calculate_risk**: Calculate risk assessments (default: true)

    **Returns:**
    List of enhanced opportunities sorted by feasibility score (descending)
    """
    try:
        service = EnhancedOpportunityService(session)

        opportunities = await service.find_enhanced_opportunities(
            min_profit_margin=min_profit_margin,
            min_gross_profit=min_gross_profit,
            max_buy_price=max_buy_price,
            source_filter=source_filter,
            limit=limit,
            calculate_demand=calculate_demand,
            calculate_risk=calculate_risk,
        )

        return [_map_opportunity_to_response(opp) for opp in opportunities]

    except Exception as e:
        logger.error(f"Error fetching enhanced opportunities: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch opportunities: {str(e)}",
        )


@router.get(
    "/opportunities/top",
    response_model=List[EnhancedOpportunityResponse],
    summary="Get top arbitrage opportunities",
    description="Get top opportunities filtered by feasibility and risk level",
)
async def get_top_opportunities(
    limit: int = Query(default=10, ge=1, le=50, description="Max results"),
    min_feasibility: int = Query(
        default=60, ge=0, le=100, description="Minimum feasibility score"
    ),
    max_risk: RiskLevelEnum = Query(
        default=RiskLevelEnum.MEDIUM, description="Maximum acceptable risk level"
    ),
    session: AsyncSession = Depends(get_async_session),
) -> List[EnhancedOpportunityResponse]:
    """
    Get top arbitrage opportunities filtered by feasibility and risk.

    **Query Parameters:**
    - **limit**: Maximum number of results (default: 10, max: 50)
    - **min_feasibility**: Minimum feasibility score 0-100 (default: 60)
    - **max_risk**: Maximum risk level - LOW, MEDIUM, or HIGH (default: MEDIUM)

    **Returns:**
    Top opportunities sorted by feasibility score
    """
    try:
        service = EnhancedOpportunityService(session)

        # Convert enum to RiskLevel
        risk_level_map = {
            RiskLevelEnum.LOW: RiskLevel.LOW,
            RiskLevelEnum.MEDIUM: RiskLevel.MEDIUM,
            RiskLevelEnum.HIGH: RiskLevel.HIGH,
        }
        max_risk_level = risk_level_map[max_risk]

        opportunities = await service.get_top_opportunities(
            limit=limit, min_feasibility=min_feasibility, max_risk=max_risk_level
        )

        return [_map_opportunity_to_response(opp) for opp in opportunities]

    except Exception as e:
        logger.error(f"Error fetching top opportunities: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch top opportunities: {str(e)}",
        )


@router.get(
    "/demand/{product_id}",
    response_model=DemandScoreResponse,
    summary="Get product demand score",
    description="Calculate and return demand score for a specific product",
)
async def get_product_demand_score(
    product_id: UUID,
    days_back: int = Query(default=90, ge=7, le=365, description="Analysis period in days"),
    save_pattern: bool = Query(
        default=False, description="Save demand pattern to database"
    ),
    session: AsyncSession = Depends(get_async_session),
) -> DemandScoreResponse:
    """
    Calculate demand score for a product.

    **Path Parameters:**
    - **product_id**: Product UUID

    **Query Parameters:**
    - **days_back**: Number of days to analyze (default: 90, min: 7, max: 365)
    - **save_pattern**: Save demand pattern to database (default: false)

    **Returns:**
    Demand score with detailed breakdown
    """
    try:
        calculator = DemandScoreCalculator(session)

        if save_pattern:
            demand_score, pattern = await calculator.calculate_and_save(product_id, days_back)
            return DemandScoreResponse(
                product_id=product_id,
                demand_score=demand_score,
                breakdown=pattern.pattern_metadata or {},
                pattern_date=pattern.pattern_date,
                trend_direction=pattern.trend_direction or "unknown",
            )
        else:
            demand_score, breakdown = await calculator.calculate_product_demand_score(
                product_id, days_back
            )
            return DemandScoreResponse(
                product_id=product_id,
                demand_score=demand_score,
                breakdown=breakdown,
                pattern_date=breakdown.get("pattern_date", None),
                trend_direction=breakdown.get("trend_direction", "unknown"),
            )

    except Exception as e:
        logger.error(f"Error calculating demand score for {product_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate demand score: {str(e)}",
        )


@router.post(
    "/assess-batch",
    response_model=BatchAssessResponse,
    summary="Batch risk assessment",
    description="Assess risk for multiple products in one request",
)
async def assess_batch_risk(
    request: BatchAssessRequest,
    session: AsyncSession = Depends(get_async_session),
) -> BatchAssessResponse:
    """
    Assess risk for multiple products in batch.

    **Request Body:**
    ```json
    {
        "product_ids": ["uuid1", "uuid2", ...]
    }
    ```

    **Returns:**
    Dictionary of product_id → RiskAssessment mappings

    **Note:** Maximum 50 products per request
    """
    try:
        # Get opportunities for these products
        quickflip = QuickFlipDetectionService(session)
        risk_scorer = RiskScorer(session)

        assessments = {}
        failed = 0

        for product_id in request.product_ids:
            try:
                # Find opportunities for this product
                opportunities = await quickflip.get_opportunity_by_product(product_id)

                if not opportunities:
                    failed += 1
                    continue

                # Assess first opportunity
                assessment = await risk_scorer.assess_opportunity_risk(opportunities[0])

                # Map to response
                assessments[str(product_id)] = RiskAssessmentResponse(
                    risk_level=RiskLevelEnum(assessment.risk_level.value),
                    risk_score=assessment.risk_score,
                    confidence_score=assessment.confidence_score,
                    risk_factors=RiskFactorsResponse(**assessment.risk_factors),
                    recommendations=assessment.recommendations,
                )

            except Exception as e:
                logger.warning(f"Failed to assess product {product_id}: {str(e)}")
                failed += 1
                continue

        return BatchAssessResponse(
            assessments=assessments,
            total_assessed=len(assessments),
            failed_assessments=failed,
        )

    except Exception as e:
        logger.error(f"Error in batch assessment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch assessment failed: {str(e)}",
        )


@router.get(
    "/summary",
    response_model=OpportunitySummaryResponse,
    summary="Get opportunity summary statistics",
    description="Get aggregated statistics for current arbitrage opportunities",
)
async def get_opportunity_summary(
    min_profit_margin: float = Query(default=10.0, ge=0, le=100),
    min_gross_profit: float = Query(default=20.0, ge=0),
    session: AsyncSession = Depends(get_async_session),
) -> OpportunitySummaryResponse:
    """
    Get summary statistics for arbitrage opportunities.

    **Query Parameters:**
    - **min_profit_margin**: Minimum profit margin % (default: 10%)
    - **min_gross_profit**: Minimum gross profit € (default: €20)

    **Returns:**
    Summary statistics including:
    - Total opportunities
    - Average feasibility, demand, and risk scores
    - Risk distribution
    - Total potential profit
    - Estimated average days to sell
    """
    try:
        service = EnhancedOpportunityService(session)

        # Get all opportunities
        opportunities = await service.find_enhanced_opportunities(
            min_profit_margin=min_profit_margin,
            min_gross_profit=min_gross_profit,
            calculate_demand=True,
            calculate_risk=True,
        )

        # Get summary
        summary = await service.get_opportunity_summary(opportunities)

        return OpportunitySummaryResponse(**summary)

    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate summary: {str(e)}",
        )


@router.get(
    "/health",
    summary="Health check",
    description="Check if arbitrage service is operational",
)
async def health_check(session: AsyncSession = Depends(get_async_session)) -> dict:
    """
    Health check endpoint for arbitrage service.

    **Returns:**
    Status and service information
    """
    try:
        # Quick test: try to create service instances
        _ = EnhancedOpportunityService(session)
        _ = DemandScoreCalculator(session)
        _ = RiskScorer(session)

        return {
            "status": "healthy",
            "service": "arbitrage",
            "services_available": [
                "demand_score_calculator",
                "risk_scorer",
                "enhanced_opportunity_service",
            ],
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {str(e)}",
        )

"""
Arbitrage API Router

REST API endpoints for arbitrage opportunity analysis.
"""

import logging
from datetime import time
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from domains.arbitrage.models.alert import RiskLevelFilter
from domains.arbitrage.services import (
    AlertService,
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
from shared.auth.dependencies import get_current_user
from shared.auth.models import User
from shared.database.connection import get_async_session

from .schemas import (
    AlertCreate,
    AlertResponse,
    AlertStatsResponse,
    AlertToggleRequest,
    AlertUpdate,
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


# =====================================================
# ALERT MANAGEMENT ENDPOINTS
# =====================================================


@router.post(
    "/alerts",
    response_model=AlertResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create arbitrage alert",
    description="Create a new arbitrage opportunity alert with custom filters",
)
async def create_alert(
    alert_data: AlertCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> AlertResponse:
    """
    Create a new arbitrage alert.

    **Request Body:**
    - **alert_name**: Name for the alert
    - **n8n_webhook_url**: Webhook URL for notifications
    - **Filter criteria**: min_profit_margin, min_gross_profit, etc.
    - **Schedule settings**: alert_frequency_minutes, active_hours, etc.

    **Returns:**
    Created alert configuration
    """
    try:
        alert_service = AlertService(session)

        # Parse time strings to time objects if provided
        active_hours_start = None
        active_hours_end = None
        if alert_data.active_hours_start:
            hour, minute = map(int, alert_data.active_hours_start.split(":"))
            active_hours_start = time(hour, minute)
        if alert_data.active_hours_end:
            hour, minute = map(int, alert_data.active_hours_end.split(":"))
            active_hours_end = time(hour, minute)

        # Convert RiskLevelEnum to RiskLevelFilter
        max_risk_filter = RiskLevelFilter(alert_data.max_risk_level.value)

        alert = await alert_service.create_alert(
            user_id=current_user.id,
            alert_name=alert_data.alert_name,
            description=alert_data.description,
            n8n_webhook_url=alert_data.n8n_webhook_url,
            min_profit_margin=alert_data.min_profit_margin,
            min_gross_profit=alert_data.min_gross_profit,
            max_buy_price=alert_data.max_buy_price,
            min_feasibility_score=alert_data.min_feasibility_score,
            max_risk_level=max_risk_filter,
            source_filter=alert_data.source_filter,
            additional_filters=alert_data.additional_filters,
            notification_config=alert_data.notification_config,
            include_demand_breakdown=alert_data.include_demand_breakdown,
            include_risk_details=alert_data.include_risk_details,
            max_opportunities_per_alert=alert_data.max_opportunities_per_alert,
            alert_frequency_minutes=alert_data.alert_frequency_minutes,
            active_hours_start=active_hours_start,
            active_hours_end=active_hours_end,
            active_days=alert_data.active_days,
            timezone=alert_data.timezone,
            active=alert_data.active,
        )

        return _map_alert_to_response(alert)

    except Exception as e:
        logger.error(f"Error creating alert: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create alert: {str(e)}",
        )


@router.get(
    "/alerts",
    response_model=List[AlertResponse],
    summary="List user's alerts",
    description="Get all alerts for the current user",
)
async def list_alerts(
    active_only: bool = Query(default=False, description="Only return active alerts"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> List[AlertResponse]:
    """
    List all alerts for the current user.

    **Query Parameters:**
    - **active_only**: Only return active alerts (default: false)

    **Returns:**
    List of user's alerts
    """
    try:
        alert_service = AlertService(session)
        alerts = await alert_service.get_user_alerts(current_user.id, active_only)
        return [_map_alert_to_response(alert) for alert in alerts]

    except Exception as e:
        logger.error(f"Error listing alerts: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list alerts: {str(e)}",
        )


@router.get(
    "/alerts/{alert_id}",
    response_model=AlertResponse,
    summary="Get alert details",
    description="Get details of a specific alert",
)
async def get_alert(
    alert_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> AlertResponse:
    """
    Get details of a specific alert.

    **Path Parameters:**
    - **alert_id**: UUID of the alert

    **Returns:**
    Alert configuration
    """
    try:
        alert_service = AlertService(session)
        alert = await alert_service.get_alert(alert_id)

        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert {alert_id} not found",
            )

        # Ensure user owns this alert
        if alert.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )

        return _map_alert_to_response(alert)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting alert: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alert: {str(e)}",
        )


@router.put(
    "/alerts/{alert_id}",
    response_model=AlertResponse,
    summary="Update alert",
    description="Update alert configuration",
)
async def update_alert(
    alert_id: UUID,
    alert_data: AlertUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> AlertResponse:
    """
    Update an existing alert.

    **Path Parameters:**
    - **alert_id**: UUID of the alert

    **Request Body:**
    Only include fields you want to update (all fields optional)

    **Returns:**
    Updated alert configuration
    """
    try:
        alert_service = AlertService(session)
        alert = await alert_service.get_alert(alert_id)

        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert {alert_id} not found",
            )

        # Ensure user owns this alert
        if alert.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )

        # Build update dictionary (only non-None values)
        update_dict = {}
        for field, value in alert_data.model_dump(exclude_unset=True).items():
            if value is not None:
                # Convert time strings to time objects
                if field == "active_hours_start" and isinstance(value, str):
                    hour, minute = map(int, value.split(":"))
                    value = time(hour, minute)
                elif field == "active_hours_end" and isinstance(value, str):
                    hour, minute = map(int, value.split(":"))
                    value = time(hour, minute)
                # Convert RiskLevelEnum to RiskLevelFilter
                elif field == "max_risk_level" and isinstance(value, RiskLevelEnum):
                    value = RiskLevelFilter(value.value)

                update_dict[field] = value

        updated_alert = await alert_service.update_alert(alert_id, update_dict)
        return _map_alert_to_response(updated_alert)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating alert: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update alert: {str(e)}",
        )


@router.delete(
    "/alerts/{alert_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete alert",
    description="Delete an alert",
)
async def delete_alert(
    alert_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Delete an alert.

    **Path Parameters:**
    - **alert_id**: UUID of the alert

    **Returns:**
    No content (204) on success
    """
    try:
        alert_service = AlertService(session)
        alert = await alert_service.get_alert(alert_id)

        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert {alert_id} not found",
            )

        # Ensure user owns this alert
        if alert.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )

        await alert_service.delete_alert(alert_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting alert: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete alert: {str(e)}",
        )


@router.post(
    "/alerts/{alert_id}/toggle",
    response_model=AlertResponse,
    summary="Enable/disable alert",
    description="Enable or disable an alert",
)
async def toggle_alert(
    alert_id: UUID,
    toggle_data: AlertToggleRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> AlertResponse:
    """
    Enable or disable an alert.

    **Path Parameters:**
    - **alert_id**: UUID of the alert

    **Request Body:**
    - **active**: true to enable, false to disable

    **Returns:**
    Updated alert configuration
    """
    try:
        alert_service = AlertService(session)
        alert = await alert_service.get_alert(alert_id)

        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert {alert_id} not found",
            )

        # Ensure user owns this alert
        if alert.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )

        updated_alert = await alert_service.toggle_alert(alert_id, toggle_data.active)
        return _map_alert_to_response(updated_alert)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling alert: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle alert: {str(e)}",
        )


@router.get(
    "/alerts/{alert_id}/stats",
    response_model=AlertStatsResponse,
    summary="Get alert statistics",
    description="Get performance statistics for an alert",
)
async def get_alert_stats(
    alert_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> AlertStatsResponse:
    """
    Get statistics for an alert.

    **Path Parameters:**
    - **alert_id**: UUID of the alert

    **Returns:**
    Alert performance statistics
    """
    try:
        alert_service = AlertService(session)
        alert = await alert_service.get_alert(alert_id)

        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert {alert_id} not found",
            )

        # Ensure user owns this alert
        if alert.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )

        stats = await alert_service.get_alert_statistics(alert_id)
        return AlertStatsResponse(**stats)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting alert stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alert stats: {str(e)}",
        )


# =====================================================
# HELPER FUNCTIONS
# =====================================================


def _map_alert_to_response(alert) -> AlertResponse:
    """Map ArbitrageAlert model to API response"""
    return AlertResponse(
        id=alert.id,
        user_id=alert.user_id,
        alert_name=alert.alert_name,
        description=alert.description,
        active=alert.active,
        n8n_webhook_url=alert.n8n_webhook_url,
        min_profit_margin=float(alert.min_profit_margin),
        min_gross_profit=float(alert.min_gross_profit),
        max_buy_price=float(alert.max_buy_price) if alert.max_buy_price else None,
        min_feasibility_score=alert.min_feasibility_score,
        max_risk_level=RiskLevelEnum(alert.max_risk_level.value),
        source_filter=alert.source_filter,
        additional_filters=alert.additional_filters,
        notification_config=alert.notification_config,
        include_demand_breakdown=alert.include_demand_breakdown,
        include_risk_details=alert.include_risk_details,
        max_opportunities_per_alert=alert.max_opportunities_per_alert,
        alert_frequency_minutes=alert.alert_frequency_minutes,
        active_hours_start=alert.active_hours_start.isoformat() if alert.active_hours_start else None,
        active_hours_end=alert.active_hours_end.isoformat() if alert.active_hours_end else None,
        active_days=alert.active_days,
        timezone=alert.timezone,
        last_triggered_at=alert.last_triggered_at,
        last_scanned_at=alert.last_scanned_at,
        total_alerts_sent=alert.total_alerts_sent,
        total_opportunities_sent=alert.total_opportunities_sent,
        last_error=alert.last_error,
        last_error_at=alert.last_error_at,
        created_at=alert.created_at,
        updated_at=alert.updated_at,
    )


# =====================================================
# HEALTH CHECK
# =====================================================


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
        _ = AlertService(session)

        return {
            "status": "healthy",
            "service": "arbitrage",
            "services_available": [
                "demand_score_calculator",
                "risk_scorer",
                "enhanced_opportunity_service",
                "alert_service",
            ],
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {str(e)}",
        )

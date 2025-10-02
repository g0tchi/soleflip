"""
QuickFlip Detection API Router
REST endpoints for arbitrage opportunity detection and market price management
"""

from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from shared.api.dependencies import get_db_session
from domains.integration.services.quickflip_detection_service import QuickFlipDetectionService
from domains.integration.services.market_price_import_service import MarketPriceImportService

router = APIRouter()


# Pydantic Models for API
class QuickFlipOpportunityResponse(BaseModel):
    """Response model for QuickFlip opportunities"""
    product_id: str
    product_name: str
    product_sku: str
    brand_name: str
    buy_price: float
    buy_source: str
    buy_supplier: str
    buy_url: Optional[str]
    buy_stock_qty: Optional[int]
    sell_price: float
    stockx_listing_id: Optional[str]
    gross_profit: float
    profit_margin: float
    roi: float
    days_since_last_sale: Optional[int]
    stockx_demand_score: Optional[float]

    class Config:
        from_attributes = True


class QuickFlipSummaryResponse(BaseModel):
    """Response model for opportunity summary"""
    total_opportunities: int
    avg_profit_margin: float
    avg_gross_profit: float
    best_opportunity: Optional[QuickFlipOpportunityResponse]
    sources_breakdown: Dict[str, Dict[str, float]]


class OpportunityFilters(BaseModel):
    """Filters for opportunity search"""
    min_profit_margin: Optional[float] = Field(default=10.0, ge=0, le=1000)
    min_gross_profit: Optional[float] = Field(default=20.0, ge=0)
    max_buy_price: Optional[float] = Field(default=None, ge=0)
    sources: Optional[List[str]] = Field(default=None)
    limit: Optional[int] = Field(default=100, ge=1, le=1000)


class ImportStatsResponse(BaseModel):
    """Response model for import statistics"""
    total_market_prices: int
    sources_breakdown: Optional[Dict[str, int]] = None


@router.get(
    "/opportunities",
    response_model=List[QuickFlipOpportunityResponse],
    summary="Find QuickFlip opportunities",
    description="Discover profitable arbitrage opportunities by comparing market prices with StockX data"
)
async def get_quickflip_opportunities(
    min_profit_margin: float = Query(default=10.0, ge=0, le=1000, description="Minimum profit margin percentage"),
    min_gross_profit: float = Query(default=20.0, ge=0, description="Minimum gross profit in EUR"),
    max_buy_price: Optional[float] = Query(default=None, ge=0, description="Maximum buy price filter"),
    sources: Optional[str] = Query(default=None, description="Comma-separated list of sources (e.g., 'awin,webgains')"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of opportunities to return"),
    db: AsyncSession = Depends(get_db_session),
    # user = Depends(require_authenticated_user)  # Uncomment for authentication
):
    """Get QuickFlip opportunities with customizable filters"""

    detection_service = QuickFlipDetectionService(db)

    # Parse sources parameter
    sources_list = None
    if sources:
        sources_list = [s.strip() for s in sources.split(",") if s.strip()]

    try:
        opportunities = await detection_service.find_opportunities(
            min_profit_margin=min_profit_margin,
            min_gross_profit=Decimal(str(min_gross_profit)),
            max_buy_price=Decimal(str(max_buy_price)) if max_buy_price else None,
            sources=sources_list,
            limit=limit
        )

        # Convert to response models
        return [QuickFlipOpportunityResponse(**opp.to_dict()) for opp in opportunities]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find opportunities: {str(e)}"
        )


@router.get(
    "/opportunities/summary",
    response_model=QuickFlipSummaryResponse,
    summary="Get opportunities summary",
    description="Get statistical summary of all available QuickFlip opportunities"
)
async def get_opportunities_summary(
    db: AsyncSession = Depends(get_db_session),
    # user = Depends(require_authenticated_user)
):
    """Get summary statistics about available opportunities"""

    detection_service = QuickFlipDetectionService(db)

    try:
        summary = await detection_service.get_opportunities_summary()

        # Convert best opportunity to response model if it exists
        best_opp = None
        if summary.get("best_opportunity"):
            best_opp = QuickFlipOpportunityResponse(**summary["best_opportunity"])

        return QuickFlipSummaryResponse(
            total_opportunities=summary["total_opportunities"],
            avg_profit_margin=summary["avg_profit_margin"],
            avg_gross_profit=summary["avg_gross_profit"],
            best_opportunity=best_opp,
            sources_breakdown=summary["sources_breakdown"]
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get summary: {str(e)}"
        )


@router.get(
    "/opportunities/product/{product_id}",
    response_model=List[QuickFlipOpportunityResponse],
    summary="Get opportunities for specific product",
    description="Get all available opportunities for a specific product"
)
async def get_opportunities_by_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    # user = Depends(require_authenticated_user)
):
    """Get opportunities for a specific product"""

    detection_service = QuickFlipDetectionService(db)

    try:
        opportunities = await detection_service.get_opportunity_by_product(product_id)

        return [QuickFlipOpportunityResponse(**opp.to_dict()) for opp in opportunities]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get opportunities for product: {str(e)}"
        )


@router.get(
    "/opportunities/source/{source}",
    response_model=List[QuickFlipOpportunityResponse],
    summary="Get best opportunities by source",
    description="Get the best opportunities from a specific data source"
)
async def get_opportunities_by_source(
    source: str,
    limit: int = Query(default=20, ge=1, le=100, description="Maximum number of opportunities to return"),
    db: AsyncSession = Depends(get_db_session),
    # user = Depends(require_authenticated_user)
):
    """Get best opportunities from a specific source"""

    detection_service = QuickFlipDetectionService(db)

    try:
        opportunities = await detection_service.get_best_opportunities_by_source(
            source=source,
            limit=limit
        )

        return [QuickFlipOpportunityResponse(**opp.to_dict()) for opp in opportunities]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get opportunities for source {source}: {str(e)}"
        )


@router.post(
    "/opportunities/mark-acted",
    status_code=status.HTTP_200_OK,
    summary="Mark opportunity as acted upon",
    description="Mark an opportunity as acted upon (purchased, etc.) for tracking"
)
async def mark_opportunity_acted(
    product_id: UUID,
    source: str,
    action: str = "purchased",
    db: AsyncSession = Depends(get_db_session),
    # user = Depends(require_authenticated_user)
):
    """Mark an opportunity as acted upon"""

    detection_service = QuickFlipDetectionService(db)

    try:
        result = await detection_service.mark_opportunity_as_acted(
            product_id=product_id,
            source=source,
            action=action
        )

        return {
            "success": result,
            "message": f"Opportunity marked as {action}",
            "product_id": str(product_id),
            "source": source
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark opportunity: {str(e)}"
        )


# Market Price Import Endpoints
@router.post(
    "/import/csv",
    status_code=status.HTTP_200_OK,
    summary="Import market prices from CSV",
    description="Import product price data from CSV file (AWIN, Webgains, etc.)"
)
async def import_market_prices_csv(
    file_path: str,
    source: str = "awin",
    db: AsyncSession = Depends(get_db_session),
    # user = Depends(require_authenticated_user)
):
    """Import market prices from CSV file"""

    import_service = MarketPriceImportService(db)

    try:
        stats = await import_service.import_csv_file(
            file_path=file_path,
            source=source
        )

        return {
            "success": True,
            "message": f"Successfully imported {stats['created']} new prices and updated {stats['updated']} existing prices",
            "statistics": stats
        }

    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CSV file not found: {file_path}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import CSV: {str(e)}"
        )


@router.get(
    "/import/stats",
    response_model=ImportStatsResponse,
    summary="Get import statistics",
    description="Get statistics about imported market price data"
)
async def get_import_stats(
    source: Optional[str] = Query(default=None, description="Specific source to get stats for"),
    db: AsyncSession = Depends(get_db_session),
    # user = Depends(require_authenticated_user)
):
    """Get statistics about imported market price data"""

    import_service = MarketPriceImportService(db)

    try:
        stats = await import_service.get_import_stats(source=source)

        return ImportStatsResponse(**stats)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get import stats: {str(e)}"
        )


# Health check endpoint
@router.get(
    "/health",
    summary="QuickFlip service health check",
    description="Check if QuickFlip detection service is operational"
)
async def quickflip_health_check(
    db: AsyncSession = Depends(get_db_session)
):
    """Health check for QuickFlip service"""

    try:
        # Simple test to ensure database connectivity and service functionality
        detection_service = QuickFlipDetectionService(db)

        # Get a quick summary without full processing
        summary = await detection_service.get_opportunities_summary()

        return {
            "status": "healthy",
            "service": "quickflip_detection",
            "total_opportunities": summary.get("total_opportunities", 0),
            "timestamp": "2025-09-18T08:30:00Z"  # Could use datetime.utcnow()
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"QuickFlip service unhealthy: {str(e)}"
        )
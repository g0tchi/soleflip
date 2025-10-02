"""
Business Intelligence API Endpoints
Notion-style analytics with ROI, PAS, and Shelf Life insights
"""

from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from domains.analytics.services.business_intelligence_service import BusinessIntelligenceService
from shared.api.dependencies import get_db_session, ResponseFormatter
from shared.database.models import InventoryItem

router = APIRouter(prefix="/api/analytics/business-intelligence", tags=["Business Intelligence"])


# Response Models
class InventoryAnalyticsResponse(BaseModel):
    shelf_life_days: int
    roi_percentage: float
    profit_per_shelf_day: float
    profit: float
    sale_overview: str


class DeadStockItem(BaseModel):
    item_id: str
    product_name: str
    sku: str
    purchase_price: float
    days_in_stock: int
    profit_per_day: float
    total_cost: float
    size: Optional[str]
    supplier: Optional[str]
    status: str


class ROIPerformanceItem(BaseModel):
    item_id: str
    product_name: str
    sku: str
    roi_percentage: float
    profit_per_shelf_day: float
    shelf_life_days: Optional[int]
    purchase_price: float
    size: Optional[str]


class ROIPerformanceReport(BaseModel):
    summary: Dict
    best_performers: List[ROIPerformanceItem]
    worst_performers: List[ROIPerformanceItem]


class ShelfLifeDistributionItem(BaseModel):
    shelf_life_days: int
    item_count: int
    category: str


class ShelfLifeDistribution(BaseModel):
    summary: Dict
    distribution: List[ShelfLifeDistributionItem]


class SupplierPerformanceItem(BaseModel):
    supplier_id: str
    supplier_name: str
    month_year: Optional[str]
    total_orders: Optional[int]
    avg_delivery_time: float
    return_rate: float
    avg_roi: float
    supplier_category: Optional[str]
    vat_rate: float
    default_email: Optional[str]


# Request Models
class UpdateAnalyticsRequest(BaseModel):
    sale_price: Optional[Decimal] = Field(None, description="Sale price for ROI calculation")
    sale_date: Optional[date] = Field(None, description="Sale date for shelf life calculation")


async def get_bi_service(db: AsyncSession = Depends(get_db_session)) -> BusinessIntelligenceService:
    """Get Business Intelligence service instance"""
    return BusinessIntelligenceService(db)


@router.get("/inventory/{item_id}/analytics", response_model=InventoryAnalyticsResponse)
async def get_inventory_analytics(
    item_id: UUID,
    sale_price: Optional[float] = Query(None, description="Optional sale price for ROI calculation"),
    sale_date: Optional[date] = Query(None, description="Optional sale date for shelf life calculation"),
    bi_service: BusinessIntelligenceService = Depends(get_bi_service)
):
    """
    Calculate comprehensive analytics for a specific inventory item
    Includes ROI, PAS (Profit per Shelf day), and shelf life calculations
    """
    try:
        # Get inventory item
        from sqlalchemy import select
        query = select(InventoryItem).where(InventoryItem.id == item_id)
        result = await bi_service.db.execute(query)
        item = result.scalar_one_or_none()

        if not item:
            raise HTTPException(status_code=404, detail=f"Inventory item {item_id} not found")

        sale_price_decimal = Decimal(str(sale_price)) if sale_price else None
        analytics = await bi_service.calculate_inventory_analytics(item, sale_price_decimal, sale_date)

        return InventoryAnalyticsResponse(**analytics)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate analytics: {str(e)}")


@router.post("/inventory/{item_id}/update-analytics", response_model=InventoryAnalyticsResponse)
async def update_inventory_analytics(
    item_id: UUID,
    update_request: UpdateAnalyticsRequest,
    bi_service: BusinessIntelligenceService = Depends(get_bi_service)
):
    """
    Update and persist analytics for an inventory item
    Used when item is sold or status changes
    """
    try:
        analytics = await bi_service.update_inventory_analytics(
            item_id, update_request.sale_price, update_request.sale_date
        )
        return InventoryAnalyticsResponse(**analytics)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update analytics: {str(e)}")


@router.get("/dead-stock", response_model=List[DeadStockItem])
async def get_dead_stock_analysis(
    days_threshold: int = Query(90, description="Days threshold for dead stock identification"),
    bi_service: BusinessIntelligenceService = Depends(get_bi_service)
):
    """
    Identify dead stock using shelf life analysis
    Items in stock longer than threshold are considered dead stock
    """
    try:
        dead_stock = await bi_service.get_dead_stock_analysis(days_threshold)
        return [DeadStockItem(**item) for item in dead_stock]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze dead stock: {str(e)}")


@router.get("/roi-performance", response_model=ROIPerformanceReport)
async def get_roi_performance_report(
    limit: int = Query(100, description="Number of items to return for best/worst performers"),
    bi_service: BusinessIntelligenceService = Depends(get_bi_service)
):
    """
    Generate comprehensive ROI performance report
    Shows best and worst performing items by return on investment
    """
    try:
        report = await bi_service.get_roi_performance_report(limit)

        return ROIPerformanceReport(
            summary=report["summary"],
            best_performers=[ROIPerformanceItem(**item) for item in report["best_performers"]],
            worst_performers=[ROIPerformanceItem(**item) for item in report["worst_performers"]]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate ROI report: {str(e)}")


@router.get("/shelf-life-distribution", response_model=ShelfLifeDistribution)
async def get_shelf_life_distribution(
    bi_service: BusinessIntelligenceService = Depends(get_bi_service)
):
    """
    Analyze shelf life distribution across inventory
    Categorizes items as fast/medium/slow moving or dead stock
    """
    try:
        distribution = await bi_service.get_shelf_life_distribution()

        return ShelfLifeDistribution(
            summary=distribution["summary"],
            distribution=[ShelfLifeDistributionItem(**item) for item in distribution["distribution"]]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze shelf life distribution: {str(e)}")


@router.get("/supplier-performance", response_model=List[SupplierPerformanceItem])
async def get_supplier_performance(
    supplier_id: Optional[UUID] = Query(None, description="Filter by specific supplier"),
    bi_service: BusinessIntelligenceService = Depends(get_bi_service)
):
    """
    Get supplier performance analytics
    Shows delivery times, return rates, and ROI performance by supplier
    """
    try:
        performance = await bi_service.get_supplier_performance_summary(supplier_id)
        return [SupplierPerformanceItem(**item) for item in performance]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get supplier performance: {str(e)}")


@router.get("/dashboard-metrics")
async def get_dashboard_metrics(
    bi_service: BusinessIntelligenceService = Depends(get_bi_service)
):
    """
    Get key business intelligence metrics for dashboard
    Combines multiple analytics for overview display
    """
    try:
        # Get dead stock count
        dead_stock = await bi_service.get_dead_stock_analysis(90)
        dead_stock_count = len(dead_stock)

        # Get shelf life distribution summary
        shelf_distribution = await bi_service.get_shelf_life_distribution()

        # Get ROI performance summary
        roi_report = await bi_service.get_roi_performance_report(10)

        dashboard_metrics = {
            "dead_stock_count": dead_stock_count,
            "total_inventory_items": shelf_distribution["summary"]["total_items"],
            "fast_moving_percentage": shelf_distribution["summary"]["fast_moving_percentage"],
            "dead_stock_percentage": shelf_distribution["summary"]["dead_stock_percentage"],
            "average_roi": roi_report["summary"]["average_roi"],
            "best_roi_items": roi_report["best_performers"][:5],  # Top 5
            "analysis_timestamp": roi_report["summary"]["analysis_date"]
        }

        return ResponseFormatter.format_success_response(
            "Dashboard metrics retrieved successfully",
            dashboard_metrics,
            "dashboard_metrics"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard metrics: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint for business intelligence service"""
    return {"status": "healthy", "service": "business_intelligence", "features": [
        "roi_calculation", "pas_analysis", "shelf_life_tracking", "dead_stock_detection",
        "supplier_performance", "notion_feature_parity"
    ]}
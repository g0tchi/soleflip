"""
Supplier Intelligence API
45+ Supplier Management with Notion Feature Parity
"""

from datetime import date
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from domains.suppliers.services.supplier_intelligence_service import SupplierIntelligenceService
from shared.api.dependencies import get_db_session, ResponseFormatter

router = APIRouter(prefix="/api/suppliers/intelligence", tags=["Supplier Intelligence"])


# Response Models
class SupplierCreateResponse(BaseModel):
    supplier_id: str
    name: str
    category: str
    message: str


class SupplierPerformanceMetrics(BaseModel):
    total_orders: int
    avg_delivery_time: float
    return_rate: float
    avg_roi: float


class SupplierIntelligenceDashboard(BaseModel):
    summary: Dict
    category_distribution: Dict[str, int]
    country_distribution: Dict[str, int]
    top_performers: List[Dict]
    analysis_date: str


class SupplierRecommendation(BaseModel):
    supplier_id: str
    name: str
    category: str
    country: str
    vat_rate: float
    performance_score: float
    avg_roi: float
    recommendation_reason: str


# Request Models
class CreateSupplierRequest(BaseModel):
    name: str = Field(..., description="Supplier name")
    email: Optional[str] = Field(None, description="Default email address")
    vat_rate: Optional[float] = Field(19.0, description="VAT rate percentage")
    return_policy: Optional[str] = Field(None, description="Return policy description")
    contact_person: Optional[str] = Field(None, description="Contact person name")
    phone: Optional[str] = Field(None, description="Phone number")
    website: Optional[str] = Field(None, description="Website URL")
    address: Optional[str] = Field(None, description="Address")
    city: Optional[str] = Field("Unknown", description="City")
    country: Optional[str] = Field("Germany", description="Country")
    return_days: Optional[int] = Field(14, description="Return policy days")
    payment_terms: Optional[str] = Field("Net 30", description="Payment terms")
    min_order: Optional[float] = Field(50.0, description="Minimum order amount")


async def get_supplier_intelligence_service(db: AsyncSession = Depends(get_db_session)) -> SupplierIntelligenceService:
    """Get Supplier Intelligence service instance"""
    return SupplierIntelligenceService(db)


@router.post("/suppliers", response_model=SupplierCreateResponse)
async def create_supplier(
    supplier_request: CreateSupplierRequest,
    service: SupplierIntelligenceService = Depends(get_supplier_intelligence_service)
):
    """
    Create a new supplier with intelligence data
    Automatically categorizes supplier and sets appropriate defaults
    """
    try:
        supplier_data = supplier_request.dict()
        supplier_id = await service.create_supplier_from_notion_data(supplier_data)

        # Get the created supplier info
        from sqlalchemy import select
        from shared.database.models import Supplier
        query = select(Supplier).where(Supplier.id == supplier_id)
        result = await service.db.execute(query)
        supplier = result.scalar_one()

        return SupplierCreateResponse(
            supplier_id=str(supplier_id),
            name=supplier.name,
            category=supplier.supplier_category,
            message=f"Supplier '{supplier.name}' created successfully with category '{supplier.supplier_category}'"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create supplier: {str(e)}")


@router.post("/bulk-create-notion-suppliers")
async def bulk_create_notion_suppliers(
    service: SupplierIntelligenceService = Depends(get_supplier_intelligence_service)
):
    """
    Bulk create all 45+ suppliers from Notion analysis
    Recreates the comprehensive supplier network identified in Notion
    """
    try:
        supplier_ids = await service.bulk_create_notion_suppliers()

        return ResponseFormatter.format_success_response(
            f"Successfully created/verified {len(supplier_ids)} suppliers from Notion analysis",
            {
                "created_supplier_ids": [str(sid) for sid in supplier_ids],
                "total_count": len(supplier_ids),
                "notion_target": 45,
                "completion_status": "completed" if len(supplier_ids) >= 45 else "in_progress"
            },
            "bulk_supplier_creation"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to bulk create suppliers: {str(e)}")


@router.post("/suppliers/{supplier_id}/calculate-performance", response_model=SupplierPerformanceMetrics)
async def calculate_supplier_performance(
    supplier_id: UUID,
    month_year: date = Query(..., description="Month for performance calculation (YYYY-MM-DD)"),
    service: SupplierIntelligenceService = Depends(get_supplier_intelligence_service)
):
    """
    Calculate monthly performance metrics for a supplier
    Includes delivery time, return rate, and ROI analysis
    """
    try:
        performance = await service.calculate_supplier_performance(supplier_id, month_year)
        return SupplierPerformanceMetrics(**performance)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate performance: {str(e)}")


@router.get("/dashboard", response_model=SupplierIntelligenceDashboard)
async def get_supplier_intelligence_dashboard(
    service: SupplierIntelligenceService = Depends(get_supplier_intelligence_service)
):
    """
    Get comprehensive supplier intelligence dashboard
    Shows 45+ supplier analytics with performance insights
    """
    try:
        dashboard = await service.get_supplier_intelligence_dashboard()
        return SupplierIntelligenceDashboard(**dashboard)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard: {str(e)}")


@router.get("/recommendations", response_model=List[SupplierRecommendation])
async def get_supplier_recommendations(
    category: Optional[str] = Query(None, description="Filter by supplier category"),
    service: SupplierIntelligenceService = Depends(get_supplier_intelligence_service)
):
    """
    Get supplier recommendations based on performance analytics
    Returns top performing suppliers with recommendation reasons
    """
    try:
        recommendations = await service.get_supplier_recommendations(category)
        return [SupplierRecommendation(**rec) for rec in recommendations]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")


@router.get("/categories")
async def get_supplier_categories(
    service: SupplierIntelligenceService = Depends(get_supplier_intelligence_service)
):
    """
    Get all supplier categories with example suppliers
    Shows the 45+ supplier categorization system from Notion
    """
    return ResponseFormatter.format_success_response(
        "Supplier categories retrieved successfully",
        {
            "categories": service.SUPPLIER_CATEGORIES,
            "total_categories": len(service.SUPPLIER_CATEGORIES),
            "total_example_suppliers": sum(len(suppliers) for suppliers in service.SUPPLIER_CATEGORIES.values())
        },
        "supplier_categories"
    )


@router.get("/performance-summary/{supplier_id}")
async def get_supplier_performance_summary(
    supplier_id: UUID,
    service: SupplierIntelligenceService = Depends(get_supplier_intelligence_service)
):
    """
    Get comprehensive performance summary for a specific supplier
    Includes historical performance data and trends
    """
    try:
        from sqlalchemy import select, desc
        from shared.database.models import Supplier, SupplierPerformance

        # Get supplier info
        supplier_query = select(Supplier).where(Supplier.id == supplier_id)
        supplier_result = await service.db.execute(supplier_query)
        supplier = supplier_result.scalar_one_or_none()

        if not supplier:
            raise HTTPException(status_code=404, detail=f"Supplier {supplier_id} not found")

        # Get performance history
        performance_query = select(SupplierPerformance).where(
            SupplierPerformance.supplier_id == supplier_id
        ).order_by(desc(SupplierPerformance.month_year))

        performance_result = await service.db.execute(performance_query)
        performance_records = performance_result.fetchall()

        performance_history = []
        for record in performance_records:
            performance_history.append({
                "month_year": record.month_year.isoformat() if record.month_year else None,
                "total_orders": record.total_orders,
                "avg_delivery_time": float(record.avg_delivery_time or 0),
                "return_rate": float(record.return_rate or 0),
                "avg_roi": float(record.avg_roi or 0)
            })

        summary = {
            "supplier_info": {
                "id": str(supplier.id),
                "name": supplier.name,
                "category": supplier.supplier_category,
                "country": supplier.country,
                "vat_rate": float(supplier.vat_rate or 0),
                "default_email": supplier.default_email,
                "return_policy": supplier.return_policy
            },
            "performance_history": performance_history,
            "performance_count": len(performance_history),
            "latest_performance": performance_history[0] if performance_history else None
        }

        return ResponseFormatter.format_success_response(
            f"Performance summary for {supplier.name} retrieved successfully",
            summary,
            "supplier_performance_summary"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance summary: {str(e)}")


@router.get("/analytics/category/{category}")
async def get_category_analytics(
    category: str,
    service: SupplierIntelligenceService = Depends(get_supplier_intelligence_service)
):
    """
    Get analytics for a specific supplier category
    Shows performance comparison within category
    """
    try:
        from sqlalchemy import select, func
        from shared.database.models import Supplier, SupplierPerformance

        # Get suppliers in category
        suppliers_query = select(Supplier).where(Supplier.supplier_category == category)
        suppliers_result = await service.db.execute(suppliers_query)
        suppliers = suppliers_result.fetchall()

        if not suppliers:
            raise HTTPException(status_code=404, detail=f"No suppliers found in category '{category}'")

        # Get performance data for category
        supplier_ids = [supplier.id for supplier in suppliers]
        performance_query = select(
            func.avg(SupplierPerformance.avg_roi).label('avg_roi'),
            func.avg(SupplierPerformance.avg_delivery_time).label('avg_delivery_time'),
            func.avg(SupplierPerformance.return_rate).label('avg_return_rate'),
            func.sum(SupplierPerformance.total_orders).label('total_orders')
        ).where(SupplierPerformance.supplier_id.in_(supplier_ids))

        performance_result = await service.db.execute(performance_query)
        performance_stats = performance_result.fetchone()

        analytics = {
            "category": category,
            "supplier_count": len(suppliers),
            "performance_stats": {
                "avg_roi": float(performance_stats.avg_roi or 0),
                "avg_delivery_time": float(performance_stats.avg_delivery_time or 0),
                "avg_return_rate": float(performance_stats.avg_return_rate or 0),
                "total_orders": int(performance_stats.total_orders or 0)
            },
            "suppliers": [
                {
                    "id": str(supplier.id),
                    "name": supplier.name,
                    "country": supplier.country,
                    "vat_rate": float(supplier.vat_rate or 0)
                }
                for supplier in suppliers
            ]
        }

        return ResponseFormatter.format_success_response(
            f"Category analytics for '{category}' retrieved successfully",
            analytics,
            "category_analytics"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get category analytics: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint for supplier intelligence service"""
    return {
        "status": "healthy",
        "service": "supplier_intelligence",
        "features": [
            "45_supplier_management", "performance_analytics", "category_intelligence",
            "notion_feature_parity", "roi_tracking", "delivery_analytics"
        ],
        "notion_target": 45
    }
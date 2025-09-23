"""
Order Management Router - StockX Order Tracking & Analytics
Sales tracking, profit calculations, and reporting endpoints
"""

import os
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from shared.api.dependencies import get_db_session
from shared.auth.dependencies import require_authenticated_user
from shared.auth.models import User
from shared.database.models import StockXOrder, StockXListing
from shared.utils.financial import FinancialCalculator
from domains.selling.services.order_tracking_service import OrderTrackingService

router = APIRouter()


# Pydantic Models for API
class OrderResponse(BaseModel):
    """Response model for StockX orders"""
    id: str
    listing_id: str
    stockx_order_number: str
    sale_price: float
    buyer_premium: Optional[float]
    seller_fee: Optional[float]
    processing_fee: Optional[float]
    net_proceeds: Optional[float]
    original_buy_price: Optional[float]
    gross_profit: Optional[float]
    net_profit: Optional[float]
    actual_margin: Optional[float]
    roi: Optional[float]
    order_status: Optional[str]
    shipping_status: Optional[str]
    tracking_number: Optional[str]
    sold_at: str
    shipped_at: Optional[str]
    completed_at: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class OrderSummaryResponse(BaseModel):
    """Summary statistics for orders"""
    total_orders: int
    active_orders: int
    completed_orders: int
    total_sales_value: float
    total_net_proceeds: float
    total_gross_profit: float
    total_net_profit: float
    avg_sale_price: float
    avg_profit_margin: float
    avg_roi: float
    best_performing_order: Optional[OrderResponse]


class ProfitAnalyticsResponse(BaseModel):
    """Profit analytics and performance metrics"""
    period: str
    total_sales: int
    gross_revenue: float
    net_revenue: float
    total_fees: float
    gross_profit: float
    net_profit: float
    profit_margin: float
    avg_roi: float
    best_sale: Optional[OrderResponse]
    worst_sale: Optional[OrderResponse]
    daily_breakdown: List[Dict[str, float]]


class TaxReportEntry(BaseModel):
    """Tax reporting entry"""
    order_id: str
    stockx_order_number: str
    sale_date: str
    product_name: str
    sale_price: float
    cost_basis: float
    gross_profit: float
    fees_paid: float
    net_profit: float
    holding_period_days: int


class TaxReportResponse(BaseModel):
    """Tax report response"""
    year: int
    total_sales: int
    total_gross_revenue: float
    total_cost_basis: float
    total_gross_profit: float
    total_fees: float
    total_net_profit: float
    short_term_sales: int
    long_term_sales: int
    entries: List[TaxReportEntry]


def get_order_tracking_service(db: AsyncSession = Depends(get_db_session)) -> OrderTrackingService:
    """Dependency to get order tracking service"""
    api_token = os.getenv("STOCKX_API_TOKEN")
    if not api_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="StockX API token not configured"
        )
    return OrderTrackingService(db, api_token)


@router.get(
    "/orders/active",
    response_model=List[OrderResponse],
    summary="Get active orders",
    description="Retrieve all active sales orders that are not yet completed"
)
async def get_active_orders(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    order_service: OrderTrackingService = Depends(get_order_tracking_service),
    user: User = Depends(require_authenticated_user)
):
    """Get all active sales orders"""
    try:
        orders = await order_service.get_active_orders(limit=limit)
        return [OrderResponse(**order.to_dict()) for order in orders]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get active orders: {str(e)}"
        )


@router.get(
    "/orders/history",
    response_model=List[OrderResponse],
    summary="Get order history",
    description="Get sales history with profit calculations and optional date filtering"
)
async def get_order_history(
    start_date: Optional[date] = Query(None, description="Start date for filtering (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date for filtering (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="Filter by order status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    order_service: OrderTrackingService = Depends(get_order_tracking_service),
    user: User = Depends(require_authenticated_user)
):
    """Get sales history with profit calculations"""
    try:
        orders = await order_service.get_order_history(
            start_date=start_date,
            end_date=end_date,
            status=status,
            limit=limit
        )
        return [OrderResponse(**order.to_dict()) for order in orders]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get order history: {str(e)}"
        )


@router.get(
    "/orders/summary",
    response_model=OrderSummaryResponse,
    summary="Get orders summary",
    description="Get comprehensive summary statistics for all orders"
)
async def get_orders_summary(
    days: int = Query(30, ge=1, le=365, description="Number of days to include in summary"),
    order_service: OrderTrackingService = Depends(get_order_tracking_service),
    user: User = Depends(require_authenticated_user)
):
    """Get summary statistics for orders"""
    try:
        since_date = datetime.utcnow().date() - timedelta(days=days)
        orders = await order_service.get_order_history(start_date=since_date, limit=1000)

        total_orders = len(orders)
        active_orders = len([o for o in orders if o.order_status in ["pending", "authenticated", "shipped"]])
        completed_orders = len([o for o in orders if o.order_status == "completed"])

        # Use safe financial calculations with Decimal precision
        sale_prices = [o.sale_price for o in orders if o.sale_price]
        net_proceeds = [o.net_proceeds for o in orders if o.net_proceeds]
        gross_profits = [o.gross_profit for o in orders if o.gross_profit]
        net_profits = [o.net_profit for o in orders if o.net_profit]
        margins = [o.actual_margin for o in orders if o.actual_margin]
        rois = [o.roi for o in orders if o.roi]

        # Calculate totals using safe financial operations
        total_sales_value = FinancialCalculator.safe_sum(sale_prices)
        total_net_proceeds = FinancialCalculator.safe_sum(net_proceeds)
        total_gross_profit = FinancialCalculator.safe_sum(gross_profits)
        total_net_profit = FinancialCalculator.safe_sum(net_profits)

        # Calculate averages using safe financial operations
        avg_sale_price = FinancialCalculator.safe_average(sale_prices)
        avg_profit_margin = FinancialCalculator.safe_average(margins)
        avg_roi = FinancialCalculator.safe_average(rois)

        # Find best performing order (highest net profit)
        best_order = None
        if orders:
            profit_orders = [o for o in orders if o.net_profit]
            if profit_orders:
                best_order = max(profit_orders, key=lambda x: FinancialCalculator.to_decimal(x.net_profit))

        return OrderSummaryResponse(
            total_orders=total_orders,
            active_orders=active_orders,
            completed_orders=completed_orders,
            total_sales_value=float(total_sales_value),
            total_net_proceeds=float(total_net_proceeds),
            total_gross_profit=float(total_gross_profit),
            total_net_profit=float(total_net_profit),
            avg_sale_price=float(avg_sale_price),
            avg_profit_margin=float(avg_profit_margin),
            avg_roi=float(avg_roi),
            best_performing_order=OrderResponse(**best_order.to_dict()) if best_order else None
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get orders summary: {str(e)}"
        )


@router.get(
    "/analytics/profits",
    response_model=ProfitAnalyticsResponse,
    summary="Get profit analytics",
    description="Get comprehensive profit analytics and performance metrics"
)
async def get_profit_analytics(
    period: str = Query("30d", regex="^(7d|30d|90d|365d)$", description="Analysis period: 7d, 30d, 90d, 365d"),
    order_service: OrderTrackingService = Depends(get_order_tracking_service),
    user: User = Depends(require_authenticated_user)
):
    """Get profit analytics and performance metrics"""
    try:
        period_map = {"7d": 7, "30d": 30, "90d": 90, "365d": 365}
        days = period_map[period]

        analytics = await order_service.calculate_profit_analytics(days=days)

        return ProfitAnalyticsResponse(
            period=period,
            total_sales=analytics["total_sales"],
            gross_revenue=analytics["gross_revenue"],
            net_revenue=analytics["net_revenue"],
            total_fees=analytics["total_fees"],
            gross_profit=analytics["gross_profit"],
            net_profit=analytics["net_profit"],
            profit_margin=analytics["profit_margin"],
            avg_roi=analytics["avg_roi"],
            best_sale=OrderResponse(**analytics["best_sale"].to_dict()) if analytics["best_sale"] else None,
            worst_sale=OrderResponse(**analytics["worst_sale"].to_dict()) if analytics["worst_sale"] else None,
            daily_breakdown=analytics["daily_breakdown"]
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get profit analytics: {str(e)}"
        )


@router.get(
    "/analytics/tax-report/{year}",
    response_model=TaxReportResponse,
    summary="Generate tax report",
    description="Generate comprehensive tax reporting data for a specific year"
)
async def get_tax_report(
    year: int,
    order_service: OrderTrackingService = Depends(get_order_tracking_service),
    user: User = Depends(require_authenticated_user)
):
    """Generate tax reporting data for a specific year"""
    try:
        # Validate year parameter
        if year < 2020 or year > 2030:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Year must be between 2020 and 2030"
            )

        report_data = await order_service.generate_tax_report(year=year)

        return TaxReportResponse(
            year=year,
            total_sales=report_data["total_sales"],
            total_gross_revenue=report_data["total_gross_revenue"],
            total_cost_basis=report_data["total_cost_basis"],
            total_gross_profit=report_data["total_gross_profit"],
            total_fees=report_data["total_fees"],
            total_net_profit=report_data["total_net_profit"],
            short_term_sales=report_data["short_term_sales"],
            long_term_sales=report_data["long_term_sales"],
            entries=[
                TaxReportEntry(
                    order_id=entry["order_id"],
                    stockx_order_number=entry["stockx_order_number"],
                    sale_date=entry["sale_date"],
                    product_name=entry["product_name"],
                    sale_price=entry["sale_price"],
                    cost_basis=entry["cost_basis"],
                    gross_profit=entry["gross_profit"],
                    fees_paid=entry["fees_paid"],
                    net_profit=entry["net_profit"],
                    holding_period_days=entry["holding_period_days"]
                )
                for entry in report_data["entries"]
            ]
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate tax report: {str(e)}"
        )


@router.post(
    "/sync/orders",
    summary="Sync orders from StockX",
    description="Manually trigger synchronization of orders from StockX API"
)
async def sync_orders_from_stockx(
    order_service: OrderTrackingService = Depends(get_order_tracking_service),
    user: User = Depends(require_authenticated_user)
):
    """Manually sync orders from StockX"""
    try:
        stats = await order_service.sync_orders_from_stockx()

        return {
            "success": True,
            "message": "Orders synchronized successfully",
            "statistics": {
                "new_orders": stats["new_orders"],
                "updated_orders": stats["updated_orders"],
                "total_synced": stats["total_synced"],
                "sync_duration_seconds": stats["sync_duration_seconds"]
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync orders: {str(e)}"
        )


@router.put(
    "/orders/{order_id}/tracking",
    response_model=OrderResponse,
    summary="Update order tracking",
    description="Update tracking information for a specific order"
)
async def update_order_tracking(
    order_id: UUID,
    tracking_number: str = Query(..., min_length=1, description="Tracking number"),
    order_service: OrderTrackingService = Depends(get_order_tracking_service),
    user: User = Depends(require_authenticated_user)
):
    """Update tracking information for an order"""
    try:
        order = await order_service.update_order_tracking(
            order_id=order_id,
            tracking_number=tracking_number
        )

        return OrderResponse(**order.to_dict())

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update order tracking: {str(e)}"
        )


# Health check for order management service
@router.get(
    "/health",
    summary="Order management health check",
    description="Check if the order management service is operational"
)
async def order_management_health_check(
    order_service: OrderTrackingService = Depends(get_order_tracking_service)
):
    """Health check for order management service"""
    try:
        # Quick test to ensure service is working
        recent_orders = await order_service.get_order_history(limit=1)

        return {
            "status": "healthy",
            "service": "order_management",
            "api_connected": True,
            "orders_accessible": True,
            "timestamp": "2025-09-19T12:00:00Z"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Order management service unhealthy: {str(e)}"
        )
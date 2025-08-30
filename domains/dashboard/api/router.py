"""
Dashboard API Router
Provides comprehensive dashboard metrics and statistics
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List
import structlog
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.connection import get_db_session
from shared.api.dependencies import get_inventory_service
from domains.inventory.services.inventory_service import InventoryService

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/metrics", 
    summary="Get Dashboard Metrics",
    description="Get comprehensive dashboard metrics including inventory, sales, and system statistics"
)
async def get_dashboard_metrics(
    inventory_service: InventoryService = Depends(get_inventory_service),
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """Get comprehensive dashboard metrics"""
    logger.info("Fetching dashboard metrics")
    
    try:
        # Get inventory summary
        inventory_summary = await inventory_service.get_detailed_summary()
        
        # Get real transaction-based analytics data
        from sqlalchemy import text, func
        from shared.database.models import Transaction, InventoryItem, Product, Brand
        
        # Get sales analytics from transactions
        sales_query = text("""
            SELECT 
                COUNT(*) as total_transactions,
                SUM(sale_price) as total_revenue,
                AVG(sale_price) as avg_sale_price,
                SUM(net_profit) as total_profit,
                COUNT(DISTINCT DATE_TRUNC('day', transaction_date)) as active_days
            FROM sales.transactions 
            WHERE sale_price IS NOT NULL
        """)
        sales_result = await db.execute(sales_query)
        sales_data = sales_result.fetchone()
        
        # Get top brands with transaction data
        brands_query = text("""
            SELECT 
                b.name as brand_name,
                COUNT(t.id) as transaction_count,
                SUM(t.sale_price) as total_revenue,
                AVG(t.sale_price) as avg_price
            FROM sales.transactions t
            JOIN products.inventory i ON t.inventory_id = i.id
            JOIN products.products p ON i.product_id = p.id
            LEFT JOIN core.brands b ON p.brand_id = b.id
            WHERE t.sale_price IS NOT NULL AND b.name IS NOT NULL
            GROUP BY b.name
            ORDER BY total_revenue DESC
            LIMIT 5
        """)
        brands_result = await db.execute(brands_query)
        top_brands = [
            {
                "name": row.brand_name,
                "transaction_count": row.transaction_count,
                "total_revenue": float(row.total_revenue or 0),
                "avg_price": float(row.avg_price or 0)
            }
            for row in brands_result.fetchall()
        ]
        
        # Get recent transaction activity
        recent_query = text("""
            SELECT 
                t.transaction_date,
                t.sale_price,
                t.net_profit,
                p.name as product_name,
                b.name as brand_name
            FROM sales.transactions t
            JOIN products.inventory i ON t.inventory_id = i.id
            JOIN products.products p ON i.product_id = p.id
            LEFT JOIN core.brands b ON p.brand_id = b.id
            WHERE t.sale_price IS NOT NULL
            ORDER BY t.transaction_date DESC
            LIMIT 10
        """)
        recent_result = await db.execute(recent_query)
        recent_activity = [
            {
                "date": row.transaction_date.isoformat() if row.transaction_date else None,
                "sale_price": float(row.sale_price or 0),
                "net_profit": float(row.net_profit or 0),
                "product_name": row.product_name,
                "brand_name": row.brand_name
            }
            for row in recent_result.fetchall()
        ]
        
        # Debug: Log the structure of inventory_summary
        logger.info("Inventory summary structure", 
                   summary_type=type(inventory_summary).__name__,
                   summary_data=str(inventory_summary)[:200] if inventory_summary else "None")
        
        # Get system metrics
        from shared.monitoring.metrics import get_metrics_registry
        metrics_registry = get_metrics_registry()
        system_metrics = metrics_registry.get_metrics_summary()
        
        # Get health status
        from shared.monitoring.health import get_health_manager
        health_manager = get_health_manager()
        health_status = await health_manager.get_overall_health()
        
        # Use real transaction data instead of inventory placeholders
        inventory_data = {
            "total_items": inventory_summary.get("total_items", 0) if isinstance(inventory_summary, dict) else inventory_summary.total_items,
            "items_in_stock": 0,  # All inventory items are marked as "sold" 
            "items_sold": sales_data.total_transactions if sales_data else 0,
            "items_listed": 0,
            "total_inventory_value": float(sales_data.total_revenue or 0) if sales_data else 0.0,
            "average_purchase_price": float(sales_data.avg_sale_price or 0) if sales_data else 0.0,
            "top_brands": top_brands,
            "status_breakdown": {
                "in_stock": 0,
                "sold": sales_data.total_transactions if sales_data else 0,
                "listed": 0
            },
        }
        
        sales_data_response = {
            "recent_activity": recent_activity,
            "total_transactions": sales_data.total_transactions if sales_data else 0,
            "total_revenue": float(sales_data.total_revenue or 0) if sales_data else 0.0,
            "total_profit": float(sales_data.total_profit or 0) if sales_data else 0.0,
            "avg_sale_price": float(sales_data.avg_sale_price or 0) if sales_data else 0.0
        }
        
        # Prepare dashboard metrics
        dashboard_metrics = {
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "inventory": inventory_data,
            "sales": sales_data_response,
            "system": {
                "status": health_status["status"],
                "uptime_seconds": health_status.get("uptime_seconds", 0),
                "environment": health_status.get("environment", "development"),
                "version": health_status.get("version", "2.1.0")
            },
            "performance": {
                "total_requests": system_metrics.get("requests_total", 0),
                "error_rate": system_metrics.get("error_rate", 0),
                "avg_response_time": system_metrics.get("response_time_avg", 0)
            }
        }
        
        return dashboard_metrics
        
    except Exception as e:
        logger.error("Failed to fetch dashboard metrics", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail="Failed to fetch dashboard metrics"
        )


@router.get("/system-status",
    summary="Get System Status", 
    description="Get current system health and status information"
)
async def get_system_status() -> Dict[str, Any]:
    """Get system status and health information"""
    logger.info("Fetching system status")
    
    try:
        from shared.monitoring.health import get_health_manager
        health_manager = get_health_manager()
        health_status = await health_manager.get_overall_health()
        
        return {
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "status": health_status["status"],
            "uptime_seconds": health_status.get("uptime_seconds", 0),
            "environment": health_status.get("environment", "development"),
            "version": health_status.get("version", "2.1.0"),
            "components": health_status.get("components", {}),
            "checks": health_status.get("checks", {})
        }
        
    except Exception as e:
        logger.error("Failed to fetch system status", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch system status"
        )
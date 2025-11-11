"""
Dashboard API Router
Provides comprehensive dashboard metrics and statistics
"""

from datetime import datetime
from typing import Any, Dict

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from domains.inventory.services.inventory_service import InventoryService
from shared.api.dependencies import get_inventory_service
from shared.database.connection import get_db_session

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get(
    "/metrics",
    summary="Get Dashboard Metrics",
    description="Get comprehensive dashboard metrics including inventory, sales, and system statistics",
)
async def get_dashboard_metrics(
    inventory_service: InventoryService = Depends(get_inventory_service),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Get comprehensive dashboard metrics"""
    logger.info("Fetching dashboard metrics")

    # Check cache first
    from shared.caching.dashboard_cache import get_dashboard_cache

    cache = get_dashboard_cache()
    cache_key = "dashboard_metrics"

    cached_data = await cache.get(cache_key)
    if cached_data:
        logger.info("Dashboard metrics served from cache")
        return cached_data

    try:
        # Single optimized query for all dashboard metrics using CTEs
        from sqlalchemy import text

        dashboard_query = text(
            """
            WITH 
            -- Sales summary statistics
            sales_summary AS (
                SELECT
                    COUNT(*) as total_transactions,
                    SUM(sale_price) as total_revenue,
                    AVG(sale_price) as avg_sale_price,
                    SUM(net_profit) as total_profit,
                    COUNT(DISTINCT DATE_TRUNC('day', transaction_date)) as active_days
                FROM sales.order
                WHERE sale_price IS NOT NULL
            ),
            -- Top brands by revenue
            top_brands AS (
                SELECT
                    b.name as brand_name,
                    COUNT(t.id) as transaction_count,
                    SUM(t.sale_price) as total_revenue,
                    AVG(t.sale_price) as avg_price,
                    ROW_NUMBER() OVER (ORDER BY SUM(t.sale_price) DESC) as rn
                FROM sales.order t
                JOIN inventory.stock i ON t.inventory_item_id = i.id
                JOIN catalog.product p ON i.product_id = p.id
                LEFT JOIN catalog.brand b ON p.brand_id = b.id
                WHERE t.sale_price IS NOT NULL AND b.name IS NOT NULL
                GROUP BY b.name
            ),
            -- Recent activity
            recent_activity AS (
                SELECT
                    t.transaction_date,
                    t.sale_price,
                    t.net_profit,
                    p.name as product_name,
                    b.name as brand_name,
                    ROW_NUMBER() OVER (ORDER BY t.transaction_date DESC) as rn
                FROM sales.order t
                JOIN inventory.stock i ON t.inventory_item_id = i.id
                JOIN catalog.product p ON i.product_id = p.id
                LEFT JOIN catalog.brand b ON p.brand_id = b.id
                WHERE t.sale_price IS NOT NULL
            ),
            -- Inventory counts
            inventory_summary AS (
                SELECT 
                    COUNT(*) as total_items,
                    COUNT(CASE WHEN status = 'in_stock' THEN 1 END) as in_stock,
                    COUNT(CASE WHEN status = 'sold' THEN 1 END) as sold,
                    COUNT(CASE WHEN status = 'listed_stockx' THEN 1 END) as listed
                FROM inventory.stock
            )
            -- Main query combining all data
            SELECT 
                'sales' as data_type,
                s.total_transactions,
                s.total_revenue,
                s.avg_sale_price,
                s.total_profit,
                s.active_days,
                NULL::text as brand_name,
                NULL::int as transaction_count,
                NULL::numeric as brand_revenue,
                NULL::numeric as brand_avg_price,
                NULL::timestamp as activity_date,
                NULL::numeric as activity_sale_price,
                NULL::numeric as activity_net_profit,
                NULL::text as activity_product_name,
                NULL::text as activity_brand_name,
                NULL::int as total_items,
                NULL::int as in_stock,
                NULL::int as sold,
                NULL::int as listed
            FROM sales_summary s
            
            UNION ALL
            
            SELECT 
                'brand' as data_type,
                NULL, NULL, NULL, NULL, NULL,
                tb.brand_name,
                tb.transaction_count,
                tb.total_revenue,
                tb.avg_price,
                NULL, NULL, NULL, NULL, NULL,
                NULL, NULL, NULL, NULL
            FROM top_brands tb
            WHERE tb.rn <= 5
            
            UNION ALL
            
            SELECT 
                'activity' as data_type,
                NULL, NULL, NULL, NULL, NULL,
                NULL, NULL, NULL, NULL,
                ra.transaction_date,
                ra.sale_price,
                ra.net_profit,
                ra.product_name,
                ra.brand_name,
                NULL, NULL, NULL, NULL
            FROM recent_activity ra
            WHERE ra.rn <= 10
            
            UNION ALL
            
            SELECT 
                'inventory' as data_type,
                NULL, NULL, NULL, NULL, NULL,
                NULL, NULL, NULL, NULL,
                NULL, NULL, NULL, NULL, NULL,
                inv.total_items,
                inv.in_stock,
                inv.sold,
                inv.listed
            FROM inventory_summary inv
            
            ORDER BY data_type, brand_name, activity_date DESC
            """
        )

        result = await db.execute(dashboard_query)
        rows = result.fetchall()

        # Parse the unified result
        sales_data = None
        top_brands = []
        recent_activity = []
        inventory_data = None

        for row in rows:
            if row.data_type == "sales":
                sales_data = row
            elif row.data_type == "brand":
                top_brands.append(
                    {
                        "name": row.brand_name,
                        "transaction_count": row.transaction_count,
                        "total_revenue": float(row.brand_revenue or 0),
                        "avg_price": float(row.brand_avg_price or 0),
                    }
                )
            elif row.data_type == "activity":
                recent_activity.append(
                    {
                        "date": row.activity_date.isoformat() if row.activity_date else None,
                        "sale_price": float(row.activity_sale_price or 0),
                        "net_profit": float(row.activity_net_profit or 0),
                        "product_name": row.activity_product_name,
                        "brand_name": row.activity_brand_name,
                    }
                )
            elif row.data_type == "inventory":
                inventory_data = row

        # Get system metrics (simplified - no separate DB calls)
        from shared.monitoring.health import get_health_manager
        from shared.monitoring.metrics import get_metrics_registry

        metrics_registry = get_metrics_registry()
        system_metrics = metrics_registry.get_metrics_summary()

        health_manager = get_health_manager()
        health_status = await health_manager.get_overall_health()

        # Build response from unified query result
        inventory_response = {
            "total_items": inventory_data.total_items if inventory_data else 0,
            "items_in_stock": inventory_data.in_stock if inventory_data else 0,
            "items_sold": inventory_data.sold if inventory_data else 0,
            "items_listed": inventory_data.listed if inventory_data else 0,
            "total_inventory_value": float(sales_data.total_revenue or 0) if sales_data else 0.0,
            "average_purchase_price": float(sales_data.avg_sale_price or 0) if sales_data else 0.0,
            "top_brands": top_brands,
            "status_breakdown": {
                "in_stock": inventory_data.in_stock if inventory_data else 0,
                "sold": inventory_data.sold if inventory_data else 0,
                "listed": inventory_data.listed if inventory_data else 0,
            },
        }

        sales_data_response = {
            "recent_activity": recent_activity,
            "total_transactions": sales_data.total_transactions if sales_data else 0,
            "total_revenue": float(sales_data.total_revenue or 0) if sales_data else 0.0,
            "total_profit": float(sales_data.total_profit or 0) if sales_data else 0.0,
            "avg_sale_price": float(sales_data.avg_sale_price or 0) if sales_data else 0.0,
        }

        # Prepare dashboard metrics
        dashboard_metrics = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "inventory": inventory_response,
            "sales": sales_data_response,
            "system": {
                "status": health_status["status"],
                "uptime_seconds": health_status.get("uptime_seconds", 0),
                "environment": health_status.get("environment", "development"),
                "version": health_status.get("version", "2.1.0"),
            },
            "performance": {
                "total_requests": system_metrics.get("requests_total", 0),
                "error_rate": system_metrics.get("error_rate", 0),
                "avg_response_time": system_metrics.get("response_time_avg", 0),
            },
        }

        # Cache the result for 2 minutes (120 seconds)
        await cache.set(cache_key, dashboard_metrics, ttl=120)
        logger.info("Dashboard metrics cached for 2 minutes")

        return dashboard_metrics

    except Exception as e:
        logger.error("Failed to fetch dashboard metrics", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard metrics")


@router.get(
    "/system-status",
    summary="Get System Status",
    description="Get current system health and status information",
)
async def get_system_status() -> Dict[str, Any]:
    """Get system status and health information"""
    logger.info("Fetching system status")

    try:
        from shared.monitoring.health import get_health_manager

        health_manager = get_health_manager()
        health_status = await health_manager.get_overall_health()

        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": health_status["status"],
            "uptime_seconds": health_status.get("uptime_seconds", 0),
            "environment": health_status.get("environment", "development"),
            "version": health_status.get("version", "2.1.0"),
            "components": health_status.get("components", {}),
            "checks": health_status.get("checks", {}),
        }

    except Exception as e:
        logger.error("Failed to fetch system status", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch system status")

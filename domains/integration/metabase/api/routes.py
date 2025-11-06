"""
Metabase Integration API Endpoints
==================================

REST API for managing Metabase materialized views and dashboards.
"""

from typing import Dict, List

from fastapi import APIRouter, HTTPException, BackgroundTasks, status

from ..services.view_manager import MetabaseViewManager
from ..services.dashboard_service import MetabaseDashboardService
from ..services.sync_service import MetabaseSyncService
from ..schemas.metabase_models import MaterializedViewStatus, RefreshJobStatus, MetabaseDashboard
from ..config.materialized_views import RefreshStrategy

router = APIRouter(prefix="/metabase", tags=["Metabase Integration"])


@router.post("/views/create", status_code=status.HTTP_201_CREATED)
async def create_all_views(drop_existing: bool = False) -> Dict[str, bool]:
    """
    Create all Metabase materialized views.

    Args:
        drop_existing: Drop existing views before creating

    Returns:
        Dict mapping view names to success status
    """
    view_manager = MetabaseViewManager()
    results = await view_manager.create_all_views(drop_existing=drop_existing)
    return results


@router.post("/views/{view_name}/refresh")
async def refresh_view(
    view_name: str, background_tasks: BackgroundTasks = None
) -> RefreshJobStatus:
    """
    Manually refresh a specific materialized view.

    Args:
        view_name: Name of the view to refresh
        background_tasks: Optional background task execution

    Returns:
        RefreshJobStatus with timing information
    """
    view_manager = MetabaseViewManager()

    # For long-running refreshes, use background tasks
    if background_tasks:
        background_tasks.add_task(view_manager.refresh_view, view_name)
        return RefreshJobStatus(view_name=view_name, status="pending", started_at=None)

    return await view_manager.refresh_view(view_name)


@router.post("/views/refresh-by-strategy/{strategy}")
async def refresh_by_strategy(strategy: RefreshStrategy) -> List[RefreshJobStatus]:
    """
    Refresh all views with a specific refresh strategy.

    Args:
        strategy: RefreshStrategy (hourly, daily, weekly)

    Returns:
        List of RefreshJobStatus for each view
    """
    view_manager = MetabaseViewManager()
    return await view_manager.refresh_by_strategy(strategy)


@router.get("/views/status")
async def get_all_view_statuses() -> List[MaterializedViewStatus]:
    """
    Get status of all materialized views.

    Returns:
        List of MaterializedViewStatus with row counts and indexes
    """
    view_manager = MetabaseViewManager()
    return await view_manager.get_all_view_statuses()


@router.get("/views/{view_name}/status")
async def get_view_status(view_name: str) -> MaterializedViewStatus:
    """
    Get status of a specific materialized view.

    Args:
        view_name: Name of the view

    Returns:
        MaterializedViewStatus or 404 if not found
    """
    view_manager = MetabaseViewManager()
    status = await view_manager.get_view_status(view_name)

    if not status or not status.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"View '{view_name}' not found"
        )

    return status


@router.delete("/views/{view_name}")
async def drop_view(view_name: str, cascade: bool = True) -> Dict[str, str]:
    """
    Drop a materialized view.

    Args:
        view_name: Name of the view to drop
        cascade: Drop dependent objects as well

    Returns:
        Success message
    """
    view_manager = MetabaseViewManager()
    success = await view_manager.drop_view(view_name, cascade=cascade)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to drop view '{view_name}'",
        )

    return {"message": f"View '{view_name}' dropped successfully"}


@router.post("/sync/all")
async def sync_all_views() -> Dict[str, RefreshJobStatus]:
    """
    Sync all materialized views regardless of refresh strategy.

    Returns:
        Dict mapping view names to refresh job statuses
    """
    sync_service = MetabaseSyncService()
    return await sync_service.sync_all()


@router.post("/sync/on-order-event")
async def sync_on_order_event() -> List[RefreshJobStatus]:
    """
    Sync views affected by order data changes.

    Returns:
        List of RefreshJobStatus for affected views
    """
    sync_service = MetabaseSyncService()
    return await sync_service.sync_on_order_event()


@router.post("/sync/on-inventory-event")
async def sync_on_inventory_event() -> List[RefreshJobStatus]:
    """
    Sync views affected by inventory data changes.

    Returns:
        List of RefreshJobStatus for affected views
    """
    sync_service = MetabaseSyncService()
    return await sync_service.sync_on_inventory_event()


@router.get("/sync/status")
async def get_sync_status() -> Dict:
    """
    Get overall sync status for monitoring.

    Returns:
        Sync status information including view counts and row counts
    """
    sync_service = MetabaseSyncService()
    return await sync_service.get_sync_status()


@router.get("/dashboards")
async def get_all_dashboards() -> Dict[str, MetabaseDashboard]:
    """
    Get all pre-configured dashboard templates.

    Returns:
        Dict mapping dashboard names to MetabaseDashboard configurations
    """
    dashboard_service = MetabaseDashboardService()
    return dashboard_service.generate_all_dashboards()


@router.get("/dashboards/{dashboard_name}")
async def get_dashboard(dashboard_name: str) -> MetabaseDashboard:
    """
    Get a specific dashboard configuration.

    Args:
        dashboard_name: Name of the dashboard

    Returns:
        MetabaseDashboard configuration or 404 if not found
    """
    dashboard_service = MetabaseDashboardService()
    dashboard_service.generate_all_dashboards()

    dashboard = dashboard_service.get_dashboard(dashboard_name)
    if not dashboard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Dashboard '{dashboard_name}' not found"
        )

    return dashboard


@router.post("/setup/refresh-schedule")
async def setup_refresh_schedule() -> Dict[str, str]:
    """
    Setup automatic refresh schedules using pg_cron.

    Requires:
        - PostgreSQL pg_cron extension installed
        - Superuser privileges

    Returns:
        Dict mapping view names to cron job schedule types
    """
    view_manager = MetabaseViewManager()
    return await view_manager.setup_refresh_schedule()

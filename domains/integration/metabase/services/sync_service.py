"""
Metabase Sync Service
====================

Synchronizes SoleFlipper database changes with Metabase materialized views.
"""

import logging
from datetime import datetime
from typing import Dict, List

from .view_manager import MetabaseViewManager
from ..config.materialized_views import RefreshStrategy
from ..schemas.metabase_models import RefreshJobStatus

logger = logging.getLogger(__name__)


class MetabaseSyncService:
    """
    Manages synchronization between SoleFlipper database and Metabase.

    Features:
    - Scheduled refresh of materialized views
    - Event-driven refresh on data changes
    - Performance monitoring
    - Error handling and retry logic
    """

    def __init__(self):
        self.view_manager = MetabaseViewManager()

    async def sync_all(self) -> Dict[str, RefreshJobStatus]:
        """
        Sync all materialized views regardless of refresh strategy.

        Returns:
            Dict mapping view names to refresh job statuses
        """
        logger.info("Starting full sync of all Metabase views")

        results = {}
        for view_config in self.view_manager.config.get_all_views():
            view_name = view_config["name"]
            status = await self.view_manager.refresh_view(view_name)
            results[view_name] = status

        success_count = sum(1 for s in results.values() if s.status == "completed")
        logger.info(f"Sync completed: {success_count}/{len(results)} views refreshed successfully")

        return results

    async def sync_by_strategy(self, strategy: RefreshStrategy) -> List[RefreshJobStatus]:
        """
        Sync views with specific refresh strategy.

        Args:
            strategy: RefreshStrategy (HOURLY, DAILY, WEEKLY)

        Returns:
            List of RefreshJobStatus
        """
        logger.info(f"Syncing {strategy.value} views")
        return await self.view_manager.refresh_by_strategy(strategy)

    async def sync_on_order_event(self) -> List[RefreshJobStatus]:
        """
        Sync views when order data changes.
        Should be called when orders are created/updated.

        Returns:
            List of RefreshJobStatus for affected views
        """
        logger.info("Syncing views after order event")

        # Refresh views that depend on orders table
        affected_views = [
            "metabase_executive_metrics",
            "metabase_platform_performance",
            "metabase_product_performance",
        ]

        results = []
        for view_name in affected_views:
            status = await self.view_manager.refresh_view(view_name)
            results.append(status)

        return results

    async def sync_on_inventory_event(self) -> List[RefreshJobStatus]:
        """
        Sync views when inventory data changes.
        Should be called when inventory is added/updated.

        Returns:
            List of RefreshJobStatus for affected views
        """
        logger.info("Syncing views after inventory event")

        # Refresh views that depend on inventory table
        affected_views = [
            "metabase_inventory_status",
            "metabase_product_performance",
            "metabase_supplier_performance",
        ]

        results = []
        for view_name in affected_views:
            status = await self.view_manager.refresh_view(view_name)
            results.append(status)

        return results

    async def get_sync_status(self) -> Dict[str, any]:
        """
        Get overall sync status for monitoring.

        Returns:
            Dict with sync status information
        """
        view_statuses = await self.view_manager.get_all_view_statuses()

        total_views = len(view_statuses)
        existing_views = sum(1 for v in view_statuses if v.exists)
        total_rows = sum(v.row_count or 0 for v in view_statuses)

        return {
            "total_views": total_views,
            "existing_views": existing_views,
            "missing_views": total_views - existing_views,
            "total_rows": total_rows,
            "last_check": datetime.utcnow(),
            "views": [
                {
                    "name": v.view_name,
                    "exists": v.exists,
                    "rows": v.row_count,
                    "indexes": len(v.indexes),
                }
                for v in view_statuses
            ],
        }

"""
Metabase View Manager Service
=============================

Manages creation, refresh, and maintenance of materialized views for Metabase.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.connection import DatabaseManager
from ..config.materialized_views import MetabaseViewConfig, RefreshStrategy
from ..schemas.metabase_models import MaterializedViewStatus, RefreshJobStatus

logger = logging.getLogger(__name__)


class MetabaseViewManager:
    """
    Manages materialized views for Metabase dashboards.

    Features:
    - Create/drop materialized views
    - Refresh views with different strategies
    - Monitor view status and performance
    - Automatic index creation
    """

    def __init__(self):
        self.db = DatabaseManager()
        self.config = MetabaseViewConfig()

    async def create_all_views(self, drop_existing: bool = False) -> Dict[str, bool]:
        """
        Create all materialized views for Metabase.

        Args:
            drop_existing: Drop existing views before creating

        Returns:
            Dict mapping view names to success status
        """
        logger.info("Creating all Metabase materialized views")

        results = {}
        async with self.db.get_session() as session:
            for view_config in self.config.get_all_views():
                try:
                    success = await self._create_view(
                        session,
                        view_config,
                        drop_existing
                    )
                    results[view_config["name"]] = success

                    if success:
                        logger.info(f"✓ Created view: {view_config['name']}")
                    else:
                        logger.error(f"✗ Failed to create view: {view_config['name']}")

                except Exception as e:
                    logger.error(f"Error creating view {view_config['name']}: {e}")
                    results[view_config["name"]] = False

        return results

    async def _create_view(
        self,
        session: AsyncSession,
        view_config: Dict,
        drop_existing: bool
    ) -> bool:
        """Create single materialized view with indexes"""
        try:
            view_name = view_config["name"]

            # Drop existing if requested
            if drop_existing:
                await session.execute(
                    text(f"DROP MATERIALIZED VIEW IF EXISTS analytics.{view_name} CASCADE")
                )

            # Create materialized view
            create_sql = f"""
                CREATE MATERIALIZED VIEW analytics.{view_name} AS
                {view_config['sql']}
            """
            await session.execute(text(create_sql))

            # Create indexes
            for index_sql in view_config.get("indexes", []):
                await session.execute(text(index_sql))

            await session.commit()
            return True

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to create view {view_config['name']}: {e}")
            return False

    async def refresh_view(self, view_name: str) -> RefreshJobStatus:
        """
        Manually refresh a specific materialized view.

        Args:
            view_name: Name of the view to refresh

        Returns:
            RefreshJobStatus with timing and status info
        """
        logger.info(f"Refreshing materialized view: {view_name}")

        job_status = RefreshJobStatus(
            view_name=view_name,
            status="running",
            started_at=datetime.utcnow()
        )

        try:
            async with self.db.get_session() as session:
                # Refresh materialized view
                await session.execute(
                    text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.{view_name}")
                )
                await session.commit()

                job_status.status = "completed"
                job_status.completed_at = datetime.utcnow()
                job_status.duration_seconds = (
                    job_status.completed_at - job_status.started_at
                ).total_seconds()

                logger.info(
                    f"✓ Refreshed {view_name} in {job_status.duration_seconds:.2f}s"
                )

        except Exception as e:
            job_status.status = "failed"
            job_status.error_message = str(e)
            job_status.completed_at = datetime.utcnow()
            logger.error(f"Failed to refresh {view_name}: {e}")

        return job_status

    async def refresh_by_strategy(self, strategy: RefreshStrategy) -> List[RefreshJobStatus]:
        """
        Refresh all views with a specific refresh strategy.

        Args:
            strategy: RefreshStrategy (HOURLY, DAILY, WEEKLY)

        Returns:
            List of RefreshJobStatus for each view
        """
        logger.info(f"Refreshing all {strategy} views")

        views = self.config.get_views_by_refresh_strategy(strategy)
        results = []

        for view_config in views:
            status = await self.refresh_view(view_config["name"])
            results.append(status)

        return results

    async def get_view_status(self, view_name: str) -> Optional[MaterializedViewStatus]:
        """
        Get current status of a materialized view.

        Args:
            view_name: Name of the view

        Returns:
            MaterializedViewStatus or None if not found
        """
        async with self.db.get_session() as session:
            # Check if view exists
            result = await session.execute(text("""
                SELECT
                    schemaname,
                    matviewname,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||matviewname)) as size
                FROM pg_matviews
                WHERE schemaname = 'analytics' AND matviewname = :view_name
            """), {"view_name": view_name})

            row = result.fetchone()
            if not row:
                return MaterializedViewStatus(
                    view_name=view_name,
                    exists=False
                )

            # Get row count
            count_result = await session.execute(
                text(f"SELECT COUNT(*) FROM analytics.{view_name}")
            )
            row_count = count_result.fetchone()[0]

            # Get indexes
            indexes_result = await session.execute(text("""
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'analytics' AND tablename = :view_name
            """), {"view_name": view_name})

            indexes = [r[0] for r in indexes_result.fetchall()]

            return MaterializedViewStatus(
                view_name=view_name,
                exists=True,
                row_count=row_count,
                size_bytes=None,  # Would need to parse pg_size_pretty
                indexes=indexes
            )

    async def get_all_view_statuses(self) -> List[MaterializedViewStatus]:
        """Get status of all configured materialized views"""
        statuses = []

        for view_config in self.config.get_all_views():
            status = await self.get_view_status(view_config["name"])
            if status:
                statuses.append(status)

        return statuses

    async def drop_view(self, view_name: str, cascade: bool = True) -> bool:
        """
        Drop a materialized view.

        Args:
            view_name: Name of the view to drop
            cascade: Drop dependent objects as well

        Returns:
            True if successful
        """
        try:
            async with self.db.get_session() as session:
                cascade_clause = "CASCADE" if cascade else ""
                await session.execute(
                    text(f"DROP MATERIALIZED VIEW IF EXISTS analytics.{view_name} {cascade_clause}")
                )
                await session.commit()
                logger.info(f"✓ Dropped view: {view_name}")
                return True

        except Exception as e:
            logger.error(f"Failed to drop view {view_name}: {e}")
            return False

    async def setup_refresh_schedule(self) -> Dict[str, str]:
        """
        Setup automatic refresh schedules using pg_cron.
        Requires pg_cron extension to be installed.

        Returns:
            Dict mapping view names to cron job IDs
        """
        logger.info("Setting up automatic refresh schedules with pg_cron")

        schedules = {}
        async with self.db.get_session() as session:
            # Hourly views - Every hour at :00
            for view in self.config.get_views_by_refresh_strategy(RefreshStrategy.HOURLY):
                try:
                    await session.execute(text("""
                        SELECT cron.schedule(
                            :job_name,
                            '0 * * * *',
                            $$REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.{view_name}$$
                        )
                    """.format(view_name=view["name"])), {
                        "job_name": f"refresh_{view['name']}"
                    })
                    schedules[view["name"]] = "hourly"
                    logger.info(f"✓ Scheduled hourly refresh for {view['name']}")
                except Exception as e:
                    logger.warning(f"Could not schedule {view['name']}: {e}")

            # Daily views - Every day at 2 AM
            for view in self.config.get_views_by_refresh_strategy(RefreshStrategy.DAILY):
                try:
                    await session.execute(text("""
                        SELECT cron.schedule(
                            :job_name,
                            '0 2 * * *',
                            $$REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.{view_name}$$
                        )
                    """.format(view_name=view["name"])), {
                        "job_name": f"refresh_{view['name']}"
                    })
                    schedules[view["name"]] = "daily"
                    logger.info(f"✓ Scheduled daily refresh for {view['name']}")
                except Exception as e:
                    logger.warning(f"Could not schedule {view['name']}: {e}")

            # Weekly views - Every Monday at 3 AM
            for view in self.config.get_views_by_refresh_strategy(RefreshStrategy.WEEKLY):
                try:
                    await session.execute(text("""
                        SELECT cron.schedule(
                            :job_name,
                            '0 3 * * 1',
                            $$REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.{view_name}$$
                        )
                    """.format(view_name=view["name"])), {
                        "job_name": f"refresh_{view['name']}"
                    })
                    schedules[view["name"]] = "weekly"
                    logger.info(f"✓ Scheduled weekly refresh for {view['name']}")
                except Exception as e:
                    logger.warning(f"Could not schedule {view['name']}: {e}")

            await session.commit()

        return schedules

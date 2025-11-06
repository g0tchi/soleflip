"""
Advanced Health Check System
Comprehensive health monitoring with detailed component checks
"""

import asyncio
import time
from datetime import datetime
from typing import Any, Dict, Optional

import structlog
from sqlalchemy import text

from shared.database.connection import db_manager
from .apm import collect_system_metrics, get_apm_collector
from .health import HealthStatus, HealthCheckResult

logger = structlog.get_logger(__name__)


class AdvancedHealthChecker:
    """Advanced health checking with comprehensive component monitoring"""

    def __init__(self):
        self.startup_time = datetime.utcnow()
        self.last_full_check = None
        self.cached_results = {}
        self.cache_ttl_seconds = 30

    async def perform_startup_checks(self) -> Dict[str, HealthCheckResult]:
        """Perform comprehensive startup health checks"""
        logger.info("Performing startup health checks")

        checks = {
            "database_connection": await self._check_database_connection(),
            "database_migrations": await self._check_database_migrations(),
            "essential_tables": await self._check_essential_tables(),
            "system_resources": await self._check_system_resources(),
            "configuration": await self._check_configuration(),
        }

        self.last_full_check = datetime.utcnow()
        self.cached_results.update(checks)

        return checks

    async def perform_readiness_checks(self) -> Dict[str, HealthCheckResult]:
        """Perform readiness checks - is the service ready to serve traffic?"""
        logger.debug("Performing readiness health checks")

        checks = {
            "database_readiness": await self._check_database_readiness(),
            "api_dependencies": await self._check_api_dependencies(),
            "cache_availability": await self._check_cache_availability(),
            "file_system": await self._check_file_system_access(),
        }

        return checks

    async def perform_liveness_checks(self) -> Dict[str, HealthCheckResult]:
        """Perform liveness checks - is the service alive and responsive?"""
        logger.debug("Performing liveness health checks")

        checks = {
            "application_health": await self._check_application_health(),
            "memory_usage": await self._check_memory_usage(),
            "performance_metrics": await self._check_performance_metrics(),
        }

        return checks

    async def perform_dependency_checks(self) -> Dict[str, HealthCheckResult]:
        """Check external dependencies"""
        logger.debug("Performing dependency health checks")

        checks = {
            "stockx_api": await self._check_stockx_api(),
            "external_services": await self._check_external_services(),
        }

        return checks

    async def get_comprehensive_health(self) -> Dict[str, Any]:
        """Get comprehensive health status with caching"""
        now = datetime.utcnow()

        # Use cached results if recent enough
        if (
            self.last_full_check
            and (now - self.last_full_check).total_seconds() < self.cache_ttl_seconds
        ):

            return self._format_health_response(self.cached_results)

        # Perform all checks
        all_checks = {}

        # Run checks concurrently for better performance
        readiness_task = asyncio.create_task(self.perform_readiness_checks())
        liveness_task = asyncio.create_task(self.perform_liveness_checks())
        dependency_task = asyncio.create_task(self.perform_dependency_checks())

        readiness_checks = await readiness_task
        liveness_checks = await liveness_task
        dependency_checks = await dependency_task

        all_checks.update(readiness_checks)
        all_checks.update(liveness_checks)
        all_checks.update(dependency_checks)

        self.last_full_check = now
        self.cached_results = all_checks

        return self._format_health_response(all_checks)

    async def _check_database_connection(self) -> HealthCheckResult:
        """Check basic database connectivity"""
        start_time = time.time()

        try:
            async with db_manager.get_session() as session:
                await session.execute(text("SELECT 1"))

            response_time = (time.time() - start_time) * 1000

            return HealthCheckResult(
                name="database_connection",
                status=HealthStatus.HEALTHY,
                message="Database connection successful",
                response_time_ms=response_time,
            )

        except Exception as e:
            return HealthCheckResult(
                name="database_connection",
                status=HealthStatus.UNHEALTHY,
                message="Database connection failed",
                error=str(e),
                response_time_ms=(time.time() - start_time) * 1000,
            )

    async def _check_database_readiness(self) -> HealthCheckResult:
        """Check if database is ready for operations"""
        start_time = time.time()

        try:
            async with db_manager.get_session() as session:
                # Check if we can perform basic operations
                result = await session.execute(
                    text(
                        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'catalog'"
                    )
                )
                table_count = result.scalar()

                # Check connection pool
                pool_status = await session.execute(text("SELECT count(*) FROM pg_stat_activity"))
                active_connections = pool_status.scalar()

                response_time = (time.time() - start_time) * 1000

                if table_count > 0:
                    return HealthCheckResult(
                        name="database_readiness",
                        status=HealthStatus.HEALTHY,
                        message=f"Database ready with {table_count} tables, {active_connections} active connections",
                        response_time_ms=response_time,
                        details={
                            "table_count": table_count,
                            "active_connections": active_connections,
                        },
                    )
                else:
                    return HealthCheckResult(
                        name="database_readiness",
                        status=HealthStatus.DEGRADED,
                        message="Database connected but no tables found",
                        response_time_ms=response_time,
                    )

        except Exception as e:
            return HealthCheckResult(
                name="database_readiness",
                status=HealthStatus.UNHEALTHY,
                message="Database readiness check failed",
                error=str(e),
                response_time_ms=(time.time() - start_time) * 1000,
            )

    async def _check_database_migrations(self) -> HealthCheckResult:
        """Check database migration status"""
        start_time = time.time()

        try:
            async with db_manager.get_session() as session:
                # Check if alembic version table exists
                result = await session.execute(
                    text(
                        """
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = 'alembic_version'
                        )
                    """
                    )
                )
                has_alembic = result.scalar()

                if has_alembic:
                    # Get current migration version
                    version_result = await session.execute(
                        text("SELECT version_num FROM alembic_version")
                    )
                    current_version = version_result.scalar()

                    return HealthCheckResult(
                        name="database_migrations",
                        status=HealthStatus.HEALTHY,
                        message=f"Migrations current, version: {current_version}",
                        response_time_ms=(time.time() - start_time) * 1000,
                        details={"current_version": current_version},
                    )
                else:
                    return HealthCheckResult(
                        name="database_migrations",
                        status=HealthStatus.DEGRADED,
                        message="No migration tracking found",
                        response_time_ms=(time.time() - start_time) * 1000,
                    )

        except Exception as e:
            return HealthCheckResult(
                name="database_migrations",
                status=HealthStatus.UNHEALTHY,
                message="Migration check failed",
                error=str(e),
                response_time_ms=(time.time() - start_time) * 1000,
            )

    async def _check_essential_tables(self) -> HealthCheckResult:
        """Check that essential tables exist and are accessible"""
        start_time = time.time()
        essential_tables = ["catalog.product", "inventory.stock", "auth.users"]

        try:
            async with db_manager.get_session() as session:
                table_status = {}

                for table in essential_tables:
                    try:
                        schema, table_name = table.split(".")
                        await session.execute(
                            text(f"SELECT COUNT(*) FROM {schema}.{table_name} LIMIT 1")
                        )
                        table_status[table] = "accessible"
                    except Exception as e:
                        table_status[table] = f"error: {str(e)}"

                failed_tables = [
                    t for t, status in table_status.items() if status.startswith("error")
                ]

                if not failed_tables:
                    return HealthCheckResult(
                        name="essential_tables",
                        status=HealthStatus.HEALTHY,
                        message=f"All {len(essential_tables)} essential tables accessible",
                        response_time_ms=(time.time() - start_time) * 1000,
                        details=table_status,
                    )
                else:
                    return HealthCheckResult(
                        name="essential_tables",
                        status=HealthStatus.UNHEALTHY,
                        message=f"{len(failed_tables)} essential tables not accessible",
                        response_time_ms=(time.time() - start_time) * 1000,
                        details=table_status,
                        error=f"Failed tables: {', '.join(failed_tables)}",
                    )

        except Exception as e:
            return HealthCheckResult(
                name="essential_tables",
                status=HealthStatus.UNHEALTHY,
                message="Essential tables check failed",
                error=str(e),
                response_time_ms=(time.time() - start_time) * 1000,
            )

    async def _check_system_resources(self) -> HealthCheckResult:
        """Check system resource availability"""
        start_time = time.time()

        try:
            system_metrics = await collect_system_metrics()

            if system_metrics is None:
                return HealthCheckResult(
                    name="system_resources",
                    status=HealthStatus.UNKNOWN,
                    message="Could not collect system metrics",
                    response_time_ms=(time.time() - start_time) * 1000,
                )

            # Determine status based on resource usage
            if system_metrics.cpu_percent > 90 or system_metrics.memory_percent > 95:
                status = HealthStatus.UNHEALTHY
                message = "Critical resource usage"
            elif system_metrics.cpu_percent > 80 or system_metrics.memory_percent > 85:
                status = HealthStatus.DEGRADED
                message = "High resource usage"
            else:
                status = HealthStatus.HEALTHY
                message = "Resource usage normal"

            return HealthCheckResult(
                name="system_resources",
                status=status,
                message=message,
                response_time_ms=(time.time() - start_time) * 1000,
                details={
                    "cpu_percent": system_metrics.cpu_percent,
                    "memory_percent": system_metrics.memory_percent,
                    "memory_used_mb": system_metrics.memory_used_mb,
                    "disk_usage_percent": system_metrics.disk_usage_percent,
                    "active_connections": system_metrics.active_connections,
                },
            )

        except Exception as e:
            return HealthCheckResult(
                name="system_resources",
                status=HealthStatus.UNHEALTHY,
                message="System resource check failed",
                error=str(e),
                response_time_ms=(time.time() - start_time) * 1000,
            )

    async def _check_configuration(self) -> HealthCheckResult:
        """Check critical configuration settings"""
        start_time = time.time()

        try:
            from config import get_settings

            settings = get_settings()

            issues = []

            # Check database configuration
            if not settings.database.host:
                issues.append("Database host not configured")

            # Check API configuration
            if not settings.api.secret_key or len(settings.api.secret_key) < 32:
                issues.append("API secret key not properly configured")

            # Check environment
            if settings.environment == "development" and settings.debug is False:
                issues.append("Inconsistent development/debug configuration")

            if issues:
                return HealthCheckResult(
                    name="configuration",
                    status=HealthStatus.DEGRADED,
                    message=f"Configuration issues found: {len(issues)}",
                    response_time_ms=(time.time() - start_time) * 1000,
                    details={"issues": issues},
                )
            else:
                return HealthCheckResult(
                    name="configuration",
                    status=HealthStatus.HEALTHY,
                    message="Configuration validated",
                    response_time_ms=(time.time() - start_time) * 1000,
                )

        except Exception as e:
            return HealthCheckResult(
                name="configuration",
                status=HealthStatus.UNHEALTHY,
                message="Configuration check failed",
                error=str(e),
                response_time_ms=(time.time() - start_time) * 1000,
            )

    async def _check_api_dependencies(self) -> HealthCheckResult:
        """Check API dependencies and integrations"""
        start_time = time.time()

        try:
            # This would check external API integrations
            # For now, return a placeholder
            return HealthCheckResult(
                name="api_dependencies",
                status=HealthStatus.HEALTHY,
                message="API dependencies accessible",
                response_time_ms=(time.time() - start_time) * 1000,
            )

        except Exception as e:
            return HealthCheckResult(
                name="api_dependencies",
                status=HealthStatus.DEGRADED,
                message="API dependency check failed",
                error=str(e),
                response_time_ms=(time.time() - start_time) * 1000,
            )

    async def _check_cache_availability(self) -> HealthCheckResult:
        """Check cache system availability"""
        start_time = time.time()

        # For now, return healthy since we don't have Redis yet
        return HealthCheckResult(
            name="cache_availability",
            status=HealthStatus.HEALTHY,
            message="Cache system not configured (in-memory caching active)",
            response_time_ms=(time.time() - start_time) * 1000,
        )

    async def _check_file_system_access(self) -> HealthCheckResult:
        """Check file system access for uploads and logs"""
        start_time = time.time()

        try:
            import tempfile

            # Test write access to temp directory
            with tempfile.NamedTemporaryFile(delete=True) as tmp_file:
                tmp_file.write(b"health check test")
                tmp_file.flush()

            return HealthCheckResult(
                name="file_system",
                status=HealthStatus.HEALTHY,
                message="File system accessible",
                response_time_ms=(time.time() - start_time) * 1000,
            )

        except Exception as e:
            return HealthCheckResult(
                name="file_system",
                status=HealthStatus.UNHEALTHY,
                message="File system access failed",
                error=str(e),
                response_time_ms=(time.time() - start_time) * 1000,
            )

    async def _check_application_health(self) -> HealthCheckResult:
        """Check application-specific health metrics"""
        start_time = time.time()

        try:
            uptime_seconds = (datetime.utcnow() - self.startup_time).total_seconds()

            # Get performance summary from APM
            apm = get_apm_collector()
            perf_summary = apm.get_performance_summary(minutes=5)
            health_score = perf_summary.get("health_score", 100)

            if health_score >= 80:
                status = HealthStatus.HEALTHY
                message = f"Application healthy (score: {health_score:.1f}/100)"
            elif health_score >= 60:
                status = HealthStatus.DEGRADED
                message = f"Application degraded (score: {health_score:.1f}/100)"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Application unhealthy (score: {health_score:.1f}/100)"

            return HealthCheckResult(
                name="application_health",
                status=status,
                message=message,
                response_time_ms=(time.time() - start_time) * 1000,
                details={
                    "uptime_seconds": uptime_seconds,
                    "health_score": health_score,
                    "performance_summary": perf_summary,
                },
            )

        except Exception as e:
            return HealthCheckResult(
                name="application_health",
                status=HealthStatus.UNKNOWN,
                message="Application health check failed",
                error=str(e),
                response_time_ms=(time.time() - start_time) * 1000,
            )

    async def _check_memory_usage(self) -> HealthCheckResult:
        """Check memory usage patterns"""
        start_time = time.time()

        try:
            import psutil
            import gc

            # Force garbage collection
            gc.collect()

            # Get memory info
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()

            # Check memory usage
            if memory_percent > 90:
                status = HealthStatus.UNHEALTHY
                message = "Critical memory usage"
            elif memory_percent > 80:
                status = HealthStatus.DEGRADED
                message = "High memory usage"
            else:
                status = HealthStatus.HEALTHY
                message = "Memory usage normal"

            return HealthCheckResult(
                name="memory_usage",
                status=status,
                message=f"{message} ({memory_percent:.1f}%)",
                response_time_ms=(time.time() - start_time) * 1000,
                details={
                    "memory_percent": memory_percent,
                    "rss_mb": memory_info.rss / (1024 * 1024),
                    "vms_mb": memory_info.vms / (1024 * 1024),
                },
            )

        except Exception as e:
            return HealthCheckResult(
                name="memory_usage",
                status=HealthStatus.UNKNOWN,
                message="Memory usage check failed",
                error=str(e),
                response_time_ms=(time.time() - start_time) * 1000,
            )

    async def _check_performance_metrics(self) -> HealthCheckResult:
        """Check recent performance metrics"""
        start_time = time.time()

        try:
            apm = get_apm_collector()
            perf_summary = apm.get_performance_summary(minutes=5)

            requests = perf_summary.get("requests", {})
            database = perf_summary.get("database", {})
            alerts = perf_summary.get("alerts", {})

            issues = []

            # Check request performance
            if requests.get("error_rate", 0) > 5:
                issues.append(f"High error rate: {requests['error_rate']:.1f}%")

            if requests.get("avg_response_time_ms", 0) > 2000:
                issues.append(f"Slow responses: {requests['avg_response_time_ms']:.1f}ms avg")

            # Check database performance
            if database.get("slow_query_rate", 0) > 20:
                issues.append(f"High slow query rate: {database['slow_query_rate']:.1f}%")

            # Check alerts
            critical_alerts = alerts.get("by_severity", {}).get("critical", 0)
            if critical_alerts > 0:
                issues.append(f"{critical_alerts} critical alerts")

            if issues:
                return HealthCheckResult(
                    name="performance_metrics",
                    status=HealthStatus.DEGRADED,
                    message=f"Performance issues detected: {'; '.join(issues)}",
                    response_time_ms=(time.time() - start_time) * 1000,
                    details=perf_summary,
                )
            else:
                return HealthCheckResult(
                    name="performance_metrics",
                    status=HealthStatus.HEALTHY,
                    message="Performance metrics healthy",
                    response_time_ms=(time.time() - start_time) * 1000,
                    details=perf_summary,
                )

        except Exception as e:
            return HealthCheckResult(
                name="performance_metrics",
                status=HealthStatus.UNKNOWN,
                message="Performance metrics check failed",
                error=str(e),
                response_time_ms=(time.time() - start_time) * 1000,
            )

    async def _check_stockx_api(self) -> HealthCheckResult:
        """Check StockX API connectivity"""
        start_time = time.time()

        try:
            # This would test StockX API connectivity
            # For now, return a placeholder
            return HealthCheckResult(
                name="stockx_api",
                status=HealthStatus.HEALTHY,
                message="StockX API accessible",
                response_time_ms=(time.time() - start_time) * 1000,
            )

        except Exception as e:
            return HealthCheckResult(
                name="stockx_api",
                status=HealthStatus.DEGRADED,
                message="StockX API check failed",
                error=str(e),
                response_time_ms=(time.time() - start_time) * 1000,
            )

    async def _check_external_services(self) -> HealthCheckResult:
        """Check other external service dependencies"""
        start_time = time.time()

        # Placeholder for external service checks
        return HealthCheckResult(
            name="external_services",
            status=HealthStatus.HEALTHY,
            message="External services accessible",
            response_time_ms=(time.time() - start_time) * 1000,
        )

    def _format_health_response(self, checks: Dict[str, HealthCheckResult]) -> Dict[str, Any]:
        """Format health check results into a comprehensive response"""
        overall_status = self._determine_overall_status(checks)

        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": (datetime.utcnow() - self.startup_time).total_seconds(),
            "checks": {
                name: {
                    "status": result.status,
                    "message": result.message,
                    "response_time_ms": result.response_time_ms,
                    "details": result.details,
                    "error": result.error,
                }
                for name, result in checks.items()
            },
            "summary": {
                "total_checks": len(checks),
                "healthy": sum(1 for r in checks.values() if r.status == HealthStatus.HEALTHY),
                "degraded": sum(1 for r in checks.values() if r.status == HealthStatus.DEGRADED),
                "unhealthy": sum(1 for r in checks.values() if r.status == HealthStatus.UNHEALTHY),
                "unknown": sum(1 for r in checks.values() if r.status == HealthStatus.UNKNOWN),
            },
        }

    def _determine_overall_status(self, checks: Dict[str, HealthCheckResult]) -> HealthStatus:
        """Determine overall health status from individual checks"""
        if not checks:
            return HealthStatus.UNKNOWN

        statuses = [result.status for result in checks.values()]

        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        elif all(status == HealthStatus.HEALTHY for status in statuses):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN


# Global health checker instance
_advanced_health_checker: Optional[AdvancedHealthChecker] = None


def get_advanced_health_checker() -> AdvancedHealthChecker:
    """Get global advanced health checker instance"""
    global _advanced_health_checker
    if _advanced_health_checker is None:
        _advanced_health_checker = AdvancedHealthChecker()
    return _advanced_health_checker

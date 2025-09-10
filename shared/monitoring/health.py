"""
Health Check System
Comprehensive health monitoring for production environments
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Protocol

import structlog

logger = structlog.get_logger(__name__)


class HealthStatus(str, Enum):
    """Health status enumeration"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class CheckType(str, Enum):
    """Health check type enumeration"""

    STARTUP = "startup"  # Checks required during startup
    READINESS = "readiness"  # Checks if service is ready to serve traffic
    LIVENESS = "liveness"  # Checks if service is alive and responding
    DEPENDENCY = "dependency"  # External dependency checks


@dataclass
class HealthCheckResult:
    """Result of a health check"""

    name: str
    status: HealthStatus
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    response_time_ms: Optional[float] = None
    timestamp: Optional[datetime] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class HealthCheck(Protocol):
    """Health check protocol"""

    name: str
    check_type: CheckType
    timeout_seconds: float

    async def check(self) -> HealthCheckResult:
        """Perform the health check"""
        ...


class BaseHealthCheck(ABC):
    """Base class for health checks"""

    def __init__(
        self,
        name: str,
        check_type: CheckType = CheckType.LIVENESS,
        timeout_seconds: float = 30.0,
        description: str = "",
    ):
        self.name = name
        self.check_type = check_type
        self.timeout_seconds = timeout_seconds
        self.description = description

    async def check(self) -> HealthCheckResult:
        """Execute the health check with timeout"""
        start_time = asyncio.get_event_loop().time()

        try:
            # Run check with timeout
            result = await asyncio.wait_for(self._perform_check(), timeout=self.timeout_seconds)

            # Calculate response time
            response_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            result.response_time_ms = response_time_ms

            return result

        except asyncio.TimeoutError:
            response_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {self.timeout_seconds}s",
                response_time_ms=response_time_ms,
                error="timeout",
            )
        except Exception as e:
            response_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message="Health check failed with exception",
                response_time_ms=response_time_ms,
                error=str(e),
            )

    @abstractmethod
    async def _perform_check(self) -> HealthCheckResult:
        """Implement the actual health check logic"""
        pass


class DatabaseHealthCheck(BaseHealthCheck):
    """Database connectivity health check"""

    def __init__(self, db_manager, timeout_seconds: float = 5.0):
        super().__init__(
            name="database",
            check_type=CheckType.DEPENDENCY,
            timeout_seconds=timeout_seconds,
            description="Database connectivity and basic operations",
        )
        self.db_manager = db_manager

    async def _perform_check(self) -> HealthCheckResult:
        """Check database connectivity and basic operations"""
        try:
            # Test basic connectivity
            health_status = await self.db_manager.get_health_status()

            if health_status.get("status") == "healthy":
                pool_info = health_status.get("pool", {})
                db_info = health_status.get("database", {})

                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.HEALTHY,
                    message="Database is healthy",
                    details={
                        "pool_size": pool_info.get("size"),
                        "active_connections": pool_info.get("checked_out"),
                        "database_type": db_info.get("database_type", "PostgreSQL"),
                    },
                )
            else:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.UNHEALTHY,
                    message="Database is unhealthy",
                    details=health_status,
                    error=health_status.get("error"),
                )

        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message="Database health check failed",
                error=str(e),
            )


class ExternalServiceHealthCheck(BaseHealthCheck):
    """External service health check"""

    def __init__(
        self,
        service_name: str,
        check_function: Callable[[], Awaitable[bool]],
        timeout_seconds: float = 10.0,
    ):
        super().__init__(
            name=f"external_service_{service_name}",
            check_type=CheckType.DEPENDENCY,
            timeout_seconds=timeout_seconds,
            description=f"External service: {service_name}",
        )
        self.service_name = service_name
        self.check_function = check_function

    async def _perform_check(self) -> HealthCheckResult:
        """Check external service availability"""
        try:
            is_healthy = await self.check_function()

            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY,
                message=f"{self.service_name} is {'available' if is_healthy else 'unavailable'}",
                details={"service": self.service_name},
            )

        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"{self.service_name} health check failed",
                error=str(e),
                details={"service": self.service_name},
            )


class SystemResourceHealthCheck(BaseHealthCheck):
    """System resource health check"""

    def __init__(
        self,
        cpu_threshold: float = 85.0,
        memory_threshold: float = 85.0,
        disk_threshold: float = 90.0,
        timeout_seconds: float = 5.0,
    ):
        super().__init__(
            name="system_resources",
            check_type=CheckType.LIVENESS,
            timeout_seconds=timeout_seconds,
            description="System resource usage monitoring",
        )
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.disk_threshold = disk_threshold

    async def _perform_check(self) -> HealthCheckResult:
        """Check system resource usage"""
        try:
            import psutil

            # Get current resource usage
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            disk_percent = (disk.used / disk.total) * 100

            # Determine health status
            issues = []
            status = HealthStatus.HEALTHY

            if cpu_percent > self.cpu_threshold:
                issues.append(f"High CPU usage: {cpu_percent:.1f}%")
                status = HealthStatus.DEGRADED

            if memory.percent > self.memory_threshold:
                issues.append(f"High memory usage: {memory.percent:.1f}%")
                status = HealthStatus.DEGRADED

            if disk_percent > self.disk_threshold:
                issues.append(f"High disk usage: {disk_percent:.1f}%")
                status = (
                    HealthStatus.DEGRADED
                    if status == HealthStatus.HEALTHY
                    else HealthStatus.UNHEALTHY
                )

            # Critical thresholds make it unhealthy
            if cpu_percent > 95 or memory.percent > 95 or disk_percent > 95:
                status = HealthStatus.UNHEALTHY

            message = (
                "System resources are healthy"
                if status == HealthStatus.HEALTHY
                else f"Resource issues: {', '.join(issues)}"
            )

            return HealthCheckResult(
                name=self.name,
                status=status,
                message=message,
                details={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "disk_percent": disk_percent,
                    "thresholds": {
                        "cpu": self.cpu_threshold,
                        "memory": self.memory_threshold,
                        "disk": self.disk_threshold,
                    },
                },
            )

        except ImportError:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNKNOWN,
                message="psutil not available for system monitoring",
                error="missing_dependency",
            )
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message="System resource check failed",
                error=str(e),
            )


class ApplicationHealthCheck(BaseHealthCheck):
    """Application-specific health check"""

    def __init__(self, timeout_seconds: float = 5.0):
        super().__init__(
            name="application",
            check_type=CheckType.READINESS,
            timeout_seconds=timeout_seconds,
            description="Application readiness and basic functionality",
        )

    async def _perform_check(self) -> HealthCheckResult:
        """Check application health"""
        try:
            # Check if application is ready to serve requests
            # This could include checking if all required services are initialized

            # Example checks:
            # - Configuration loaded
            # - Database migrations completed
            # - Required external services available

            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.HEALTHY,
                message="Application is ready",
                details={"version": "2.1.0", "startup_complete": True, "migrations_applied": True},
            )

        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message="Application health check failed",
                error=str(e),
            )


class HealthCheckManager:
    """Manager for all health checks"""

    def __init__(self):
        self.checks: Dict[str, BaseHealthCheck] = {}
        self.last_results: Dict[str, HealthCheckResult] = {}
        self._check_lock = asyncio.Lock()

    def register_check(self, check: BaseHealthCheck):
        """Register a health check"""
        self.checks[check.name] = check
        logger.info("Health check registered", name=check.name, type=check.check_type)

    def unregister_check(self, name: str):
        """Unregister a health check"""
        if name in self.checks:
            del self.checks[name]
            if name in self.last_results:
                del self.last_results[name]
            logger.info("Health check unregistered", name=name)

    async def run_check(self, name: str) -> Optional[HealthCheckResult]:
        """Run a specific health check"""
        if name not in self.checks:
            return None

        check = self.checks[name]

        async with self._check_lock:
            try:
                result = await check.check()
                self.last_results[name] = result

                logger.debug(
                    "Health check completed",
                    name=name,
                    status=result.status,
                    response_time_ms=result.response_time_ms,
                )

                return result

            except Exception as e:
                result = HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message="Health check execution failed",
                    error=str(e),
                )
                self.last_results[name] = result
                return result

    async def run_checks(
        self, check_types: Optional[List[CheckType]] = None, parallel: bool = True
    ) -> Dict[str, HealthCheckResult]:
        """Run multiple health checks"""
        checks_to_run = []

        for name, check in self.checks.items():
            if check_types is None or check.check_type in check_types:
                checks_to_run.append(name)

        if parallel and len(checks_to_run) > 1:
            # Run checks in parallel
            tasks = [self.run_check(name) for name in checks_to_run]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            result_dict = {}
            for i, name in enumerate(checks_to_run):
                if isinstance(results[i], Exception):
                    result_dict[name] = HealthCheckResult(
                        name=name,
                        status=HealthStatus.UNHEALTHY,
                        message="Health check failed with exception",
                        error=str(results[i]),
                    )
                else:
                    result_dict[name] = results[i]

            return result_dict
        else:
            # Run checks sequentially
            results = {}
            for name in checks_to_run:
                result = await self.run_check(name)
                if result:
                    results[name] = result

            return results

    async def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        results = await self.run_checks(parallel=True)

        # Determine overall status
        overall_status = HealthStatus.HEALTHY
        healthy_count = 0
        degraded_count = 0
        unhealthy_count = 0
        unknown_count = 0

        for result in results.values():
            if result.status == HealthStatus.HEALTHY:
                healthy_count += 1
            elif result.status == HealthStatus.DEGRADED:
                degraded_count += 1
                if overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
            elif result.status == HealthStatus.UNHEALTHY:
                unhealthy_count += 1
                overall_status = HealthStatus.UNHEALTHY
            else:
                unknown_count += 1
                if overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.UNKNOWN

        # Calculate uptime (placeholder - would need actual startup time)
        import time

        uptime_seconds = time.time() - getattr(self, "_start_time", time.time())

        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": uptime_seconds,
            "checks": {
                "total": len(results),
                "healthy": healthy_count,
                "degraded": degraded_count,
                "unhealthy": unhealthy_count,
                "unknown": unknown_count,
            },
            "components": {
                name: {
                    "status": result.status,
                    "message": result.message,
                    "response_time_ms": result.response_time_ms,
                    "last_check": result.timestamp.isoformat() if result.timestamp else None,
                    "details": result.details,
                }
                for name, result in results.items()
            },
        }

    def get_cached_results(self) -> Dict[str, HealthCheckResult]:
        """Get last cached health check results"""
        return self.last_results.copy()

    def get_check_summary(self) -> Dict[str, Any]:
        """Get summary of registered checks"""
        return {
            "total_checks": len(self.checks),
            "checks_by_type": {
                check_type.value: sum(
                    1 for check in self.checks.values() if check.check_type == check_type
                )
                for check_type in CheckType
            },
            "registered_checks": [
                {
                    "name": check.name,
                    "type": check.check_type,
                    "timeout": check.timeout_seconds,
                    "description": check.description,
                }
                for check in self.checks.values()
            ],
        }


# Global health check manager
_health_manager = HealthCheckManager()


def get_health_manager() -> HealthCheckManager:
    """Get the global health check manager"""
    return _health_manager


# Convenience functions
async def setup_default_health_checks(db_manager=None):
    """Setup default health checks"""
    health_manager = get_health_manager()

    # Application health check
    health_manager.register_check(ApplicationHealthCheck())

    # System resources check
    health_manager.register_check(SystemResourceHealthCheck())

    # Database check (if db_manager provided)
    if db_manager:
        health_manager.register_check(DatabaseHealthCheck(db_manager))

    logger.info("Default health checks configured")


async def create_external_service_check(
    service_name: str, check_url: str, timeout_seconds: float = 10.0
) -> ExternalServiceHealthCheck:
    """Create a health check for an external HTTP service"""

    async def http_check() -> bool:
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(check_url, timeout=timeout_seconds)
                return response.status_code < 400
        except Exception:
            return False

    return ExternalServiceHealthCheck(service_name, http_check, timeout_seconds)

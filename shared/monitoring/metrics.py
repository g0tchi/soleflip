"""
Production Monitoring and Metrics Collection
Comprehensive monitoring system for production environments
"""

import asyncio
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional

import psutil
import structlog

logger = structlog.get_logger(__name__)


class MetricType(str, Enum):
    """Metric type enumeration"""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class MetricUnit(str, Enum):
    """Metric unit enumeration"""

    SECONDS = "seconds"
    MILLISECONDS = "milliseconds"
    BYTES = "bytes"
    MEGABYTES = "megabytes"
    REQUESTS = "requests"
    PERCENT = "percent"
    COUNT = "count"


@dataclass
class MetricSample:
    """Individual metric sample"""

    timestamp: datetime
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class Metric:
    """Metric definition and storage"""

    name: str
    type: MetricType
    unit: MetricUnit
    description: str
    labels: Dict[str, str] = field(default_factory=dict)
    samples: deque = field(default_factory=lambda: deque(maxlen=10000))

    def add_sample(self, value: float, labels: Optional[Dict[str, str]] = None):
        """Add a new sample to the metric"""
        sample_labels = {**self.labels, **(labels or {})}
        sample = MetricSample(timestamp=datetime.utcnow(), value=value, labels=sample_labels)
        self.samples.append(sample)

    def get_latest_value(self) -> Optional[float]:
        """Get the latest metric value"""
        return self.samples[-1].value if self.samples else None

    def get_average(self, window_minutes: int = 5) -> Optional[float]:
        """Get average value over time window"""
        cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
        recent_samples = [s for s in self.samples if s.timestamp > cutoff]
        if not recent_samples:
            return None
        return sum(s.value for s in recent_samples) / len(recent_samples)


class MetricsRegistry:
    """Central registry for all metrics"""

    def __init__(self):
        self.metrics: Dict[str, Metric] = {}
        self._locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def register_metric(
        self,
        name: str,
        type: MetricType,
        unit: MetricUnit,
        description: str,
        labels: Optional[Dict[str, str]] = None,
    ) -> Metric:
        """Register a new metric"""
        if name in self.metrics:
            return self.metrics[name]

        metric = Metric(
            name=name, type=type, unit=unit, description=description, labels=labels or {}
        )
        self.metrics[name] = metric

        logger.debug("Metric registered", name=name, type=type, unit=unit)
        return metric

    async def record_value(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a value for a metric"""
        if name not in self.metrics:
            logger.warning("Attempt to record value for unregistered metric", name=name)
            return

        async with self._locks[name]:
            self.metrics[name].add_sample(value, labels)

    def get_metric(self, name: str) -> Optional[Metric]:
        """Get a metric by name"""
        return self.metrics.get(name)

    def get_all_metrics(self) -> Dict[str, Metric]:
        """Get all registered metrics"""
        return self.metrics.copy()

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics"""
        summary = {}
        for name, metric in self.metrics.items():
            latest = metric.get_latest_value()
            avg_5m = metric.get_average(5)
            avg_1h = metric.get_average(60)

            summary[name] = {
                "type": metric.type,
                "unit": metric.unit,
                "description": metric.description,
                "latest_value": latest,
                "avg_5min": avg_5m,
                "avg_1hour": avg_1h,
                "sample_count": len(metric.samples),
                "labels": metric.labels,
            }

        return summary


# Global metrics registry
_metrics_registry = MetricsRegistry()


def get_metrics_registry() -> MetricsRegistry:
    """Get the global metrics registry"""
    return _metrics_registry


class ApplicationMetrics:
    """Application-specific metrics collector"""

    def __init__(self, registry: MetricsRegistry):
        self.registry = registry
        self._setup_standard_metrics()

    def _setup_standard_metrics(self):
        """Setup standard application metrics"""
        # Request metrics
        self.registry.register_metric(
            "http_requests_total", MetricType.COUNTER, MetricUnit.REQUESTS, "Total HTTP requests"
        )

        self.registry.register_metric(
            "http_request_duration",
            MetricType.HISTOGRAM,
            MetricUnit.MILLISECONDS,
            "HTTP request duration",
        )

        self.registry.register_metric(
            "http_response_status",
            MetricType.COUNTER,
            MetricUnit.REQUESTS,
            "HTTP responses by status code",
        )

        # Database metrics
        self.registry.register_metric(
            "database_connections_active",
            MetricType.GAUGE,
            MetricUnit.COUNT,
            "Active database connections",
        )

        self.registry.register_metric(
            "database_query_duration",
            MetricType.HISTOGRAM,
            MetricUnit.MILLISECONDS,
            "Database query duration",
        )

        self.registry.register_metric(
            "database_pool_size",
            MetricType.GAUGE,
            MetricUnit.COUNT,
            "Database connection pool size",
        )

        # Application metrics
        self.registry.register_metric(
            "application_uptime",
            MetricType.GAUGE,
            MetricUnit.SECONDS,
            "Application uptime in seconds",
        )

        self.registry.register_metric(
            "background_tasks_total",
            MetricType.COUNTER,
            MetricUnit.COUNT,
            "Total background tasks executed",
        )

        self.registry.register_metric(
            "background_task_duration",
            MetricType.HISTOGRAM,
            MetricUnit.MILLISECONDS,
            "Background task duration",
        )

        # Business metrics
        self.registry.register_metric(
            "inventory_items_total", MetricType.GAUGE, MetricUnit.COUNT, "Total inventory items"
        )

        self.registry.register_metric(
            "transactions_total",
            MetricType.COUNTER,
            MetricUnit.COUNT,
            "Total transactions processed",
        )

        self.registry.register_metric(
            "import_batches_total",
            MetricType.COUNTER,
            MetricUnit.COUNT,
            "Total import batches processed",
        )

    async def record_http_request(
        self, method: str, path: str, status_code: int, duration_ms: float
    ):
        """Record HTTP request metrics"""
        labels = {"method": method, "path": path}

        await self.registry.record_value("http_requests_total", 1, labels)
        await self.registry.record_value("http_request_duration", duration_ms, labels)
        await self.registry.record_value(
            "http_response_status", 1, {**labels, "status": str(status_code)}
        )

    async def record_database_query(self, operation: str, duration_ms: float):
        """Record database query metrics"""
        labels = {"operation": operation}
        await self.registry.record_value("database_query_duration", duration_ms, labels)

    async def update_database_pool_metrics(self, active: int, pool_size: int):
        """Update database pool metrics"""
        await self.registry.record_value("database_connections_active", active)
        await self.registry.record_value("database_pool_size", pool_size)

    async def record_background_task(self, task_name: str, duration_ms: float, success: bool):
        """Record background task metrics"""
        labels = {"task": task_name, "status": "success" if success else "failure"}
        await self.registry.record_value("background_tasks_total", 1, labels)
        await self.registry.record_value("background_task_duration", duration_ms, labels)

    async def update_business_metrics(self, inventory_count: int, transaction_count: int):
        """Update business metrics"""
        await self.registry.record_value("inventory_items_total", inventory_count)
        await self.registry.record_value("transactions_total", transaction_count)


class SystemMetrics:
    """System resource metrics collector"""

    def __init__(self, registry: MetricsRegistry):
        self.registry = registry
        self._setup_system_metrics()
        self._start_time = time.time()

    def _setup_system_metrics(self):
        """Setup system metrics"""
        self.registry.register_metric(
            "system_cpu_percent", MetricType.GAUGE, MetricUnit.PERCENT, "CPU usage percentage"
        )

        self.registry.register_metric(
            "system_memory_percent", MetricType.GAUGE, MetricUnit.PERCENT, "Memory usage percentage"
        )

        self.registry.register_metric(
            "system_memory_bytes", MetricType.GAUGE, MetricUnit.BYTES, "Memory usage in bytes"
        )

        self.registry.register_metric(
            "system_disk_percent", MetricType.GAUGE, MetricUnit.PERCENT, "Disk usage percentage"
        )

        self.registry.register_metric(
            "system_network_bytes_sent", MetricType.COUNTER, MetricUnit.BYTES, "Network bytes sent"
        )

        self.registry.register_metric(
            "system_network_bytes_recv",
            MetricType.COUNTER,
            MetricUnit.BYTES,
            "Network bytes received",
        )

        self.registry.register_metric(
            "process_open_files", MetricType.GAUGE, MetricUnit.COUNT, "Number of open files"
        )

    async def collect_system_metrics(self):
        """Collect current system metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            await self.registry.record_value("system_cpu_percent", cpu_percent)

            # Memory metrics
            memory = psutil.virtual_memory()
            await self.registry.record_value("system_memory_percent", memory.percent)
            await self.registry.record_value("system_memory_bytes", memory.used)

            # Disk metrics
            disk = psutil.disk_usage("/")
            disk_percent = (disk.used / disk.total) * 100
            await self.registry.record_value("system_disk_percent", disk_percent)

            # Network metrics
            network = psutil.net_io_counters()
            await self.registry.record_value("system_network_bytes_sent", network.bytes_sent)
            await self.registry.record_value("system_network_bytes_recv", network.bytes_recv)

            # Process metrics
            process = psutil.Process()
            await self.registry.record_value("process_open_files", len(process.open_files()))

            # Uptime
            uptime = time.time() - self._start_time
            await self.registry.record_value("application_uptime", uptime)

        except Exception as e:
            logger.error("Error collecting system metrics", error=str(e))


class MetricsCollector:
    """Main metrics collector service"""

    def __init__(self):
        self.registry = get_metrics_registry()
        self.app_metrics = ApplicationMetrics(self.registry)
        self.system_metrics = SystemMetrics(self.registry)
        self._collection_task: Optional[asyncio.Task] = None
        self._collection_interval = 30  # seconds

    def start_collection(self):
        """Start background metrics collection"""
        if self._collection_task and not self._collection_task.done():
            return

        self._collection_task = asyncio.create_task(self._collection_loop())
        logger.info("Metrics collection started", interval=self._collection_interval)

    def stop_collection(self):
        """Stop background metrics collection"""
        if self._collection_task and not self._collection_task.done():
            self._collection_task.cancel()
            logger.info("Metrics collection stopped")

    async def _collection_loop(self):
        """Background metrics collection loop"""
        while True:
            try:
                await self.system_metrics.collect_system_metrics()
                await asyncio.sleep(self._collection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in metrics collection loop", error=str(e))
                await asyncio.sleep(5)  # Short delay on error

    def get_health_status(self) -> Dict[str, Any]:
        """Get system health status based on metrics"""
        try:
            cpu_metric = self.registry.get_metric("system_cpu_percent")
            memory_metric = self.registry.get_metric("system_memory_percent")

            cpu_usage = cpu_metric.get_latest_value() if cpu_metric else None
            memory_usage = memory_metric.get_latest_value() if memory_metric else None

            status = "healthy"
            issues = []

            if cpu_usage and cpu_usage > 80:
                status = "degraded"
                issues.append(f"High CPU usage: {cpu_usage:.1f}%")

            if memory_usage and memory_usage > 85:
                status = "degraded" if status == "healthy" else "unhealthy"
                issues.append(f"High memory usage: {memory_usage:.1f}%")

            if cpu_usage and cpu_usage > 95:
                status = "unhealthy"

            if memory_usage and memory_usage > 95:
                status = "unhealthy"

            return {
                "status": status,
                "issues": issues,
                "metrics": {"cpu_usage": cpu_usage, "memory_usage": memory_usage},
            }

        except Exception as e:
            return {"status": "unknown", "error": str(e)}


# Global metrics collector instance
_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector"""
    return _metrics_collector


# Decorators for automatic metrics collection
def track_execution_time(metric_name: str = None):
    """Decorator to track function execution time"""

    def decorator(func):
        nonlocal metric_name
        if not metric_name:
            metric_name = f"{func.__module__}.{func.__name__}_duration"

        # Register metric if not exists
        registry = get_metrics_registry()
        registry.register_metric(
            metric_name,
            MetricType.HISTOGRAM,
            MetricUnit.MILLISECONDS,
            f"Execution time for {func.__name__}",
        )

        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                await registry.record_value(metric_name, duration_ms, {"status": "success"})
                return result
            except Exception:
                duration_ms = (time.time() - start_time) * 1000
                await registry.record_value(metric_name, duration_ms, {"status": "error"})
                raise

        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                asyncio.create_task(
                    registry.record_value(metric_name, duration_ms, {"status": "success"})
                )
                return result
            except Exception:
                duration_ms = (time.time() - start_time) * 1000
                asyncio.create_task(
                    registry.record_value(metric_name, duration_ms, {"status": "error"})
                )
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def track_counter(metric_name: str, labels: Optional[Dict[str, str]] = None):
    """Decorator to track function calls as counter"""

    def decorator(func):
        # Register metric if not exists
        registry = get_metrics_registry()
        registry.register_metric(
            metric_name, MetricType.COUNTER, MetricUnit.COUNT, f"Number of calls to {func.__name__}"
        )

        async def async_wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                await registry.record_value(metric_name, 1, {**(labels or {}), "status": "success"})
                return result
            except Exception:
                await registry.record_value(metric_name, 1, {**(labels or {}), "status": "error"})
                raise

        def sync_wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                asyncio.create_task(
                    registry.record_value(metric_name, 1, {**(labels or {}), "status": "success"})
                )
                return result
            except Exception:
                asyncio.create_task(
                    registry.record_value(metric_name, 1, {**(labels or {}), "status": "error"})
                )
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Context managers for metrics
@asynccontextmanager
async def track_operation(operation_name: str, labels: Optional[Dict[str, str]] = None):
    """Context manager to track operation duration and success"""
    registry = get_metrics_registry()

    # Register metrics
    duration_metric = f"{operation_name}_duration"
    counter_metric = f"{operation_name}_total"

    registry.register_metric(
        duration_metric, MetricType.HISTOGRAM, MetricUnit.MILLISECONDS, f"{operation_name} duration"
    )
    registry.register_metric(
        counter_metric, MetricType.COUNTER, MetricUnit.COUNT, f"{operation_name} total"
    )

    start_time = time.time()
    try:
        yield
        duration_ms = (time.time() - start_time) * 1000
        await registry.record_value(
            duration_metric, duration_ms, {**(labels or {}), "status": "success"}
        )
        await registry.record_value(counter_metric, 1, {**(labels or {}), "status": "success"})
    except Exception:
        duration_ms = (time.time() - start_time) * 1000
        await registry.record_value(
            duration_metric, duration_ms, {**(labels or {}), "status": "error"}
        )
        await registry.record_value(counter_metric, 1, {**(labels or {}), "status": "error"})
        raise

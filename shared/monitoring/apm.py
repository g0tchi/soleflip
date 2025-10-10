"""
Application Performance Monitoring (APM) System
Advanced monitoring and observability for production environments
"""

import asyncio
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from functools import wraps

import psutil
import structlog
from sqlalchemy import text

from shared.database.connection import db_manager

logger = structlog.get_logger(__name__)


@dataclass
class RequestMetrics:
    """Metrics for individual requests"""
    
    method: str
    path: str
    status_code: int
    response_time_ms: float
    timestamp: datetime
    user_id: Optional[str] = None
    request_size: Optional[int] = None
    response_size: Optional[int] = None
    error_message: Optional[str] = None


@dataclass
class DatabaseMetrics:
    """Database operation metrics"""
    
    query_type: str
    execution_time_ms: float
    rows_affected: Optional[int] = None
    table_name: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    error: Optional[str] = None


@dataclass
class SystemMetrics:
    """System resource metrics"""
    
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    disk_usage_percent: float
    active_connections: int
    timestamp: datetime = field(default_factory=datetime.utcnow)


class APMCollector:
    """Advanced Performance Monitoring data collector"""
    
    def __init__(self, max_samples: int = 10000):
        self.max_samples = max_samples
        self.request_metrics: deque = deque(maxlen=max_samples)
        self.database_metrics: deque = deque(maxlen=max_samples)
        self.system_metrics: deque = deque(maxlen=max_samples)
        self.error_tracking: defaultdict = defaultdict(int)
        self.slow_queries: deque = deque(maxlen=100)  # Track 100 slowest queries
        self.performance_alerts: List[Dict] = []
        
        # Performance thresholds
        self.slow_request_threshold_ms = 1000
        self.slow_query_threshold_ms = 500
        self.high_cpu_threshold = 80.0
        self.high_memory_threshold = 90.0  # Increased for dev environment with multiple services
        
        logger.info("APM Collector initialized", max_samples=max_samples)
    
    def record_request(self, metrics: RequestMetrics):
        """Record HTTP request metrics"""
        self.request_metrics.append(metrics)
        
        # Check for performance issues
        if metrics.response_time_ms > self.slow_request_threshold_ms:
            self._create_alert("slow_request", {
                "path": metrics.path,
                "method": metrics.method,
                "response_time_ms": metrics.response_time_ms,
                "threshold_ms": self.slow_request_threshold_ms
            })
        
        # Track errors
        if metrics.status_code >= 400:
            error_key = f"{metrics.method}:{metrics.path}:{metrics.status_code}"
            self.error_tracking[error_key] += 1
    
    def record_database_operation(self, metrics: DatabaseMetrics):
        """Record database operation metrics"""
        self.database_metrics.append(metrics)
        
        # Track slow queries
        if metrics.execution_time_ms > self.slow_query_threshold_ms:
            self.slow_queries.append(metrics)
            self._create_alert("slow_query", {
                "query_type": metrics.query_type,
                "execution_time_ms": metrics.execution_time_ms,
                "table_name": metrics.table_name,
                "threshold_ms": self.slow_query_threshold_ms
            })
    
    def record_system_metrics(self, metrics: SystemMetrics):
        """Record system resource metrics"""
        self.system_metrics.append(metrics)
        
        # Check resource usage alerts
        if metrics.cpu_percent > self.high_cpu_threshold:
            self._create_alert("high_cpu", {
                "cpu_percent": metrics.cpu_percent,
                "threshold": self.high_cpu_threshold
            })
        
        if metrics.memory_percent > self.high_memory_threshold:
            self._create_alert("high_memory", {
                "memory_percent": metrics.memory_percent,
                "memory_used_mb": metrics.memory_used_mb,
                "threshold": self.high_memory_threshold
            })
    
    def _create_alert(self, alert_type: str, details: Dict):
        """Create performance alert"""
        alert = {
            "type": alert_type,
            "timestamp": datetime.utcnow(),
            "details": details,
            "severity": self._get_alert_severity(alert_type, details)
        }
        self.performance_alerts.append(alert)
        logger.warning("Performance alert created", alert=alert)
    
    def _get_alert_severity(self, alert_type: str, details: Dict) -> str:
        """Determine alert severity"""
        if alert_type == "slow_request":
            if details.get("response_time_ms", 0) > 5000:
                return "critical"
            elif details.get("response_time_ms", 0) > 2000:
                return "high"
            return "medium"
        
        elif alert_type == "slow_query":
            if details.get("execution_time_ms", 0) > 2000:
                return "critical"
            elif details.get("execution_time_ms", 0) > 1000:
                return "high"
            return "medium"
        
        elif alert_type in ["high_cpu", "high_memory"]:
            threshold_percent = details.get("threshold", 0)
            current_percent = details.get(f"{alert_type.split('_')[1]}_percent", 0)
            
            if current_percent > threshold_percent + 15:
                return "critical"
            elif current_percent > threshold_percent + 10:
                return "high"
            return "medium"
        
        return "low"
    
    def get_performance_summary(self, minutes: int = 15) -> Dict[str, Any]:
        """Get performance summary for the last N minutes"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        # Filter recent metrics
        recent_requests = [m for m in self.request_metrics if m.timestamp > cutoff_time]
        recent_db_ops = [m for m in self.database_metrics if m.timestamp > cutoff_time]
        recent_system = [m for m in self.system_metrics if m.timestamp > cutoff_time]
        recent_alerts = [a for a in self.performance_alerts if a["timestamp"] > cutoff_time]
        
        # Calculate statistics
        request_stats = self._calculate_request_stats(recent_requests)
        database_stats = self._calculate_database_stats(recent_db_ops)
        system_stats = self._calculate_system_stats(recent_system)
        
        return {
            "timeframe_minutes": minutes,
            "timestamp": datetime.utcnow(),
            "requests": request_stats,
            "database": database_stats,
            "system": system_stats,
            "alerts": {
                "count": len(recent_alerts),
                "by_severity": self._group_alerts_by_severity(recent_alerts),
                "recent": recent_alerts[-5:]  # Last 5 alerts
            },
            "health_score": self._calculate_health_score(request_stats, database_stats, system_stats, recent_alerts)
        }
    
    def _calculate_request_stats(self, requests: List[RequestMetrics]) -> Dict[str, Any]:
        """Calculate request statistics"""
        if not requests:
            return {"total": 0, "avg_response_time_ms": 0, "error_rate": 0}
        
        total_requests = len(requests)
        avg_response_time = sum(r.response_time_ms for r in requests) / total_requests
        error_requests = sum(1 for r in requests if r.status_code >= 400)
        error_rate = (error_requests / total_requests) * 100
        
        # Group by endpoint
        endpoint_stats = defaultdict(lambda: {"count": 0, "total_time": 0, "errors": 0})
        for req in requests:
            key = f"{req.method} {req.path}"
            endpoint_stats[key]["count"] += 1
            endpoint_stats[key]["total_time"] += req.response_time_ms
            if req.status_code >= 400:
                endpoint_stats[key]["errors"] += 1
        
        # Calculate per-endpoint averages
        for stats in endpoint_stats.values():
            stats["avg_response_time_ms"] = stats["total_time"] / stats["count"]
            stats["error_rate"] = (stats["errors"] / stats["count"]) * 100
        
        return {
            "total": total_requests,
            "avg_response_time_ms": round(avg_response_time, 2),
            "error_rate": round(error_rate, 2),
            "slowest_endpoints": sorted(
                [(k, v["avg_response_time_ms"]) for k, v in endpoint_stats.items()],
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }
    
    def _calculate_database_stats(self, db_ops: List[DatabaseMetrics]) -> Dict[str, Any]:
        """Calculate database statistics"""
        if not db_ops:
            return {"total_queries": 0, "avg_execution_time_ms": 0, "slow_queries": 0}
        
        total_queries = len(db_ops)
        avg_execution_time = sum(op.execution_time_ms for op in db_ops) / total_queries
        slow_queries = sum(1 for op in db_ops if op.execution_time_ms > self.slow_query_threshold_ms)
        
        # Group by query type
        query_type_stats = defaultdict(lambda: {"count": 0, "total_time": 0})
        for op in db_ops:
            query_type_stats[op.query_type]["count"] += 1
            query_type_stats[op.query_type]["total_time"] += op.execution_time_ms
        
        return {
            "total_queries": total_queries,
            "avg_execution_time_ms": round(avg_execution_time, 2),
            "slow_queries": slow_queries,
            "slow_query_rate": round((slow_queries / total_queries) * 100, 2),
            "by_query_type": {
                k: {
                    "count": v["count"],
                    "avg_time_ms": round(v["total_time"] / v["count"], 2)
                }
                for k, v in query_type_stats.items()
            }
        }
    
    def _calculate_system_stats(self, system_metrics: List[SystemMetrics]) -> Dict[str, Any]:
        """Calculate system resource statistics"""
        if not system_metrics:
            return {"avg_cpu_percent": 0, "avg_memory_percent": 0, "avg_connections": 0}
        
        total_samples = len(system_metrics)
        avg_cpu = sum(m.cpu_percent for m in system_metrics) / total_samples
        avg_memory = sum(m.memory_percent for m in system_metrics) / total_samples
        avg_connections = sum(m.active_connections for m in system_metrics) / total_samples
        max_memory_mb = max(m.memory_used_mb for m in system_metrics)
        
        return {
            "avg_cpu_percent": round(avg_cpu, 2),
            "avg_memory_percent": round(avg_memory, 2),
            "max_memory_used_mb": round(max_memory_mb, 2),
            "avg_connections": round(avg_connections, 2)
        }
    
    def _group_alerts_by_severity(self, alerts: List[Dict]) -> Dict[str, int]:
        """Group alerts by severity"""
        severity_counts = defaultdict(int)
        for alert in alerts:
            severity_counts[alert.get("severity", "unknown")] += 1
        return dict(severity_counts)
    
    def _calculate_health_score(self, request_stats: Dict, db_stats: Dict, 
                               system_stats: Dict, alerts: List[Dict]) -> float:
        """Calculate overall health score (0-100)"""
        score = 100.0
        
        # Deduct for high error rates
        error_rate = request_stats.get("error_rate", 0)
        if error_rate > 5:
            score -= min(error_rate * 2, 20)
        
        # Deduct for slow responses
        avg_response_time = request_stats.get("avg_response_time_ms", 0)
        if avg_response_time > 1000:
            score -= min((avg_response_time - 1000) / 100, 15)
        
        # Deduct for slow database queries
        slow_query_rate = db_stats.get("slow_query_rate", 0)
        if slow_query_rate > 10:
            score -= min(slow_query_rate, 20)
        
        # Deduct for high resource usage
        cpu_percent = system_stats.get("avg_cpu_percent", 0)
        memory_percent = system_stats.get("avg_memory_percent", 0)
        
        if cpu_percent > 80:
            score -= min((cpu_percent - 80) * 2, 15)
        if memory_percent > 85:
            score -= min((memory_percent - 85) * 2, 15)
        
        # Deduct for critical alerts
        critical_alerts = sum(1 for a in alerts if a.get("severity") == "critical")
        score -= critical_alerts * 10
        
        return max(0.0, min(100.0, score))


# Global APM collector instance
_apm_collector: Optional[APMCollector] = None


def get_apm_collector() -> APMCollector:
    """Get global APM collector instance"""
    global _apm_collector
    if _apm_collector is None:
        _apm_collector = APMCollector()
    return _apm_collector


async def collect_system_metrics():
    """Collect current system metrics"""
    try:
        # Get CPU and memory stats
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get database connection count
        active_connections = 0
        try:
            async with db_manager.get_session() as session:
                result = await session.execute(
                    text("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
                )
                active_connections = result.scalar() or 0
        except Exception as e:
            logger.warning("Failed to get database connection count", error=str(e))
        
        metrics = SystemMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_mb=memory.used / (1024 * 1024),
            disk_usage_percent=disk.percent,
            active_connections=active_connections
        )
        
        get_apm_collector().record_system_metrics(metrics)
        return metrics
        
    except Exception as e:
        logger.error("Failed to collect system metrics", error=str(e))
        return None


@asynccontextmanager
async def monitor_database_operation(query_type: str, table_name: Optional[str] = None):
    """Context manager for monitoring database operations"""
    start_time = time.time()
    error_msg = None
    
    try:
        yield
    except Exception as e:
        error_msg = str(e)
        raise
    finally:
        execution_time_ms = (time.time() - start_time) * 1000
        
        metrics = DatabaseMetrics(
            query_type=query_type,
            execution_time_ms=execution_time_ms,
            table_name=table_name,
            error=error_msg
        )
        
        get_apm_collector().record_database_operation(metrics)


def monitor_request(func: Callable) -> Callable:
    """Decorator for monitoring HTTP requests"""
    @wraps(func)
    async def async_wrapper(request, *args, **kwargs):
        start_time = time.time()
        status_code = 200
        error_message = None
        
        try:
            response = await func(request, *args, **kwargs)
            if hasattr(response, 'status_code'):
                status_code = response.status_code
            return response
        except Exception as e:
            status_code = 500
            error_message = str(e)
            raise
        finally:
            response_time_ms = (time.time() - start_time) * 1000
            
            metrics = RequestMetrics(
                method=request.method,
                path=str(request.url.path),
                status_code=status_code,
                response_time_ms=response_time_ms,
                timestamp=datetime.utcnow(),
                error_message=error_message
            )
            
            get_apm_collector().record_request(metrics)
    
    @wraps(func)
    def sync_wrapper(request, *args, **kwargs):
        start_time = time.time()
        status_code = 200
        error_message = None
        
        try:
            response = func(request, *args, **kwargs)
            if hasattr(response, 'status_code'):
                status_code = response.status_code
            return response
        except Exception as e:
            status_code = 500
            error_message = str(e)
            raise
        finally:
            response_time_ms = (time.time() - start_time) * 1000
            
            metrics = RequestMetrics(
                method=request.method,
                path=str(request.url.path),
                status_code=status_code,
                response_time_ms=response_time_ms,
                timestamp=datetime.utcnow(),
                error_message=error_message
            )
            
            get_apm_collector().record_request(metrics)
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper
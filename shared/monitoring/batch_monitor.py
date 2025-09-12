"""
Batch Processing Monitor with Alerting System
Monitors import batch processes and triggers alerts for failures or performance issues
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

import structlog
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.connection import get_db_session
from shared.database.models import ImportBatch
from .metrics import get_metrics_collector

logger = structlog.get_logger(__name__)


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(str, Enum):
    BATCH_FAILURE = "batch_failure"
    HIGH_FAILURE_RATE = "high_failure_rate"
    LONG_PROCESSING_TIME = "long_processing_time"
    STUCK_BATCH = "stuck_batch"
    RETRY_EXHAUSTED = "retry_exhausted"
    SYSTEM_DEGRADATION = "system_degradation"


@dataclass
class BatchAlert:
    """Alert for batch processing issues"""
    
    id: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    batch_id: Optional[str] = None
    source_type: Optional[str] = None
    created_at: datetime = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)


@dataclass
class BatchMonitorStats:
    """Batch processing monitoring statistics"""
    
    total_batches_24h: int
    successful_batches_24h: int
    failed_batches_24h: int
    retrying_batches: int
    stuck_batches: int
    avg_processing_time_minutes: float
    failure_rate_percentage: float
    alerts_generated: int


class BatchProcessingMonitor:
    """Monitor for batch processing operations with alerting"""
    
    def __init__(self):
        self.logger = logger.bind(service="batch_monitor")
        self.alert_callbacks: List = []
        self.monitoring_thresholds = {
            "max_processing_time_hours": 2,
            "failure_rate_threshold": 0.15,  # 15%
            "stuck_batch_threshold_hours": 4,
            "max_retry_failures": 5
        }
        
    def register_alert_callback(self, callback):
        """Register a callback function to handle alerts"""
        self.alert_callbacks.append(callback)
        
    async def _trigger_alert(self, alert: BatchAlert):
        """Trigger an alert by calling all registered callbacks"""
        self.logger.warning(
            "Batch processing alert triggered",
            alert_type=alert.alert_type,
            severity=alert.severity,
            title=alert.title,
            batch_id=alert.batch_id
        )
        
        # Call all registered alert handlers
        for callback in self.alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                self.logger.error(f"Alert callback failed: {e}")
        
        # Record alert in metrics
        metrics = get_metrics_collector()
        metrics.increment_counter(
            "batch_alerts_total",
            labels={"type": alert.alert_type, "severity": alert.severity}
        )
    
    async def monitor_batch_processing(self) -> BatchMonitorStats:
        """Monitor current batch processing status and generate alerts"""
        
        async with get_db_session() as session:
            try:
                # Get statistics for the last 24 hours
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
                
                # Total batches in last 24h
                total_count = await session.scalar(
                    select(func.count(ImportBatch.id))
                    .where(ImportBatch.created_at >= cutoff_time)
                )
                
                # Successful batches
                successful_count = await session.scalar(
                    select(func.count(ImportBatch.id))
                    .where(and_(
                        ImportBatch.created_at >= cutoff_time,
                        ImportBatch.status == "completed"
                    ))
                )
                
                # Failed batches
                failed_count = await session.scalar(
                    select(func.count(ImportBatch.id))
                    .where(and_(
                        ImportBatch.created_at >= cutoff_time,
                        ImportBatch.status == "failed"
                    ))
                )
                
                # Currently retrying batches
                retrying_count = await session.scalar(
                    select(func.count(ImportBatch.id))
                    .where(ImportBatch.status == "retrying")
                )
                
                # Average processing time (in minutes)
                avg_processing_time = await session.scalar(
                    select(func.avg(
                        func.extract('epoch', ImportBatch.completed_at - ImportBatch.started_at) / 60
                    ))
                    .where(and_(
                        ImportBatch.completed_at.isnot(None),
                        ImportBatch.started_at.isnot(None),
                        ImportBatch.created_at >= cutoff_time
                    ))
                ) or 0.0
                
                # Calculate failure rate
                failure_rate = (failed_count / max(total_count, 1)) * 100
                
                # Find stuck batches (processing for too long)
                stuck_cutoff = datetime.now(timezone.utc) - timedelta(
                    hours=self.monitoring_thresholds["stuck_batch_threshold_hours"]
                )
                stuck_batches_result = await session.execute(
                    select(ImportBatch)
                    .where(and_(
                        ImportBatch.status.in_(["processing", "retrying"]),
                        ImportBatch.started_at < stuck_cutoff
                    ))
                )
                stuck_batches = stuck_batches_result.scalars().all()
                
                # Check for alerts
                alerts_generated = 0
                
                # Alert 1: High failure rate
                if failure_rate > self.monitoring_thresholds["failure_rate_threshold"] * 100:
                    await self._trigger_alert(BatchAlert(
                        id=f"high_failure_rate_{datetime.now().timestamp()}",
                        alert_type=AlertType.HIGH_FAILURE_RATE,
                        severity=AlertSeverity.HIGH if failure_rate > 30 else AlertSeverity.MEDIUM,
                        title=f"High batch failure rate: {failure_rate:.1f}%",
                        message=f"Batch failure rate of {failure_rate:.1f}% exceeds threshold of {self.monitoring_thresholds['failure_rate_threshold']*100}%",
                        metadata={
                            "failure_rate": failure_rate,
                            "total_batches": total_count,
                            "failed_batches": failed_count,
                            "threshold": self.monitoring_thresholds["failure_rate_threshold"] * 100
                        }
                    ))
                    alerts_generated += 1
                
                # Alert 2: Stuck batches
                if stuck_batches:
                    for batch in stuck_batches:
                        await self._trigger_alert(BatchAlert(
                            id=f"stuck_batch_{batch.id}",
                            alert_type=AlertType.STUCK_BATCH,
                            severity=AlertSeverity.HIGH,
                            title=f"Batch stuck in processing",
                            message=f"Batch {batch.id} has been {batch.status} for over {self.monitoring_thresholds['stuck_batch_threshold_hours']} hours",
                            batch_id=str(batch.id),
                            source_type=batch.source_type,
                            metadata={
                                "started_at": batch.started_at.isoformat() if batch.started_at else None,
                                "status": batch.status,
                                "hours_processing": self.monitoring_thresholds["stuck_batch_threshold_hours"]
                            }
                        ))
                        alerts_generated += 1
                
                # Alert 3: Long average processing time
                if avg_processing_time > self.monitoring_thresholds["max_processing_time_hours"] * 60:
                    await self._trigger_alert(BatchAlert(
                        id=f"long_processing_{datetime.now().timestamp()}",
                        alert_type=AlertType.LONG_PROCESSING_TIME,
                        severity=AlertSeverity.MEDIUM,
                        title=f"Long average processing time",
                        message=f"Average batch processing time of {avg_processing_time:.1f} minutes exceeds threshold",
                        metadata={
                            "avg_processing_time_minutes": avg_processing_time,
                            "threshold_minutes": self.monitoring_thresholds["max_processing_time_hours"] * 60
                        }
                    ))
                    alerts_generated += 1
                
                # Alert 4: Retry exhausted batches
                retry_exhausted_result = await session.execute(
                    select(ImportBatch)
                    .where(and_(
                        ImportBatch.status == "failed",
                        ImportBatch.retry_count >= ImportBatch.max_retries,
                        ImportBatch.updated_at >= cutoff_time
                    ))
                )
                retry_exhausted_batches = retry_exhausted_result.scalars().all()
                
                for batch in retry_exhausted_batches:
                    await self._trigger_alert(BatchAlert(
                        id=f"retry_exhausted_{batch.id}",
                        alert_type=AlertType.RETRY_EXHAUSTED,
                        severity=AlertSeverity.HIGH,
                        title=f"Batch retry attempts exhausted",
                        message=f"Batch {batch.id} has failed after {batch.retry_count} retry attempts",
                        batch_id=str(batch.id),
                        source_type=batch.source_type,
                        metadata={
                            "retry_count": batch.retry_count,
                            "max_retries": batch.max_retries,
                            "last_error": batch.last_error
                        }
                    ))
                    alerts_generated += 1
                
                # Create stats summary
                stats = BatchMonitorStats(
                    total_batches_24h=total_count or 0,
                    successful_batches_24h=successful_count or 0,
                    failed_batches_24h=failed_count or 0,
                    retrying_batches=retrying_count or 0,
                    stuck_batches=len(stuck_batches),
                    avg_processing_time_minutes=float(avg_processing_time),
                    failure_rate_percentage=failure_rate,
                    alerts_generated=alerts_generated
                )
                
                # Update metrics
                metrics = get_metrics_collector()
                metrics.set_gauge("batch_processing_total_24h", total_count or 0)
                metrics.set_gauge("batch_processing_successful_24h", successful_count or 0)
                metrics.set_gauge("batch_processing_failed_24h", failed_count or 0)
                metrics.set_gauge("batch_processing_failure_rate", failure_rate)
                metrics.set_gauge("batch_processing_avg_time_minutes", avg_processing_time)
                metrics.set_gauge("batch_processing_stuck_count", len(stuck_batches))
                
                self.logger.info(
                    "Batch processing monitoring completed",
                    stats=stats.__dict__
                )
                
                return stats
                
            except Exception as e:
                self.logger.error(f"Error in batch monitoring: {e}", exc_info=True)
                raise

    async def check_specific_batch(self, batch_id: str) -> Optional[BatchAlert]:
        """Check a specific batch for issues and return alert if needed"""
        
        async with get_db_session() as session:
            try:
                batch = await session.get(ImportBatch, batch_id)
                if not batch:
                    return None
                
                current_time = datetime.now(timezone.utc)
                
                # Check if batch is stuck
                if batch.status in ["processing", "retrying"] and batch.started_at:
                    processing_duration = current_time - batch.started_at
                    if processing_duration.total_seconds() > self.monitoring_thresholds["stuck_batch_threshold_hours"] * 3600:
                        return BatchAlert(
                            id=f"stuck_batch_check_{batch_id}",
                            alert_type=AlertType.STUCK_BATCH,
                            severity=AlertSeverity.HIGH,
                            title=f"Batch {batch_id} is stuck",
                            message=f"Batch has been {batch.status} for {processing_duration}",
                            batch_id=batch_id,
                            source_type=batch.source_type
                        )
                
                # Check if retries are exhausted
                if batch.status == "failed" and batch.retry_count >= (batch.max_retries or 0):
                    return BatchAlert(
                        id=f"retry_exhausted_check_{batch_id}",
                        alert_type=AlertType.RETRY_EXHAUSTED,
                        severity=AlertSeverity.HIGH,
                        title=f"Batch {batch_id} retries exhausted",
                        message=f"Batch failed after {batch.retry_count} attempts",
                        batch_id=batch_id,
                        source_type=batch.source_type,
                        metadata={"last_error": batch.last_error}
                    )
                
                return None
                
            except Exception as e:
                self.logger.error(f"Error checking specific batch {batch_id}: {e}")
                return None

    async def get_batch_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive batch processing health summary"""
        
        async with get_db_session() as session:
            try:
                # Get various time windows for analysis
                now = datetime.now(timezone.utc)
                windows = {
                    "1h": now - timedelta(hours=1),
                    "6h": now - timedelta(hours=6),
                    "24h": now - timedelta(hours=24),
                    "7d": now - timedelta(days=7)
                }
                
                health_summary = {
                    "overall_status": "healthy",
                    "windows": {}
                }
                
                for window_name, cutoff_time in windows.items():
                    # Get batch statistics for this window
                    total = await session.scalar(
                        select(func.count(ImportBatch.id))
                        .where(ImportBatch.created_at >= cutoff_time)
                    ) or 0
                    
                    completed = await session.scalar(
                        select(func.count(ImportBatch.id))
                        .where(and_(
                            ImportBatch.created_at >= cutoff_time,
                            ImportBatch.status == "completed"
                        ))
                    ) or 0
                    
                    failed = await session.scalar(
                        select(func.count(ImportBatch.id))
                        .where(and_(
                            ImportBatch.created_at >= cutoff_time,
                            ImportBatch.status == "failed"
                        ))
                    ) or 0
                    
                    success_rate = (completed / max(total, 1)) * 100
                    failure_rate = (failed / max(total, 1)) * 100
                    
                    health_summary["windows"][window_name] = {
                        "total_batches": total,
                        "completed_batches": completed,
                        "failed_batches": failed,
                        "success_rate": round(success_rate, 2),
                        "failure_rate": round(failure_rate, 2)
                    }
                
                # Determine overall health status
                recent_failure_rate = health_summary["windows"]["6h"]["failure_rate"]
                if recent_failure_rate > 30:
                    health_summary["overall_status"] = "critical"
                elif recent_failure_rate > 15:
                    health_summary["overall_status"] = "degraded"
                elif recent_failure_rate > 5:
                    health_summary["overall_status"] = "warning"
                
                return health_summary
                
            except Exception as e:
                self.logger.error(f"Error getting batch health summary: {e}")
                return {"overall_status": "unknown", "error": str(e)}

    async def run_continuous_monitoring(self, interval_seconds: int = 300):
        """Run continuous monitoring loop with specified interval"""
        
        self.logger.info(f"Starting continuous batch monitoring with {interval_seconds}s interval")
        
        while True:
            try:
                await self.monitor_batch_processing()
                await asyncio.sleep(interval_seconds)
                
            except asyncio.CancelledError:
                self.logger.info("Batch monitoring cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in continuous monitoring: {e}", exc_info=True)
                await asyncio.sleep(interval_seconds)  # Continue monitoring despite errors


# Global monitor instance
_batch_monitor = BatchProcessingMonitor()


def get_batch_monitor() -> BatchProcessingMonitor:
    """Get the global batch processing monitor instance"""
    return _batch_monitor


# Default alert handlers
async def log_alert_handler(alert: BatchAlert):
    """Default alert handler that logs alerts"""
    logger.warning(
        f"BATCH ALERT: {alert.title}",
        alert_type=alert.alert_type,
        severity=alert.severity,
        message=alert.message,
        batch_id=alert.batch_id,
        metadata=alert.metadata
    )


async def metrics_alert_handler(alert: BatchAlert):
    """Alert handler that updates metrics"""
    metrics = get_metrics_collector()
    metrics.increment_counter(
        "batch_processing_alerts",
        labels={
            "type": alert.alert_type,
            "severity": alert.severity,
            "source_type": alert.source_type or "unknown"
        }
    )


# Register default handlers
_batch_monitor.register_alert_callback(log_alert_handler)
_batch_monitor.register_alert_callback(metrics_alert_handler)
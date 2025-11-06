"""
Batch Processing Monitor API Router
Exposes batch monitoring capabilities via REST API
"""

from typing import Dict, Any
from datetime import datetime

import structlog
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from .batch_monitor import get_batch_monitor, BatchAlert

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/monitoring/batch", tags=["Batch Monitoring"])


class BatchHealthResponse(BaseModel):
    """Response model for batch health check"""

    overall_status: str
    windows: Dict[str, Dict[str, Any]]
    timestamp: datetime


class BatchMonitorStatsResponse(BaseModel):
    """Response model for batch monitoring statistics"""

    total_batches_24h: int
    successful_batches_24h: int
    failed_batches_24h: int
    retrying_batches: int
    stuck_batches: int
    avg_processing_time_minutes: float
    failure_rate_percentage: float
    alerts_generated: int
    timestamp: datetime


class BatchAlertResponse(BaseModel):
    """Response model for batch alerts"""

    id: str
    alert_type: str
    severity: str
    title: str
    message: str
    batch_id: str = None
    source_type: str = None
    created_at: datetime
    metadata: Dict[str, Any] = None


@router.get("/health", response_model=BatchHealthResponse)
async def get_batch_health():
    """
    Get comprehensive batch processing health status across multiple time windows
    """
    try:
        monitor = get_batch_monitor()
        health_data = await monitor.get_batch_health_summary()

        return BatchHealthResponse(
            overall_status=health_data["overall_status"],
            windows=health_data.get("windows", {}),
            timestamp=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Failed to get batch health: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve batch health: {str(e)}")


@router.get("/stats", response_model=BatchMonitorStatsResponse)
async def get_batch_monitoring_stats():
    """
    Get detailed batch processing monitoring statistics and trigger alerts if needed
    """
    try:
        monitor = get_batch_monitor()
        stats = await monitor.monitor_batch_processing()

        return BatchMonitorStatsResponse(
            total_batches_24h=stats.total_batches_24h,
            successful_batches_24h=stats.successful_batches_24h,
            failed_batches_24h=stats.failed_batches_24h,
            retrying_batches=stats.retrying_batches,
            stuck_batches=stats.stuck_batches,
            avg_processing_time_minutes=stats.avg_processing_time_minutes,
            failure_rate_percentage=stats.failure_rate_percentage,
            alerts_generated=stats.alerts_generated,
            timestamp=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Failed to get batch monitoring stats: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve monitoring stats: {str(e)}"
        )


@router.get("/batch/{batch_id}/check")
async def check_specific_batch(batch_id: str):
    """
    Check a specific batch for issues and return alert information if any
    """
    try:
        monitor = get_batch_monitor()
        alert = await monitor.check_specific_batch(batch_id)

        if alert:
            return {
                "has_issues": True,
                "alert": {
                    "id": alert.id,
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "title": alert.title,
                    "message": alert.message,
                    "created_at": alert.created_at.isoformat(),
                    "metadata": alert.metadata,
                },
            }
        else:
            return {"has_issues": False, "message": f"Batch {batch_id} appears to be healthy"}

    except Exception as e:
        logger.error(f"Failed to check batch {batch_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check batch: {str(e)}")


@router.post("/monitoring/start")
async def start_continuous_monitoring(
    background_tasks: BackgroundTasks, interval_seconds: int = 300
):
    """
    Start continuous batch monitoring in the background
    """
    try:
        monitor = get_batch_monitor()

        # Start monitoring as a background task
        background_tasks.add_task(monitor.run_continuous_monitoring, interval_seconds)

        return {
            "status": "started",
            "message": f"Continuous batch monitoring started with {interval_seconds}s interval",
            "interval_seconds": interval_seconds,
        }

    except Exception as e:
        logger.error(f"Failed to start continuous monitoring: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start monitoring: {str(e)}")


@router.get("/alerts/test")
async def test_alert_system():
    """
    Test the alert system by generating a test alert
    """
    try:
        monitor = get_batch_monitor()

        test_alert = BatchAlert(
            id=f"test_alert_{datetime.now().timestamp()}",
            alert_type="system_test",
            severity="low",
            title="Test Alert",
            message="This is a test alert to verify the alerting system is working",
            metadata={"test": True, "generated_by": "api_endpoint"},
        )

        await monitor._trigger_alert(test_alert)

        return {
            "status": "success",
            "message": "Test alert generated successfully",
            "alert_id": test_alert.id,
        }

    except Exception as e:
        logger.error(f"Failed to generate test alert: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to test alert system: {str(e)}")


@router.get("/dashboard")
async def get_monitoring_dashboard():
    """
    Get comprehensive monitoring dashboard data for batch processing
    """
    try:
        monitor = get_batch_monitor()

        # Get health summary and current stats
        health_data = await monitor.get_batch_health_summary()
        current_stats = await monitor.monitor_batch_processing()

        return {
            "overall_health": health_data,
            "current_stats": {
                "total_batches_24h": current_stats.total_batches_24h,
                "successful_batches_24h": current_stats.successful_batches_24h,
                "failed_batches_24h": current_stats.failed_batches_24h,
                "retrying_batches": current_stats.retrying_batches,
                "stuck_batches": current_stats.stuck_batches,
                "avg_processing_time_minutes": current_stats.avg_processing_time_minutes,
                "failure_rate_percentage": current_stats.failure_rate_percentage,
                "alerts_generated": current_stats.alerts_generated,
            },
            "thresholds": {
                "max_processing_time_hours": monitor.monitoring_thresholds[
                    "max_processing_time_hours"
                ],
                "failure_rate_threshold": monitor.monitoring_thresholds["failure_rate_threshold"]
                * 100,
                "stuck_batch_threshold_hours": monitor.monitoring_thresholds[
                    "stuck_batch_threshold_hours"
                ],
                "max_retry_failures": monitor.monitoring_thresholds["max_retry_failures"],
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get monitoring dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve dashboard data: {str(e)}")

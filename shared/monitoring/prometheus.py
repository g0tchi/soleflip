"""
Prometheus metrics exporter for SoleFlipper application.
Provides Prometheus-compatible metrics endpoint.
"""

from typing import Any, Dict

import structlog
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from .metrics import get_metrics_collector

logger = structlog.get_logger(__name__)

router = APIRouter()


def format_prometheus_metrics(metrics_data: Dict[str, Any]) -> str:
    """Format metrics data in Prometheus exposition format"""
    lines = []

    # Add metadata
    lines.append("# HELP soleflip_info Application information")
    lines.append("# TYPE soleflip_info gauge")
    lines.append('soleflip_info{version="1.0.0",environment="production"} 1')

    # Add uptime
    uptime = metrics_data.get("metadata", {}).get("uptime_seconds", 0)
    lines.append("# HELP soleflip_uptime_seconds Application uptime in seconds")
    lines.append("# TYPE soleflip_uptime_seconds counter")
    lines.append(f"soleflip_uptime_seconds {uptime}")

    # Format counters
    counters = metrics_data.get("counters", {})
    for metric_name, label_values in counters.items():
        lines.append(f"# HELP soleflip_{metric_name} Counter metric")
        lines.append(f"# TYPE soleflip_{metric_name} counter")

        for label_key, value in label_values.items():
            if label_key:
                # Parse labels back from string format
                labels_str = "{" + label_key + "}"
            else:
                labels_str = ""

            lines.append(f"soleflip_{metric_name}{labels_str} {value}")

    # Format gauges
    gauges = metrics_data.get("gauges", {})
    for metric_name, value in gauges.items():
        clean_name = metric_name.replace("_", "_").lower()
        lines.append(f"# HELP soleflip_{clean_name} Gauge metric")
        lines.append(f"# TYPE soleflip_{clean_name} gauge")
        lines.append(f"soleflip_{clean_name} {value}")

    # Format histograms
    histograms = metrics_data.get("histograms", {})
    for metric_name, stats in histograms.items():
        clean_name = metric_name.replace("_", "_").lower()

        lines.append(f"# HELP soleflip_{clean_name} Histogram metric")
        lines.append(f"# TYPE soleflip_{clean_name} histogram")

        # Histogram buckets (simplified)
        buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float("inf")]
        count = stats.get("count", 0)
        total = stats.get("sum", 0)

        for bucket in buckets:
            if bucket == float("inf"):
                bucket_count = count
                lines.append(f'soleflip_{clean_name}_bucket{{le="+Inf"}} {bucket_count}')
            else:
                # Simplified bucket counting (in real implementation, track actual buckets)
                bucket_count = count
                lines.append(f'soleflip_{clean_name}_bucket{{le="{bucket}"}} {bucket_count}')

        lines.append(f"soleflip_{clean_name}_count {count}")
        lines.append(f"soleflip_{clean_name}_sum {total}")

    # Add APM-specific metrics
    apm_data = metrics_data.get("apm", {})
    if apm_data:
        # Health score
        health_score = apm_data.get("health_score", 0)
        lines.append("# HELP soleflip_health_score Overall system health score (0-100)")
        lines.append("# TYPE soleflip_health_score gauge")
        lines.append(f"soleflip_health_score {health_score}")
        
        # Request metrics
        requests = apm_data.get("requests", {})
        if requests:
            lines.append("# HELP soleflip_request_total Total number of HTTP requests")
            lines.append("# TYPE soleflip_request_total counter")
            lines.append(f"soleflip_request_total {requests.get('total', 0)}")
            
            lines.append("# HELP soleflip_request_error_rate HTTP request error rate percentage")
            lines.append("# TYPE soleflip_request_error_rate gauge")
            lines.append(f"soleflip_request_error_rate {requests.get('error_rate', 0)}")
            
            lines.append("# HELP soleflip_request_response_time_avg Average HTTP response time in milliseconds")
            lines.append("# TYPE soleflip_request_response_time_avg gauge")
            lines.append(f"soleflip_request_response_time_avg {requests.get('avg_response_time_ms', 0)}")
        
        # Database metrics
        database = apm_data.get("database", {})
        if database:
            lines.append("# HELP soleflip_database_queries_total Total number of database queries")
            lines.append("# TYPE soleflip_database_queries_total counter")
            lines.append(f"soleflip_database_queries_total {database.get('total_queries', 0)}")
            
            lines.append("# HELP soleflip_database_slow_queries Total number of slow database queries")
            lines.append("# TYPE soleflip_database_slow_queries counter")
            lines.append(f"soleflip_database_slow_queries {database.get('slow_queries', 0)}")
            
            lines.append("# HELP soleflip_database_avg_execution_time Average database query execution time in milliseconds")
            lines.append("# TYPE soleflip_database_avg_execution_time gauge")
            lines.append(f"soleflip_database_avg_execution_time {database.get('avg_execution_time_ms', 0)}")
        
        # System metrics
        system = apm_data.get("system", {})
        if system:
            lines.append("# HELP soleflip_cpu_usage_percent CPU usage percentage")
            lines.append("# TYPE soleflip_cpu_usage_percent gauge")
            lines.append(f"soleflip_cpu_usage_percent {system.get('avg_cpu_percent', 0)}")
            
            lines.append("# HELP soleflip_memory_usage_percent Memory usage percentage")
            lines.append("# TYPE soleflip_memory_usage_percent gauge")
            lines.append(f"soleflip_memory_usage_percent {system.get('avg_memory_percent', 0)}")
        
        # Alert metrics
        alerts = apm_data.get("alerts", {})
        if alerts:
            lines.append("# HELP soleflip_alerts_total Total number of active alerts")
            lines.append("# TYPE soleflip_alerts_total gauge")
            lines.append(f"soleflip_alerts_total {alerts.get('count', 0)}")

    return "\n".join(lines)


@router.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics():
    """
    Prometheus metrics endpoint with APM integration.
    Returns metrics in Prometheus exposition format.
    """
    try:
        metrics_collector = get_metrics_collector()
        metrics_data = metrics_collector.get_all_metrics()
        
        # Get APM metrics
        from shared.monitoring.apm import get_apm_collector
        apm_collector = get_apm_collector()
        apm_summary = apm_collector.get_performance_summary(minutes=5)
        
        # Merge APM metrics into main metrics
        metrics_data["apm"] = apm_summary

        prometheus_output = format_prometheus_metrics(metrics_data)

        logger.debug(
            "Metrics scraped by Prometheus with APM data",
            metrics_count=metrics_data.get("metadata", {}).get("metrics_collected", 0),
            apm_requests=apm_summary.get("requests", {}).get("total", 0),
            health_score=apm_summary.get("health_score", 0)
        )

        return prometheus_output

    except Exception as e:
        logger.error("Failed to generate Prometheus metrics", error=str(e))
        return "# Error generating metrics\n"

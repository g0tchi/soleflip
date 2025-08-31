"""
Prometheus metrics exporter for SoleFlipper application.
Provides Prometheus-compatible metrics endpoint.
"""

from typing import Any, Dict

import structlog
from fastapi import APIRouter, Response
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
    lines.append(f'soleflip_info{{version="1.0.0",environment="production"}} 1')

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

    return "\n".join(lines)


@router.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics():
    """
    Prometheus metrics endpoint.
    Returns metrics in Prometheus exposition format.
    """
    try:
        metrics_collector = get_metrics_collector()
        metrics_data = metrics_collector.get_all_metrics()

        prometheus_output = format_prometheus_metrics(metrics_data)

        logger.debug(
            "Metrics scraped by Prometheus",
            metrics_count=metrics_data.get("metadata", {}).get("metrics_collected", 0),
        )

        return prometheus_output

    except Exception as e:
        logger.error("Failed to generate Prometheus metrics", error=str(e))
        return "# Error generating metrics\n"

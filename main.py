"""
SoleFlipper API - Main Application Entry Point
Production-ready FastAPI application with proper error handling,
logging, and monitoring.
"""

from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

load_dotenv()

from datetime import datetime

from fastapi import HTTPException


# Import centralized dependencies
from shared.config.settings import get_settings
from shared.database.connection import db_manager
from shared.error_handling.exceptions import (
    SoleFlipException,
    ValidationException,
    generic_exception_handler,
    http_exception_handler,
    soleflip_exception_handler,
    validation_exception_handler,
)
from shared.logging.logger import RequestLoggingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Get application settings
    settings = get_settings()

    # Setup logging based on configuration
    from shared.logging.logger import setup_logging

    logger = setup_logging(
        log_level=settings.get_log_level(),
        enable_database_logging=settings.logging.database_logging,
        enable_json_output=(settings.logging.format == "json"),
    )
    logger.info(
        "SoleFlipper API starting up...",
        environment=settings.environment,
        version=settings.api.version,
    )

    await db_manager.initialize()
    await db_manager.run_migrations()
    logger.info("Database connection initialized and tables created")

    # Setup monitoring
    from shared.monitoring.health import setup_default_health_checks
    from shared.monitoring.metrics import get_metrics_collector
    from shared.monitoring.batch_monitor import get_batch_monitor
    from shared.monitoring.apm import get_apm_collector, collect_system_metrics
    from shared.monitoring.alerting import get_alert_manager, start_alert_monitoring
    import asyncio
    import os

    await setup_default_health_checks(db_manager)
    metrics_collector = get_metrics_collector()
    metrics_collector.start_collection()
    
    # Initialize APM system
    apm_collector = get_apm_collector()
    logger.info("APM system initialized")
    
    # Advanced health monitoring temporarily disabled
    logger.info("Basic health monitoring active")
    
    # Initialize alerting system
    alert_manager = get_alert_manager()
    logger.info("Alerting system initialized")
    
    # Initialize batch monitoring
    batch_monitor = get_batch_monitor()
    
    # Define system metrics collection task
    async def _start_system_metrics_collection():
        """Background task for collecting system metrics"""
        while True:
            try:
                await collect_system_metrics()
                await asyncio.sleep(30)  # Collect every 30 seconds
            except Exception as e:
                logger.error("System metrics collection failed", error=str(e))
                await asyncio.sleep(60)  # Wait longer on error
    
    # Start continuous monitoring tasks
    asyncio.create_task(batch_monitor.run_continuous_monitoring(interval_seconds=300))
    asyncio.create_task(_start_system_metrics_collection())
    asyncio.create_task(start_alert_monitoring(check_interval_seconds=60))

    # Initialize event-driven domain communication
    from domains.integration.events import get_integration_event_handler
    from domains.products.events import get_product_event_handler
    from domains.inventory.events import get_inventory_event_handler
    
    # Initialize all event handlers
    get_integration_event_handler()
    get_product_event_handler() 
    get_inventory_event_handler()

    # Initialize performance optimizations
    from shared.performance import initialize_cache, get_database_optimizer
    from shared.auth.token_blacklist import initialize_token_blacklist
    
    # Initialize cache system
    redis_url = os.getenv("REDIS_URL")  # Optional Redis connection
    await initialize_cache(redis_url)
    
    # Initialize JWT token blacklist system
    try:
        # Try to reuse Redis connection for token blacklist
        redis_client = None
        if redis_url:
            import redis.asyncio as redis
            redis_client = redis.from_url(redis_url)
        await initialize_token_blacklist(redis_client)
    except ImportError:
        # Redis not available, use in-memory blacklist only
        await initialize_token_blacklist()
    
    # Setup database performance indexes (temporarily disabled)
    # db_optimizer = get_database_optimizer()
    # async with db_manager.get_session() as session:
    #     await db_optimizer.create_performance_indexes(session)

    logger.info("Monitoring, health checks, batch monitoring, event system, performance optimizations, and security systems initialized")

    yield

    logger.info("SoleFlipper API shutting down...")
    
    # Shutdown security systems
    from shared.auth.token_blacklist import shutdown_token_blacklist
    await shutdown_token_blacklist()
    
    metrics_collector.stop_collection()
    await db_manager.close()
    logger.info("Database connections closed, security systems shutdown")


class APIInfo(BaseModel):
    name: str
    version: str


# Get settings for FastAPI configuration
settings = get_settings()

app = FastAPI(
    title=settings.api.title,
    version=settings.api.version,
    description=settings.api.description,
    # Production security: Disable API docs
    openapi_url=None if settings.environment == "production" else settings.api.openapi_url,
    docs_url=None if settings.environment == "production" else settings.api.docs_url,
    redoc_url=None if settings.environment == "production" else settings.api.redoc_url,
    lifespan=lifespan,
)

# Add security middleware
from shared.security.middleware import add_security_middleware

add_security_middleware(app, settings)

# Add compression middleware for better bandwidth efficiency
from shared.middleware.compression import setup_compression_middleware
from shared.middleware.etag import setup_etag_middleware

# First add compression middleware, then ETag middleware
# This ensures ETags are calculated from compressed responses
setup_compression_middleware(app, {
    "minimum_size": 1000,  # Compress responses >= 1KB
    "compression_level": 6,  # Balanced speed vs compression
    "exclude_paths": ["/health", "/metrics", "/docs", "/openapi.json", "/health/ready", "/health/live"]
})

setup_etag_middleware(app, {
    "weak_etags": True,  # Better performance
    "exclude_paths": ["/health", "/metrics", "/docs", "/openapi.json", "/health/ready", "/health/live"]
})

# Add APM request monitoring middleware
from shared.monitoring.apm import monitor_request
from fastapi import Request
import time

@app.middleware("http")
async def apm_middleware(request: Request, call_next):
    """APM middleware to automatically track all HTTP requests"""
    from shared.monitoring.apm import get_apm_collector, RequestMetrics
    
    start_time = time.time()
    status_code = 200
    error_message = None
    
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception as e:
        status_code = 500
        error_message = str(e)
        raise
    finally:
        response_time_ms = (time.time() - start_time) * 1000
        
        # Record request metrics
        metrics = RequestMetrics(
            method=request.method,
            path=str(request.url.path),
            status_code=status_code,
            response_time_ms=response_time_ms,
            timestamp=datetime.utcnow(),
            error_message=error_message
        )
        
        get_apm_collector().record_request(metrics)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.security.cors_origins,
    allow_credentials=True,
    allow_methods=settings.security.cors_methods,
    allow_headers=settings.security.cors_headers,
)

# Add exception handlers
app.add_exception_handler(SoleFlipException, soleflip_exception_handler)
app.add_exception_handler(ValidationException, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# from domains.admin.api.router import router as admin_router  # REMOVED: Security risk in production
from domains.analytics.api.router import router as analytics_router
from domains.auth.api.router import router as auth_router
from domains.dashboard.api.router import router as dashboard_router
from domains.integration.api.upload_router import router as upload_router

# Include API routers
from domains.integration.api.webhooks import router as webhook_router
from domains.integration.api.quickflip_router import router as quickflip_router
from domains.inventory.api.router import router as inventory_router
from domains.orders.api.router import router as orders_router

# Using real router for production-ready pricing features
from domains.pricing.api.router import router as pricing_router
from domains.products.api.router import router as products_router

# Monitoring routers
from shared.monitoring.prometheus import router as prometheus_router
# from shared.monitoring.batch_monitor_router import router as batch_monitor_router  # REMOVED: Development-only

# Authentication routes (public)
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(webhook_router, prefix="/api/v1/integration", tags=["Integration"])
app.include_router(
    upload_router, prefix="/api/v1/integration", tags=["Integration"]
)  # Prefix is the same
app.include_router(quickflip_router, prefix="/api/v1/quickflip", tags=["QuickFlip"])
app.include_router(orders_router, prefix="/api/v1/orders", tags=["Orders"])
app.include_router(products_router, prefix="/api/v1/products", tags=["Products"])
app.include_router(inventory_router, prefix="/api/v1/inventory", tags=["Inventory"])
app.include_router(dashboard_router, prefix="/api/v1/dashboard", tags=["Dashboard"])
# app.include_router(admin_router, prefix="/api/v1/admin", tags=["Admin"])  # REMOVED: Security risk
app.include_router(pricing_router, prefix="/api/v1/pricing", tags=["Pricing"])
app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["Analytics"])
# Monitoring endpoints
app.include_router(prometheus_router, tags=["Monitoring"])
# app.include_router(batch_monitor_router, tags=["Batch Monitoring"])  # REMOVED: Development-only


# Root endpoint removed for production security


@app.get("/health", tags=["System"])
async def health_check():
    """Comprehensive health check endpoint with APM integration"""
    from shared.monitoring.health import get_health_manager
    # from shared.monitoring.advanced_health import get_advanced_health_manager
    from shared.monitoring.apm import get_apm_collector

    health_manager = get_health_manager()
    # advanced_health = get_advanced_health_manager()
    apm_collector = get_apm_collector()
    
    # Get basic health status
    health_status = await health_manager.get_overall_health()
    
    # Advanced health checks temporarily disabled
    advanced_status = {"overall_status": "healthy", "startup_checks": {}, "component_health": {}}
    
    # Get APM performance summary (last 5 minutes)
    performance_summary = apm_collector.get_performance_summary(minutes=5)

    return {
        "status": health_status["status"],
        "timestamp": health_status["timestamp"],
        "version": settings.api.version,
        "environment": settings.environment,
        "uptime_seconds": health_status["uptime_seconds"],
        "checks_summary": health_status["checks"],
        "components": health_status["components"],
        "advanced_health": {
            "overall_status": advanced_status["overall_status"],
            "startup_checks": advanced_status["startup_checks"],
            "component_health": advanced_status["component_health"]
        },
        "performance": {
            "health_score": performance_summary["health_score"],
            "requests": performance_summary["requests"],
            "database": performance_summary["database"],
            "system": performance_summary["system"],
            "alerts_count": performance_summary["alerts"]["count"]
        }
    }


# Metrics endpoint moved to Prometheus router only


# APM metrics endpoint removed - use external APM tools


# @app.get("/alerts", tags=["System"])  # REMOVED: Development-only
async def get_alerts():
    """Get current system alerts and alerting statistics"""
    from shared.monitoring.alerting import get_alert_manager
    
    alert_manager = get_alert_manager()
    
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "active_alerts": [
            {
                "rule_name": alert.rule_name,
                "severity": alert.severity.value,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat() + "Z",
                "details": alert.details
            }
            for alert in alert_manager.get_active_alerts()
        ],
        "alert_stats": alert_manager.get_alert_stats(hours=24),
        "rule_count": len(alert_manager.rules),
        "enabled_rules": len([rule for rule in alert_manager.rules.values() if rule.enabled])
    }


# @app.get("/alerts/history", tags=["System"])  # REMOVED: Development-only
async def get_alert_history(hours: int = 24):
    """Get alert history for the specified time period"""
    from shared.monitoring.alerting import get_alert_manager
    
    if hours > 168:  # Limit to 1 week
        hours = 168
    
    alert_manager = get_alert_manager()
    history = alert_manager.get_alert_history(hours=hours)
    
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "timeframe_hours": hours,
        "total_alerts": len(history),
        "alerts": [
            {
                "rule_name": alert.rule_name,
                "severity": alert.severity.value,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat() + "Z",
                "resolved": alert.resolved,
                "resolved_at": alert.resolved_at.isoformat() + "Z" if alert.resolved_at else None,
                "duration_minutes": round(
                    ((alert.resolved_at or datetime.utcnow()) - alert.timestamp).total_seconds() / 60, 2
                )
            }
            for alert in history
        ]
    }


@app.get("/health/ready", tags=["System"])
async def readiness_check():
    """Kubernetes readiness probe endpoint"""
    from shared.monitoring.health import CheckType, get_health_manager

    health_manager = get_health_manager()
    results = await health_manager.run_checks(check_types=[CheckType.READINESS])

    # Service is ready if all readiness checks pass
    is_ready = all(result.status == "healthy" for result in results.values())
    status_code = 200 if is_ready else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if is_ready else "not_ready",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "checks": {name: result.status for name, result in results.items()},
        },
    )


@app.get("/health/live", tags=["System"])
async def liveness_check():
    """Kubernetes liveness probe endpoint"""
    from shared.monitoring.health import CheckType, get_health_manager

    health_manager = get_health_manager()
    results = await health_manager.run_checks(check_types=[CheckType.LIVENESS])

    # Service is alive if any liveness check passes (more lenient)
    is_alive = any(result.status in ["healthy", "degraded"] for result in results.values())
    status_code = 200 if is_alive else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "alive" if is_alive else "dead",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "checks": {name: result.status for name, result in results.items()},
        },
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.reload,
        workers=settings.api.workers if not settings.api.reload else 1,
    )

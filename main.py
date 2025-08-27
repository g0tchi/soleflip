"""
SoleFlipper API - Main Application Entry Point
Production-ready FastAPI application with proper error handling,
logging, and monitoring.
"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager
import uvicorn
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv

load_dotenv()

from shared.database.connection import get_db_session, db_manager
from domains.inventory.services.inventory_service import InventoryService
from shared.error_handling.exceptions import (
    SoleFlipException,
    ValidationException,
    soleflip_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
    http_exception_handler
)
from shared.logging.logger import RequestLoggingMiddleware
from shared.config.settings import get_settings
from fastapi import HTTPException
from datetime import datetime

# Import centralized dependencies
from shared.api.dependencies import get_inventory_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Get application settings
    settings = get_settings()
    
    # Setup logging based on configuration
    from shared.logging.logger import setup_logging
    logger = setup_logging(
        log_level=settings.get_log_level(),
        enable_database_logging=settings.logging.database_logging,
        enable_json_output=(settings.logging.format == "json")
    )
    logger.info("SoleFlipper API starting up...", 
                environment=settings.environment,
                version=settings.api.version)
    
    await db_manager.initialize()
    await db_manager.run_migrations()
    logger.info("Database connection initialized and tables created")
    
    # Setup monitoring
    from shared.monitoring.health import setup_default_health_checks
    from shared.monitoring.metrics import get_metrics_collector
    
    await setup_default_health_checks(db_manager)
    metrics_collector = get_metrics_collector()
    metrics_collector.start_collection()
    
    logger.info("Monitoring and health checks initialized")
    
    yield
    
    logger.info("SoleFlipper API shutting down...")
    metrics_collector.stop_collection()
    await db_manager.close()
    logger.info("Database connections closed")

class APIInfo(BaseModel):
    name: str
    version: str

# Get settings for FastAPI configuration
settings = get_settings()

app = FastAPI(
    title=settings.api.title,
    version=settings.api.version,
    description=settings.api.description,
    openapi_url=settings.api.openapi_url,
    docs_url=settings.api.docs_url,
    redoc_url=settings.api.redoc_url,
    lifespan=lifespan,
)

# Add security middleware
from shared.security.middleware import add_security_middleware
add_security_middleware(app, settings)

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

# Include API routers
from domains.integration.api.webhooks import router as webhook_router
from domains.integration.api.upload_router import router as upload_router
from domains.orders.api.router import router as orders_router
from domains.products.api.router import router as products_router
from domains.inventory.api.router import router as inventory_router

app.include_router(webhook_router, prefix="/api/v1/integration", tags=["Integration"])
app.include_router(upload_router, prefix="/api/v1/integration", tags=["Integration"]) # Prefix is the same
app.include_router(orders_router, prefix="/api/v1/orders", tags=["Orders"])
app.include_router(products_router, prefix="/api/v1/products", tags=["Products"])
app.include_router(inventory_router, prefix="/api/v1/inventory", tags=["Inventory"])


@app.get("/", response_model=APIInfo, tags=["System"])
async def root():
    return APIInfo(name=settings.api.title, version=settings.api.version)

@app.get("/health", tags=["System"])
async def health_check():
    """Comprehensive health check endpoint"""
    from shared.monitoring.health import get_health_manager
    
    health_manager = get_health_manager()
    health_status = await health_manager.get_overall_health()
    
    return {
        "status": health_status["status"],
        "timestamp": health_status["timestamp"],
        "version": settings.api.version,
        "environment": settings.environment,
        "uptime_seconds": health_status["uptime_seconds"],
        "checks_summary": health_status["checks"],
        "components": health_status["components"]
    }

@app.get("/metrics", tags=["System"])
async def get_metrics():
    """Get application metrics"""
    from shared.monitoring.metrics import get_metrics_registry
    
    registry = get_metrics_registry()
    return {
        "timestamp": datetime.utcnow().isoformat() + 'Z',
        "metrics": registry.get_metrics_summary()
    }

@app.get("/health/ready", tags=["System"])
async def readiness_check():
    """Kubernetes readiness probe endpoint"""
    from shared.monitoring.health import get_health_manager, CheckType
    
    health_manager = get_health_manager()
    results = await health_manager.run_checks(check_types=[CheckType.READINESS])
    
    # Service is ready if all readiness checks pass
    is_ready = all(result.status == "healthy" for result in results.values())
    status_code = 200 if is_ready else 503
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if is_ready else "not_ready",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "checks": {name: result.status for name, result in results.items()}
        }
    )

@app.get("/health/live", tags=["System"])
async def liveness_check():
    """Kubernetes liveness probe endpoint"""
    from shared.monitoring.health import get_health_manager, CheckType
    
    health_manager = get_health_manager()
    results = await health_manager.run_checks(check_types=[CheckType.LIVENESS])
    
    # Service is alive if any liveness check passes (more lenient)
    is_alive = any(result.status in ["healthy", "degraded"] for result in results.values())
    status_code = 200 if is_alive else 503
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "alive" if is_alive else "dead",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "checks": {name: result.status for name, result in results.items()}
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host=settings.api.host, 
        port=settings.api.port, 
        reload=settings.api.reload,
        workers=settings.api.workers if not settings.api.reload else 1
    )
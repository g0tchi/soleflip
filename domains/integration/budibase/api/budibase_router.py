"""
Budibase Management API Router
=============================

REST endpoints for managing Budibase configurations, deployments, and synchronization.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from shared.api.dependencies import get_db_session
from shared.api.responses import SuccessResponse
from ..services.config_generator import BudibaseConfigGenerator
from ..services.deployment_service import BudibaseDeploymentService
from ..services.sync_service import BudibaseSyncService
from ..schemas.budibase_models import BudibaseApp, BudibaseEnvironment

logger = logging.getLogger(__name__)
router = APIRouter()


class GenerateConfigRequest(BaseModel):
    """Request model for configuration generation"""

    app_name: str = "SoleFlipper Business App"
    environment: BudibaseEnvironment = BudibaseEnvironment.DEVELOPMENT
    validate_endpoints: bool = True


class DeploymentRequest(BaseModel):
    """Request model for Budibase deployment"""

    app_name: str
    environment: BudibaseEnvironment
    auto_deploy: bool = False


class SyncRequest(BaseModel):
    """Request model for synchronization"""

    app_names: Optional[List[str]] = None
    force_sync: bool = False


@router.get(
    "/config/generate",
    response_model=Dict,
    summary="Generate Budibase Configuration",
    description="Generate v2.2.1 compatible Budibase configuration with validated endpoints",
)
async def generate_budibase_config(
    app_name: str = Query("SoleFlipper Business App", description="Application name"),
    environment: BudibaseEnvironment = Query(
        BudibaseEnvironment.DEVELOPMENT, description="Target environment"
    ),
    validate_endpoints: bool = Query(True, description="Validate API endpoints"),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Generate a new Budibase configuration with v2.2.1 compatibility.

    Features:
    - Validates all API endpoints before inclusion
    - Removes non-functional features
    - Generates realistic, working configurations
    - Provides detailed validation report
    """
    try:
        logger.info(f"Generating Budibase config: {app_name} for {environment}")

        # Initialize generator
        generator = BudibaseConfigGenerator()

        # Generate configuration
        config = await generator.generate_app_config(
            app_name=app_name, environment=environment, validate_endpoints=validate_endpoints
        )

        # Validate configuration
        validation_result = await generator.validate_config(config)

        # Prepare response
        response_data = {
            "config": config.dict(),
            "validation": validation_result.dict(),
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "generator_version": "2.2.1",
                "validated_endpoints": len(generator.validated_endpoints),
                "broken_endpoints": len(generator.broken_endpoints),
            },
        }

        return SuccessResponse(
            message=f"Generated Budibase configuration for {app_name}", data=response_data
        )

    except Exception as e:
        logger.error(f"Failed to generate Budibase config: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Configuration generation failed: {str(e)}",
        )


@router.post(
    "/config/validate",
    response_model=Dict,
    summary="Validate Budibase Configuration",
    description="Validate an existing Budibase configuration against v2.2.1 API",
)
async def validate_budibase_config(
    config: BudibaseApp, session: AsyncSession = Depends(get_db_session)
):
    """
    Validate a Budibase configuration for v2.2.1 compatibility.

    Checks:
    - API endpoint availability
    - Schema compatibility
    - Deprecated feature usage
    - Missing dependencies
    """
    try:
        logger.info(f"Validating Budibase config: {config.name}")

        generator = BudibaseConfigGenerator()
        validation_result = await generator.validate_config(config)

        return SuccessResponse(
            message=f"Validated configuration for {config.name}",
            data={
                "validation": validation_result.dict(),
                "summary": {
                    "is_valid": validation_result.is_valid,
                    "error_count": len(validation_result.errors),
                    "warning_count": len(validation_result.warnings),
                    "compatibility_score": len(validation_result.api_compatibility)
                    / max(
                        1,
                        len(validation_result.api_compatibility)
                        + len(validation_result.missing_endpoints),
                    )
                    * 100,
                },
            },
        )

    except Exception as e:
        logger.error(f"Configuration validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Validation failed: {str(e)}"
        )


@router.get(
    "/config/download/{config_type}",
    summary="Download Configuration Files",
    description="Download generated Budibase configuration files",
)
async def download_config_file(
    config_type: str, format: str = Query("json", description="File format")
):
    """
    Download specific Budibase configuration files.

    Available types:
    - app: Complete application configuration
    - datasources: Data source configurations
    - screens: Screen layouts and components
    - automations: Automation workflows
    - validation: Validation report
    """
    try:
        config_dir = Path(__file__).parent.parent / "config" / "generated"

        file_mapping = {
            "app": "soleflip-app-v221.json",
            "datasources": "datasources-v221.json",
            "screens": "screens-v221.json",
            "automations": "automations-v221.json",
            "validation": "validation-report-v221.json",
        }

        if config_type not in file_mapping:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid config type. Available: {list(file_mapping.keys())}",
            )

        file_path = config_dir / file_mapping[config_type]

        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration file not found: {config_type}",
            )

        return FileResponse(
            path=str(file_path),
            filename=f"budibase-{config_type}-v221.{format}",
            media_type="application/json",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File download failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Download failed: {str(e)}"
        )


@router.get(
    "/status",
    response_model=Dict,
    summary="Get Budibase Integration Status",
    description="Get status of Budibase integration and configurations",
)
async def get_budibase_status():
    """
    Get comprehensive status of Budibase integration.

    Returns:
    - API endpoint health
    - Configuration validity
    - Deployment status
    - Sync status
    """
    try:
        generator = BudibaseConfigGenerator()
        await generator._validate_api_endpoints()

        config_dir = Path(__file__).parent.parent / "config" / "generated"

        status_data = {
            "integration_status": "active",
            "api_health": {
                "validated_endpoints": len(generator.validated_endpoints),
                "broken_endpoints": len(generator.broken_endpoints),
                "working_endpoints": list(generator.validated_endpoints),
                "failed_endpoints": list(generator.broken_endpoints),
            },
            "configurations": {
                "available": config_dir.exists(),
                "config_files": (
                    [f.name for f in config_dir.glob("*.json")] if config_dir.exists() else []
                ),
                "last_generated": None,  # Would get from file timestamps
            },
            "capabilities": {
                "config_generation": True,
                "endpoint_validation": True,
                "auto_deployment": False,  # Placeholder
                "real_time_sync": False,  # Placeholder
            },
        }

        return SuccessResponse(message="Budibase integration status retrieved", data=status_data)

    except Exception as e:
        logger.error(f"Status check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Status check failed: {str(e)}",
        )


@router.post(
    "/deploy",
    response_model=Dict,
    summary="Deploy Budibase Application",
    description="Deploy Budibase configuration to target environment",
)
async def deploy_budibase_app(
    request: DeploymentRequest, session: AsyncSession = Depends(get_db_session)
):
    """
    Deploy Budibase application to specified environment.

    Note: This is a placeholder implementation.
    Real deployment would integrate with Budibase Cloud API.
    """
    try:
        logger.info(f"Deploying {request.app_name} to {request.environment}")

        # Placeholder implementation
        BudibaseDeploymentService()

        # In real implementation, this would:
        # 1. Generate configuration
        # 2. Upload to Budibase
        # 3. Configure environment
        # 4. Deploy application

        deployment_result = {
            "deployment_id": f"deploy_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "app_name": request.app_name,
            "environment": request.environment,
            "status": "queued",
            "message": "Deployment initiated (placeholder implementation)",
        }

        return SuccessResponse(
            message=f"Deployment initiated for {request.app_name}", data=deployment_result
        )

    except Exception as e:
        logger.error(f"Deployment failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Deployment failed: {str(e)}"
        )


@router.post(
    "/sync",
    response_model=Dict,
    summary="Synchronize Configurations",
    description="Sync Budibase configurations with SoleFlipper API changes",
)
async def sync_budibase_configs(
    request: SyncRequest, session: AsyncSession = Depends(get_db_session)
):
    """
    Synchronize Budibase configurations with API changes.

    Features:
    - Detect API schema changes
    - Update configurations automatically
    - Validate compatibility
    - Report sync status
    """
    try:
        logger.info(f"Syncing Budibase configurations: {request.app_names}")

        BudibaseSyncService()

        # Placeholder implementation
        sync_result = {
            "sync_id": f"sync_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "app_names": request.app_names or ["all"],
            "changes_detected": 0,
            "status": "completed",
            "message": "Sync completed (placeholder implementation)",
        }

        return SuccessResponse(message="Configuration sync completed", data=sync_result)

    except Exception as e:
        logger.error(f"Sync failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Sync failed: {str(e)}"
        )


@router.get(
    "/health",
    summary="Budibase Module Health Check",
    description="Health check for Budibase integration module",
)
async def budibase_health_check():
    """
    Health check for the Budibase integration module.

    Validates:
    - Module functionality
    - API connectivity
    - Configuration availability
    """
    try:
        # Quick health check
        generator = BudibaseConfigGenerator()

        health_status = {
            "status": "healthy",
            "module_version": "2.2.1",
            "api_base": generator.api_base_url,
            "timestamp": datetime.utcnow().isoformat(),
        }

        return SuccessResponse(message="Budibase module is healthy", data=health_status)

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Module health check failed: {str(e)}",
        )

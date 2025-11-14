"""
Budibase Integration Module
==========================

This module provides comprehensive integration with Budibase low-code platform,
including configuration management, deployment automation, and API synchronization.

Features:
- Automatic configuration generation from API schemas
- Real-time sync with SoleFlipper API changes
- Deployment automation and validation
- Schema mapping and compatibility checking
- Enterprise-grade configuration management

Version: v0.9.0 Compatible
"""

from .schemas.budibase_models import (
    BudibaseApp,
    BudibaseAutomation,
    BudibaseConnector,
    BudibaseDataSource,
    BudibaseScreen,
)
from .services.config_generator import BudibaseConfigGenerator
from .services.deployment_service import BudibaseDeploymentService
from .services.sync_service import BudibaseSyncService

__version__ = "0.9.0"
__author__ = "SoleFlipper Development Team"

__all__ = [
    "BudibaseConfigGenerator",
    "BudibaseDeploymentService",
    "BudibaseSyncService",
    "BudibaseApp",
    "BudibaseDataSource",
    "BudibaseConnector",
    "BudibaseScreen",
    "BudibaseAutomation",
]

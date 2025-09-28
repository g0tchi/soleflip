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

Version: v2.2.1 Compatible
"""

from .services.config_generator import BudibaseConfigGenerator
from .services.deployment_service import BudibaseDeploymentService
from .services.sync_service import BudibaseSyncService
from .schemas.budibase_models import (
    BudibaseApp,
    BudibaseDataSource,
    BudibaseConnector,
    BudibaseScreen,
    BudibaseAutomation
)

__version__ = "2.2.1"
__author__ = "SoleFlipper Development Team"

__all__ = [
    "BudibaseConfigGenerator",
    "BudibaseDeploymentService",
    "BudibaseSyncService",
    "BudibaseApp",
    "BudibaseDataSource",
    "BudibaseConnector",
    "BudibaseScreen",
    "BudibaseAutomation"
]
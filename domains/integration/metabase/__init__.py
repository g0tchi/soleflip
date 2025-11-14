"""
Metabase Integration Module
===========================

This module provides comprehensive integration with Metabase business intelligence platform,
including materialized views, dashboard templates, and automated synchronization.

Features:
- Optimized materialized views for fast dashboard queries
- Pre-built dashboard templates for key business metrics
- Automatic refresh scheduling and performance monitoring
- Real-time data sync with SoleFlipper database
- Enterprise-grade analytics infrastructure

Version: v2.2.3 Compatible
Architecture: Multi-Platform Orders (StockX, eBay, GOAT, etc.)
"""

from .schemas.metabase_models import (
    MetabaseCard,
    MetabaseCollection,
    MetabaseDashboard,
    MetabaseDatabase,
    MetabaseQuestion,
)
from .services.dashboard_service import MetabaseDashboardService
from .services.sync_service import MetabaseSyncService
from .services.view_manager import MetabaseViewManager

__version__ = "2.2.3"
__author__ = "SoleFlipper Development Team"

__all__ = [
    "MetabaseViewManager",
    "MetabaseDashboardService",
    "MetabaseSyncService",
    "MetabaseDashboard",
    "MetabaseQuestion",
    "MetabaseCard",
    "MetabaseDatabase",
    "MetabaseCollection",
]

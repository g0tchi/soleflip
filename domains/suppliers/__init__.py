"""
Suppliers Domain Package
Handles all supplier-related operations, including account management,
intelligence, and analytics.
"""

from .api.router import router as suppliers_router
from .services.supplier_service import SupplierService
from .core import analytics, models

__all__ = ["suppliers_router", "SupplierService", "analytics", "models"]

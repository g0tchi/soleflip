"""
SQLAlchemy Models for SoleFlipper
Clean, maintainable model definitions with proper relationships

This module re-exports all domain models from their respective files
for backward compatibility with existing imports.
"""

# Base classes and mixins
from shared.database.models.base import (
    Base,
    EncryptedFieldMixin,
    TimestampMixin,
    cipher_suite,
)

# Catalog domain models
from shared.database.models.catalog import (
    Brand,
    BrandPattern,
    Category,
    Product,
    Size,
)

# Inventory domain models
from shared.database.models.inventory import (
    InventoryItem,
    StockXPresaleMarking,
)

# Transaction and sales models
from shared.database.models.transactions import (
    Listing,
    Order,
    Transaction,
)

# Integration models
from shared.database.models.integration import (
    ImportBatch,
    ImportRecord,
    MarketplaceData,
    SourcePrice,
)

# Pricing models
from shared.database.models.pricing import (
    PricingHistory,
)

# Supplier models
from shared.database.models.suppliers import (
    AccountPurchaseHistory,
    Supplier,
    SupplierAccount,
    SupplierPerformance,
)

# System models
from shared.database.models.system import (
    EventStore,
    Platform,
    SystemConfig,
    SystemLog,
)

# Import pricing models from domains/pricing/models.py to register relationships
# This ensures the relationships defined in catalog models are properly linked
from domains.pricing.models import *  # noqa: F401,F403

__all__ = [
    # Base classes
    "Base",
    "TimestampMixin",
    "EncryptedFieldMixin",
    "cipher_suite",
    # Catalog
    "Brand",
    "BrandPattern",
    "Category",
    "Size",
    "Product",
    # Inventory
    "InventoryItem",
    "StockXPresaleMarking",
    # Transactions
    "Transaction",
    "Listing",
    "Order",
    # Integration
    "ImportBatch",
    "ImportRecord",
    "SourcePrice",
    "MarketplaceData",
    # Pricing
    "PricingHistory",
    # Suppliers
    "Supplier",
    "SupplierAccount",
    "AccountPurchaseHistory",
    "SupplierPerformance",
    # System
    "Platform",
    "SystemConfig",
    "SystemLog",
    "EventStore",
]

"""
SQLAlchemy Models for SoleFlipper
Clean, maintainable model definitions with proper relationships

DEPRECATED: This file is now a backward-compatible wrapper.
All models have been split into domain-specific files in shared/database/models/

New structure:
- shared/database/models/base.py - Base classes and mixins
- shared/database/models/catalog.py - Product catalog models
- shared/database/models/inventory.py - Inventory management models
- shared/database/models/transactions.py - Orders and transactions
- shared/database/models/integration.py - External integrations
- shared/database/models/pricing.py - Pricing history
- shared/database/models/suppliers.py - Supplier management
- shared/database/models/system.py - System configuration

For new code, import directly from the domain modules:
    from shared.database.models.catalog import Product, Brand
    from shared.database.models.inventory import InventoryItem

Or use the consolidated import from models package:
    from shared.database.models import Product, Brand, InventoryItem
"""

# Re-export all models for backward compatibility
from shared.database.models import *  # noqa: F401,F403

# Preserve the original module docstring behavior
__doc__ = """
SQLAlchemy Models for SoleFlipper
Clean, maintainable model definitions with proper relationships
"""

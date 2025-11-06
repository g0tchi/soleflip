"""
Inventory Repositories
======================

Data access layer for inventory domain.

Repositories:
- inventory_repository: Inventory item persistence
- product_repository: Product data access
"""

from domains.inventory.repositories import inventory_repository, product_repository

__all__ = [
    "inventory_repository",
    "product_repository",
]

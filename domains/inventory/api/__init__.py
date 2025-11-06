"""
Inventory API
=============

API routes for inventory management and dead stock analysis.

Routers:
- router: Inventory endpoints (stock, dead stock, predictive insights)
"""

from domains.inventory.api import router

__all__ = ["router"]

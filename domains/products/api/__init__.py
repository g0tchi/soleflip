"""
Products API
============

API routes for product catalog and brand intelligence.

Routers:
- router: Product endpoints (catalog, search, brand extraction)
"""

from domains.products.api import router

__all__ = ["router"]

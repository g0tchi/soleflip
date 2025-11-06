"""
Orders API
==========

API routes for multi-platform order management (StockX, eBay, GOAT, Alias).

Routers:
- router: Order endpoints (import, query, management)
"""

from domains.orders.api import router

__all__ = ["router"]

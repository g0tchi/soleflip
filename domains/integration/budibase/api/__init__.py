"""
Budibase API
============

API routes for Budibase integration.

Routers:
- budibase_router: Budibase sync and deployment endpoints
"""

from domains.integration.budibase.api import budibase_router

__all__ = ["budibase_router"]

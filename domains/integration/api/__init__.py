"""
Integration API
===============

API routes for external platform integrations.

Routers:
- router: Main integration endpoints
- upload_router: File upload endpoints
- webhooks: Webhook receivers
- quickflip_router: QuickFlip detection endpoints
"""

from domains.integration.api import quickflip_router, router, upload_router, webhooks

__all__ = [
    "router",
    "upload_router",
    "webhooks",
    "quickflip_router",
]

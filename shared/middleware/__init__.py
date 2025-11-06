"""
Middleware Module
=================

HTTP middleware for compression, ETag caching, and other request/response processing.

Exports:
- compression: Response compression middleware
- etag: ETag-based caching middleware
"""

from shared.middleware import compression, etag

__all__ = [
    "compression",
    "etag",
]

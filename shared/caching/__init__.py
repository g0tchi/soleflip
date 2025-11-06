"""
Caching Module
==============

Redis-based caching strategies and utilities.

Exports:
- dashboard_cache: Dashboard-specific caching implementation
"""

from shared.caching import dashboard_cache

__all__ = ["dashboard_cache"]

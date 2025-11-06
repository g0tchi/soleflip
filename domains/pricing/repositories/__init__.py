"""
Pricing Repositories
====================

Data access layer for pricing domain.

Repositories:
- pricing_repository: Price data persistence and retrieval
"""

from domains.pricing.repositories import pricing_repository

__all__ = ["pricing_repository"]

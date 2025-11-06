"""
Analytics Repositories
======================

Data access layer for analytics domain.

Repositories:
- forecast_repository: Forecast data persistence and retrieval
"""

from domains.analytics.repositories import forecast_repository

__all__ = ["forecast_repository"]

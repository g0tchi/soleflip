"""
Analytics Services
==================

Business logic for forecasting, KPI calculations, and business intelligence.

Services:
- forecast_engine: ARIMA forecasting and seasonal adjustments
"""

from domains.analytics.services import forecast_engine

__all__ = ["forecast_engine"]
